"""
Anima LoRA Comparison — ComfyUI plugin for batch LoRA comparison on Anima/Cosmos models.

Nodes:
    AnimaModelLoader  — UNET + CLIP + VAE 集合加载器
    AnimaLoraList     — LoRA 对比列表
    AnimaXYSampler    — XY 对比采样器
    AnimaImageGrid    — 图像排版节点
"""

import json
import torch
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
                "UNET模型": (
                    folder_paths.get_filename_list("diffusion_models"),
                    {"tooltip": "models/diffusion_models"},
                ),
                "权重精度": (
                    ["default", "fp8_e4m3fn", "fp8_e5m2"],
                    {"default": "default"},
                ),
                "CLIP模型": (
                    folder_paths.get_filename_list("text_encoders"),
                    {"tooltip": "models/text_encoders"},
                ),
                "CLIP类型": (
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
                "CLIP设备": (
                    ["default", "cpu"],
                    {"default": "default"},
                ),
                "VAE模型": (
                    folder_paths.get_filename_list("vae"),
                    {"tooltip": "models/vae"},
                ),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("模型", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "Anima-lora-测试"

    def load(self, UNET模型, 权重精度, CLIP模型, CLIP类型, CLIP设备, VAE模型):
        model_options = {}
        if 权重精度 == "fp8_e4m3fn":
            model_options["dtype"] = torch.float8_e4m3fn
        elif 权重精度 == "fp8_e5m2":
            model_options["dtype"] = torch.float8_e5m2

        model = comfy.sd.load_diffusion_model(
            folder_paths.get_full_path("diffusion_models", UNET模型),
            model_options=model_options,
        )

        clip_type_attr = CLIP类型.upper().replace(" ", "_")
        clip_type_enum = getattr(
            comfy.sd.CLIPType, clip_type_attr, comfy.sd.CLIPType.STABLE_DIFFUSION
        )
        clip = comfy.sd.load_clip(
            ckpt_paths=[folder_paths.get_full_path("text_encoders", CLIP模型)],
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_type_enum,
        )

        vae_sd = comfy.utils.load_torch_file(
            folder_paths.get_full_path("vae", VAE模型)
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
                "LoRA数量": (
                    "INT",
                    {
                        "default": 2,
                        "min": 1,
                        "max": s.MAX_SLOTS,
                        "step": 1,
                    },
                ),
                "lora_data": (
                    "STRING",
                    {"default": "", "multiline": False},
                ),
                "权重": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "round": 0.001,
                    },
                ),
            },
        }

    RETURN_TYPES = ("LORA_LIST",)
    RETURN_NAMES = ("LoRA列表",)
    FUNCTION = "generate"
    CATEGORY = "Anima-lora-测试"

    def generate(self, LoRA数量, lora_data="", 权重=1.0, **kwargs):
        if 权重 is None:
            权重 = 1.0
        if lora_data is None:
            lora_data = ""

        selections = {}
        if lora_data:
            try:
                selections = json.loads(lora_data)
            except (json.JSONDecodeError, TypeError):
                pass

        loras = []
        for i in range(1, LoRA数量 + 1):
            name = selections.get(f"lora_{i}", "(none)")
            if name and name != "(none)":
                loras.append((name, 权重))

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
                "模型": ("MODEL",),
                "正向": ("CONDITIONING",),
                "反向": ("CONDITIONING",),
                "潜空间": ("LATENT",),
                "VAE": ("VAE",),
                "种子": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
                "步数": (
                    "INT",
                    {"default": 30, "min": 1, "max": 10000},
                ),
                "CFG": (
                    "FLOAT",
                    {
                        "default": 5.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "round": 0.01,
                    },
                ),
                "采样器": (
                    comfy.samplers.KSampler.SAMPLERS,
                    {"default": "euler"},
                ),
                "调度器": (
                    comfy.samplers.KSampler.SCHEDULERS,
                    {"default": "simple"},
                ),
                "降噪": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            },
            "optional": {
                "LoRA列表": ("LORA_LIST",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像列表",)
    FUNCTION = "sample"
    CATEGORY = "Anima-lora-测试"

    def sample(
        self,
        模型,
        正向,
        反向,
        潜空间,
        VAE,
        种子,
        步数,
        CFG,
        采样器,
        调度器,
        降噪,
        LoRA列表=None,
    ):
        if LoRA列表 is None:
            LoRA列表 = [("", 0)]

        latent = 潜空间.copy()
        latent_samples = latent["samples"]
        latent_samples = comfy.sample.fix_empty_latent_channels(
            模型, latent_samples,
            latent.get("downscale_ratio_spacial", None),
            latent.get("downscale_ratio_temporal", None),
        )
        latent["samples"] = latent_samples
        noise_mask = latent.get("noise_mask", None)

        images = []

        for idx, item in enumerate(LoRA列表):
            lora_name = item[0] if item else ""
            strength = item[1] if len(item) > 1 else 0

            if lora_name:
                print(
                    f"[AnimaXY] ({idx + 1}/{len(LoRA列表)}) "
                    f"{lora_name}  strength={strength}"
                )
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path is None:
                    raise FileNotFoundError(f"找不到 LoRA: {lora_name}")
                lora_sd = comfy.utils.load_torch_file(lora_path)
                model_lora, _ = comfy.sd.load_lora_for_models(
                    模型, None, lora_sd, strength, 0
                )
            else:
                model_lora = 模型

            batch_inds = latent.get("batch_index", None)
            noise = comfy.sample.prepare_noise(latent_samples, 种子, batch_inds)

            samples_out = comfy.sample.sample(
                model_lora, noise, 步数, CFG,
                采样器, 调度器,
                正向, 反向, latent_samples,
                denoise=降噪,
                noise_mask=noise_mask,
                seed=种子,
            )
            samples_out = samples_out.to(
                device=comfy.model_management.intermediate_device(),
                dtype=comfy.model_management.intermediate_dtype(),
            )

            if samples_out.is_nested:
                samples_out = samples_out.unbind()[0]
            decoded = VAE.decode(samples_out)
            if len(decoded.shape) == 5:
                decoded = decoded.reshape(-1, decoded.shape[-3], decoded.shape[-2], decoded.shape[-1])
            images.append(decoded)

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
                "图像": ("IMAGE",),
                "方向": (
                    ["左右排列", "上下排列"],
                    {"default": "左右排列"},
                ),
                "间距": (
                    "INT",
                    {"default": 0, "min": 0, "max": 256, "step": 1},
                ),
                "颜色": (
                    ["黑色", "白色", "灰色", "红色", "绿色", "蓝色"],
                    {"default": "黑色"},
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

    def grid(self, 图像, 方向, 间距, 颜色):
        n = 图像.shape[0]
        if n == 1:
            return (图像,)

        r, g, b = self.COLOR_MAP.get(颜色, (0, 0, 0))
        img_list = [图像[i] for i in range(n)]

        if 方向 == "左右排列":
            max_h = max(img.shape[0] for img in img_list)
            total_w = sum(img.shape[1] for img in img_list) + 间距 * (n - 1)
            canvas = torch.zeros(max_h, total_w, 3, dtype=图像.dtype, device=图像.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            x = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                y_off = (max_h - h) // 2
                canvas[y_off:y_off+h, x:x+w, :] = img
                x += w + 间距
        else:
            max_w = max(img.shape[1] for img in img_list)
            total_h = sum(img.shape[0] for img in img_list) + 间距 * (n - 1)
            canvas = torch.zeros(total_h, max_w, 3, dtype=图像.dtype, device=图像.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            y = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                x_off = (max_w - w) // 2
                canvas[y:y+h, x_off:x_off+w, :] = img
                y += h + 间距

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
