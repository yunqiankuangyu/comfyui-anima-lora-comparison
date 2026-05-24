"""
Anima LoRA XY — ComfyUI plugin for batch LoRA comparison on Anima/Cosmos models.

Nodes:
    AnimaModelLoader  — UNET + CLIP + VAE 集合加载器
    AnimaLoraList     — LoRA 对比列表
    AnimaXYSampler    — XY 对比采样器
    AnimaImageGrid    — 图像排版节点
"""

import json
import torch
import numpy as np
import comfy.sd
import comfy.sample
import comfy.utils
import comfy.samplers
import comfy.model_management
import folder_paths


# ─────────────────────────────────────────────
#  AnimaModelLoader
# ─────────────────────────────────────────────

class AnimaModelLoader:
    """UNET + CLIP + VAE 集合加载器"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "unet_name": (
                    folder_paths.get_filename_list("diffusion_models"),
                    {"tooltip": "UNET 模型 (models/diffusion_models)"},
                ),
                "weight_dtype": (
                    ["default", "fp8_e4m3fn", "fp8_e5m2"],
                    {"default": "default"},
                ),
                "clip_name": (
                    folder_paths.get_filename_list("text_encoders"),
                    {"tooltip": "CLIP 文本编码器 (models/text_encoders)"},
                ),
                "clip_type": (
                    [
                        "stable_diffusion",
                        "stable_cascade",
                        "sd3",
                        "stable_audio",
                        "mochi",
                        "cosmos",
                        "ltxv",
                        "pixart",
                        "wan",
                        "hunyuan_video",
                    ],
                    {"default": "stable_diffusion"},
                ),
                "clip_device": (
                    ["default", "cpu"],
                    {"default": "default"},
                ),
                "vae_name": (
                    folder_paths.get_filename_list("vae"),
                    {"tooltip": "VAE (models/vae)"},
                ),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("模型", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "Anima-lora-测试"

    def load(self, unet_name, weight_dtype, clip_name, clip_type, clip_device, vae_name):
        model_options = {}
        if weight_dtype == "fp8_e4m3fn":
            model_options["dtype"] = torch.float8_e4m3fn
        elif weight_dtype == "fp8_e5m2":
            model_options["dtype"] = torch.float8_e5m2

        model = comfy.sd.load_diffusion_model(
            folder_paths.get_full_path("diffusion_models", unet_name),
            model_options=model_options,
        )

        clip_type_attr = clip_type.upper().replace(" ", "_")
        clip_type_enum = getattr(
            comfy.sd.CLIPType, clip_type_attr, comfy.sd.CLIPType.STABLE_DIFFUSION
        )
        clip = comfy.sd.load_clip(
            ckpt_paths=[folder_paths.get_full_path("text_encoders", clip_name)],
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_type_enum,
        )

        vae_sd = comfy.utils.load_torch_file(
            folder_paths.get_full_path("vae", vae_name)
        )
        vae = comfy.sd.VAE(sd=vae_sd)

        return (model, clip, vae)


# ─────────────────────────────────────────────
#  AnimaLoraList
# ─────────────────────────────────────────────

class AnimaLoraList:
    """LoRA 对比列表，JS 动态创建下拉槽位"""

    MAX_SLOTS = 20

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "lora_count": (
                    "INT",
                    {
                        "default": 2,
                        "min": 1,
                        "max": s.MAX_SLOTS,
                        "step": 1,
                        "tooltip": "要对比的 LoRA 数量",
                    },
                ),
                "lora_data": (
                    "STRING",
                    {"default": "", "multiline": False},
                ),
                "strength": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "round": 0.001,
                        "tooltip": "所有 LoRA 统一权重",
                    },
                ),
            },
        }

    RETURN_TYPES = ("LORA_LIST",)
    RETURN_NAMES = ("LoRA列表",)
    FUNCTION = "generate"
    CATEGORY = "Anima-lora-测试"

    def generate(self, lora_count, lora_data="", strength=1.0, **kwargs):
        if strength is None:
            strength = 1.0
        if lora_data is None:
            lora_data = ""

        selections = {}
        if lora_data:
            try:
                selections = json.loads(lora_data)
            except (json.JSONDecodeError, TypeError):
                pass

        loras = []
        for i in range(1, lora_count + 1):
            name = selections.get(f"lora_{i}", "(none)")
            if name and name != "(none)":
                loras.append((name, strength))

        if not loras:
            raise ValueError("AnimaLoraList: 至少需要选择一个有效的 LoRA")

        return (loras,)


# ─────────────────────────────────────────────
#  AnimaXYSampler
# ─────────────────────────────────────────────

class AnimaXYSampler:
    """
    XY 对比采样器
    连接 LoRA 列表时遍历批量生成；不接时退化为普通单次采样
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "latent_image": ("LATENT",),
                "vae": ("VAE",),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                        "tooltip": "随机种子",
                    },
                ),
                "steps": (
                    "INT",
                    {"default": 30, "min": 1, "max": 10000, "tooltip": "采样步数"},
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 5.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "round": 0.01,
                        "tooltip": "CFG 引导强度",
                    },
                ),
                "sampler_name": (
                    comfy.samplers.KSampler.SAMPLERS,
                    {"default": "euler", "tooltip": "采样器"},
                ),
                "scheduler": (
                    comfy.samplers.KSampler.SCHEDULERS,
                    {"default": "simple", "tooltip": "调度器"},
                ),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "降噪强度"},
                ),
            },
            "optional": {
                "lora_list": ("LORA_LIST",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像列表",)
    FUNCTION = "sample"
    CATEGORY = "Anima-lora-测试"

    def sample(
        self,
        model,
        positive,
        negative,
        latent_image,
        vae,
        seed,
        steps,
        cfg,
        sampler_name,
        scheduler,
        denoise,
        lora_list=None,
    ):
        if lora_list is None:
            lora_list = [("", 0)]

        latent = latent_image.copy()
        latent_samples = latent["samples"]
        latent_samples = comfy.sample.fix_empty_latent_channels(
            model, latent_samples,
            latent.get("downscale_ratio_spacial", None),
            latent.get("downscale_ratio_temporal", None),
        )
        latent["samples"] = latent_samples
        noise_mask = latent.get("noise_mask", None)

        images = []

        for idx, item in enumerate(lora_list):
            lora_name = item[0] if item else ""
            strength = item[1] if len(item) > 1 else 0

            if lora_name:
                print(
                    f"[AnimaXY] ({idx + 1}/{len(lora_list)}) "
                    f"{lora_name}  strength={strength}"
                )
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path is None:
                    raise FileNotFoundError(f"找不到 LoRA: {lora_name}")
                lora_sd = comfy.utils.load_torch_file(lora_path)
                model_lora, _ = comfy.sd.load_lora_for_models(
                    model, None, lora_sd, strength, 0
                )
            else:
                model_lora = model

            batch_inds = latent.get("batch_index", None)
            noise = comfy.sample.prepare_noise(latent_samples, seed, batch_inds)

            samples_out = comfy.sample.sample(
                model_lora, noise, steps, cfg,
                sampler_name, scheduler,
                positive, negative, latent_samples,
                denoise=denoise,
                noise_mask=noise_mask,
                seed=seed,
            )
            samples_out = samples_out.to(
                device=comfy.model_management.intermediate_device(),
                dtype=comfy.model_management.intermediate_dtype(),
            )

            if samples_out.is_nested:
                samples_out = samples_out.unbind()[0]
            decoded = vae.decode(samples_out)
            if len(decoded.shape) == 5:
                decoded = decoded.reshape(-1, decoded.shape[-3], decoded.shape[-2], decoded.shape[-1])
            images.append(decoded)

        # Concatenate all images into a single batch tensor
        output = torch.cat(images, dim=0)
        return (output,)


# ─────────────────────────────────────────────
#  AnimaImageGrid
# ─────────────────────────────────────────────

class AnimaImageGrid:
    """
    图像排版节点
    将多张图片按指定方向排列，支持调整间距
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "direction": (
                    ["左右排列", "上下排列"],
                    {"default": "左右排列", "tooltip": "排列方向"},
                ),
                "gap": (
                    "INT",
                    {"default": 0, "min": 0, "max": 256, "step": 1, "tooltip": "图像间距（像素）"},
                ),
                "gap_color": (
                    ["黑色", "白色", "灰色", "红色", "绿色", "蓝色"],
                    {"default": "黑色", "tooltip": "间距颜色"},
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "grid"
    CATEGORY = "Anima-lora-测试"

    COLOR_MAP = {
        "黑色": (0, 0, 0),
        "白色": (255, 255, 255),
        "灰色": (128, 128, 128),
        "红色": (255, 0, 0),
        "绿色": (0, 255, 0),
        "蓝色": (0, 0, 255),
    }

    def grid(self, images, direction, gap, gap_color):
        n = images.shape[0]
        if n == 1:
            return (images,)

        r, g, b = self.COLOR_MAP.get(gap_color, (0, 0, 0))
        img_list = [images[i] for i in range(n)]

        if direction == "左右排列":
            max_h = max(img.shape[0] for img in img_list)
            total_w = sum(img.shape[1] for img in img_list) + gap * (n - 1)
            canvas = torch.zeros(max_h, total_w, 3, dtype=images.dtype, device=images.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            x = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                y_off = (max_h - h) // 2
                canvas[y_off:y_off+h, x:x+w, :] = img
                x += w + gap
        else:
            max_w = max(img.shape[1] for img in img_list)
            total_h = sum(img.shape[0] for img in img_list) + gap * (n - 1)
            canvas = torch.zeros(total_h, max_w, 3, dtype=images.dtype, device=images.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            y = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                x_off = (max_w - w) // 2
                canvas[y:y+h, x_off:x_off+w, :] = img
                y += h + gap

        return (canvas.unsqueeze(0),)


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "AnimaModelLoader": AnimaModelLoader,
    "AnimaLoraList": AnimaLoraList,
    "AnimaXYSampler": AnimaXYSampler,
    "AnimaImageGrid": AnimaImageGrid,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaModelLoader": "Anima 模型加载器",
    "AnimaLoraList": "Anima LoRA 列表",
    "AnimaXYSampler": "Anima XY 采样器",
    "AnimaImageGrid": "Anima 图像排版",
}
