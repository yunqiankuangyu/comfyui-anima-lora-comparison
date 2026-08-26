"""
Anima LoRA Comparison — ComfyUI plugin for batch LoRA comparison on Anima/Cosmos models.

Nodes:
    AnimaModelLoader  — UNET + CLIP + VAE all-in-one loader
    AnimaLoraList     — LoRA comparison list
    AnimaXYSampler    — XY comparison sampler
    AnimaImageGrid    — Image grid layout node
"""

import json
import os
import sys
import torch
import comfy.sd
import comfy.sample
import comfy.utils
import comfy.samplers
import comfy.model_management
import folder_paths
import latent_preview


# ─────────────────────────────────────────────
#  AnimaModelLoader
# ─────────────────────────────────────────────

class AnimaModelLoader:
    """UNET + CLIP + VAE all-in-one loader"""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "UNET Model": (
                    folder_paths.get_filename_list("diffusion_models"),
                    {"tooltip": "models/diffusion_models"},
                ),
                "Weight Precision": (
                    ["default", "fp8_e4m3fn", "fp8_e5m2"],
                    {"default": "default"},
                ),
                "CLIP Model": (
                    folder_paths.get_filename_list("text_encoders"),
                    {"tooltip": "models/text_encoders"},
                ),
                "CLIP Type": (
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
                "CLIP Device": (
                    ["default", "cpu"],
                    {"default": "default"},
                ),
                "VAE Model": (
                    folder_paths.get_filename_list("vae"),
                    {"tooltip": "models/vae"},
                ),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "Anima/LoRA Comparison"

    def load(self, **kwargs):
        # ComfyUI 0.33+ passes INPUT_TYPES keys as-is (spaces, not underscores)
        UNET_Model = kwargs.get("UNET Model", kwargs.get("UNET_Model"))
        Weight_Precision = kwargs.get("Weight Precision", kwargs.get("Weight_Precision"))
        CLIP_Model = kwargs.get("CLIP Model", kwargs.get("CLIP_Model"))
        CLIP_Type = kwargs.get("CLIP Type", kwargs.get("CLIP_Type"))
        CLIP_Device = kwargs.get("CLIP Device", kwargs.get("CLIP_Device"))
        VAE_Model = kwargs.get("VAE Model", kwargs.get("VAE_Model"))
        model_options = {}
        if Weight_Precision == "fp8_e4m3fn":
            model_options["dtype"] = torch.float8_e4m3fn
        elif Weight_Precision == "fp8_e5m2":
            model_options["dtype"] = torch.float8_e5m2

        model = comfy.sd.load_diffusion_model(
            folder_paths.get_full_path("diffusion_models", UNET_Model),
            model_options=model_options,
        )

        clip_type_attr = CLIP_Type.upper().replace(" ", "_")
        clip_type_enum = getattr(
            comfy.sd.CLIPType, clip_type_attr, comfy.sd.CLIPType.STABLE_DIFFUSION
        )
        clip = comfy.sd.load_clip(
            ckpt_paths=[folder_paths.get_full_path("text_encoders", CLIP_Model)],
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_type_enum,
        )

        vae_sd = comfy.utils.load_torch_file(
            folder_paths.get_full_path("vae", VAE_Model)
        )
        vae = comfy.sd.VAE(sd=vae_sd)

        return (model, clip, vae)


# ─────────────────────────────────────────────
#  AnimaLoraList
# ─────────────────────────────────────────────

class AnimaLoraList:
    """LoRA comparison list, JS dynamically creates combo slots"""

    MAX_SLOTS = 20

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "Strength": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "round": 0.001,
                    },
                ),
                "LoRA Count": (
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
                "Apply Mode": (
                    ["Standard", "Anima 3.8B Bridge"],
                    {"default": "Standard"},
                ),
            },
        }

    RETURN_TYPES = ("LORA_LIST",)
    RETURN_NAMES = ("LORA_LIST",)
    FUNCTION = "generate"
    CATEGORY = "Anima/LoRA Comparison"

    def generate(self, **kwargs):
        def _get(*names, default=None):
            for n in names:
                if n in kwargs:
                    return kwargs[n]
            return default

        LoRA_Count = int(_get("LoRA Count", "LoRA_Count", default=2) or 2)
        lora_data = _get("lora_data", default="") or ""
        Strength = _get("Strength", "strength")
        Apply_Mode = _get("Apply Mode", "Apply_Mode") or "Standard"
        if Strength is None:
            Strength = 1.0
        if lora_data is None:
            lora_data = ""

        selections = {}
        if lora_data:
            try:
                selections = json.loads(lora_data)
            except (json.JSONDecodeError, TypeError):
                pass

        loras = []
        for i in range(1, LoRA_Count + 1):
            name = selections.get(f"lora_{i}", "(none)")
            if name and name != "(none)":
                loras.append((name, Strength))

        if not loras:
            raise ValueError("AnimaLoraList: at least one valid LoRA must be selected")

        # list items: (name, strength) or ("__apply_mode__", mode_string)
        return (loras + [("__apply_mode__", Apply_Mode)],)


# ─────────────────────────────────────────────
#  AnimaXYSampler
# ─────────────────────────────────────────────

class AnimaXYSampler:
    """
    XY comparison sampler
    When LoRA list is connected: iterate and generate one image per LoRA
    When not connected: falls back to a single normal sample
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "MODEL": ("MODEL",),
                "Positive": ("CONDITIONING",),
                "Negative": ("CONDITIONING",),
                "Latent": ("LATENT",),
                "VAE": ("VAE",),
                "Seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
                "Steps": (
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
                "Sampler": (
                    comfy.samplers.KSampler.SAMPLERS,
                    {"default": "euler"},
                ),
                "Scheduler": (
                    comfy.samplers.KSampler.SCHEDULERS,
                    {"default": "simple"},
                ),
                "Denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            },
            "optional": {
                "LoRA List": ("LORA_LIST",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "sample"
    CATEGORY = "Anima/LoRA Comparison"

    def sample(
        self,
        **kwargs,
    ):
        MODEL = kwargs["MODEL"]
        Positive = kwargs["Positive"]
        Negative = kwargs["Negative"]
        Latent = kwargs["Latent"]
        VAE = kwargs["VAE"]
        Seed = int(kwargs.get("Seed", 0))
        Steps = int(kwargs.get("Steps", 30))
        CFG = float(kwargs.get("CFG", 5.0))
        Sampler = kwargs.get("Sampler", "euler")
        Scheduler = kwargs.get("Scheduler", "simple")
        Denoise = float(kwargs.get("Denoise", 1.0))
        LoRA_List = kwargs.get("LoRA List") or kwargs.get("LoRA_List")
        Steps = int(kwargs.get("Steps", kwargs.get("steps", 30)))

        if LoRA_List is None:
            LoRA_List = [("", 0)]

        # Apply Mode is carried inside the LORA_LIST as a ("__apply_mode__", mode) item
        Apply_Mode = "Standard"
        clean_list = []
        for it in LoRA_List:
            if it and it[0] == "__apply_mode__":
                Apply_Mode = it[1]
            else:
                clean_list.append(it)
        LoRA_List = clean_list

        bridge_remap = None
        if Apply_Mode == "Anima 3.8B Bridge":
            block_count = MODEL.model.model_config.unet_config.get("num_blocks")
            if block_count != 52:
                raise ValueError(
                    f"Anima 3.8B Bridge requires a 52-block (3.8B) MODEL, got {block_count!r}"
                )
            try:
                from comfyui_anima_3_8b_lora_bridge.mapping import remap_lora
                bridge_remap = remap_lora
            except ImportError:
                try:
                    sys.path.insert(
                        0,
                        os.path.join(
                            folder_paths.get_folder_paths("custom_nodes")[0],
                            "comfyui-anima-3-8b-lora-bridge",
                        ),
                    )
                    from mapping import remap_lora
                    bridge_remap = remap_lora
                finally:
                    if sys.path[0].endswith("comfyui-anima-3-8b-lora-bridge"):
                        sys.path.pop(0)

        latent = Latent.copy()
        latent_samples = latent["samples"]
        latent_samples = comfy.sample.fix_empty_latent_channels(
            MODEL, latent_samples,
            latent.get("downscale_ratio_spacial", None),
        )
        latent["samples"] = latent_samples
        noise_mask = latent.get("noise_mask", None)

        disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED

        images = []

        for idx, item in enumerate(LoRA_List):
            callback = latent_preview.prepare_callback(MODEL, Steps)
            lora_name = item[0] if item else ""
            strength = item[1] if len(item) > 1 else 0

            if lora_name:
                print(
                    f"[AnimaXY] ({idx + 1}/{len(LoRA_List)}) "
                    f"{lora_name}  strength={strength}"
                )
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path is None:
                    raise FileNotFoundError(f"LoRA not found: {lora_name}")
                lora_sd = comfy.utils.load_torch_file(lora_path)
                if bridge_remap is not None:
                    lora_sd, _, _, _ = bridge_remap(lora_sd)
                model_lora, _ = comfy.sd.load_lora_for_models(
                    MODEL, None, lora_sd, strength, 0
                )
            else:
                model_lora = MODEL

            batch_inds = latent.get("batch_index", None)
            noise = comfy.sample.prepare_noise(latent_samples, Seed, batch_inds)

            samples_out = comfy.sample.sample(
                model_lora, noise, Steps, CFG,
                Sampler, Scheduler,
                Positive, Negative, latent_samples,
                denoise=Denoise,
                noise_mask=noise_mask,
                callback=callback,
                disable_pbar=disable_pbar,
                seed=Seed,
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
    Image grid layout node
    Arranges multiple images in a specified direction with adjustable gap
    """

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "Image": ("IMAGE",),
                "Direction": (
                    ["Horizontal", "Vertical"],
                    {"default": "Horizontal"},
                ),
                "Gap": (
                    "INT",
                    {"default": 0, "min": 0, "max": 256, "step": 1},
                ),
                "Color": (
                    ["Black", "White", "Gray", "Red", "Green", "Blue"],
                    {"default": "Black"},
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "grid"
    CATEGORY = "Anima/LoRA Comparison"

    COLOR_MAP = {
        "Black": (0, 0, 0),
        "White": (255, 255, 255),
        "Gray": (128, 128, 128),
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 0, 255),
    }

    def grid(self, Image, Direction, Gap, Color):
        n = Image.shape[0]
        if n == 1:
            return (Image,)

        r, g, b = self.COLOR_MAP.get(Color, (0, 0, 0))
        img_list = [Image[i] for i in range(n)]

        if Direction == "Horizontal":
            max_h = max(img.shape[0] for img in img_list)
            total_w = sum(img.shape[1] for img in img_list) + Gap * (n - 1)
            canvas = torch.zeros(max_h, total_w, 3, dtype=Image.dtype, device=Image.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            x = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                y_off = (max_h - h) // 2
                canvas[y_off:y_off+h, x:x+w, :] = img
                x += w + Gap
        else:
            max_w = max(img.shape[1] for img in img_list)
            total_h = sum(img.shape[0] for img in img_list) + Gap * (n - 1)
            canvas = torch.zeros(total_h, max_w, 3, dtype=Image.dtype, device=Image.device)
            canvas[:, :, 0] = r / 255.0
            canvas[:, :, 1] = g / 255.0
            canvas[:, :, 2] = b / 255.0

            y = 0
            for img in img_list:
                h, w = img.shape[0], img.shape[1]
                x_off = (max_w - w) // 2
                canvas[y:y+h, x_off:x_off+w, :] = img
                y += h + Gap

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
    "AnimaModelLoader": "Anima Model Loader",
    "AnimaLoraList": "Anima LoRA List",
    "AnimaXYSampler": "Anima XY Sampler",
    "AnimaImageGrid": "Anima Image Grid",
}
