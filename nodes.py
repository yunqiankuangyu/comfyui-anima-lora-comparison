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
import glob
import torch
import comfy.sd
import comfy.sample
import comfy.utils
import comfy.samplers
import comfy.model_management
import folder_paths
import latent_preview
import numpy as np
from PIL import Image, ImageDraw, ImageFont


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

    RETURN_TYPES = ("IMAGE", "LORA_NAMES")
    RETURN_NAMES = ("IMAGE", "LORA_NAMES")
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
        lora_names = []  # Extract LoRA names for passing to ImageGrid
        for it in LoRA_List:
            if it and it[0] == "__apply_mode__":
                Apply_Mode = it[1]
            else:
                clean_list.append(it)
                if it and it[0] and it[0] != "":
                    lora_names.append(it[0])
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
        lora_names_str = "\n".join(lora_names) if lora_names else ""
        return (output, lora_names_str)


# ─────────────────────────────────────────────
#  Image Annotation Utilities
# ─────────────────────────────────────────────

def _tensor_to_pil(image_tensor):
    """Convert ComfyUI IMAGE tensor (BHWC) to PIL Image."""
    if isinstance(image_tensor, torch.Tensor):
        if image_tensor.ndim == 4:  # Batch dimension
            image_tensor = image_tensor[0]
        arr = image_tensor.detach().cpu().float().numpy()
        # ComfyUI IMAGE is BHWC. If this looks like BCHW (channels on dim0), permute.
        if arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[2] > 4:
            arr = arr.transpose(1, 2, 0)  # BCHW -> HWC
        arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
        if arr.ndim == 2:
            return Image.fromarray(arr, "L").convert("RGB")
        if arr.shape[2] == 4:
            return Image.fromarray(arr, "RGBA").convert("RGB")
        return Image.fromarray(arr, "RGB")
    return image_tensor


_MODEL_EXTS = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".sft"}


def _strip_model_ext(name):
    """Strip directory prefix (keep only the basename) and trailing model extensions
    like .safetensors / .ckpt. Handles both `foo.safetensors` and nested
    `anima\\YKS\\foo.safetensors` -> `foo`."""
    name = name.strip()
    # keep only the last path segment (strip nested folder prefixes)
    for sep in ("/", "\\"):
        if sep in name:
            name = name.rsplit(sep, 1)[-1]
    changed = True
    while changed:
        changed = False
        low = name.lower()
        for ext in _MODEL_EXTS:
            if low.endswith(ext):
                name = name[: -len(ext)]
                changed = True
                break
    return name


def _pil_to_tensor(image_pil):
    """Convert PIL Image to ComfyUI IMAGE tensor (BHWC)."""
    image_np = np.array(image_pil).astype(np.float32) / 255.0
    # ComfyUI IMAGE is BHWC — keep HWC order, just add batch dim
    image_tensor = torch.from_numpy(image_np)  # (H, W, C)
    return image_tensor.unsqueeze(0)  # (1, H, W, C)


def _make_label_font(font_size):
    """Return a PIL font covering CJK + Latin. Probes system CJK fonts first
    (Windows YaHei/SimHei, macOS PingFang, Linux Noto CJK / wqy), then arial,
    then PIL default. Cached per font_size."""
    if font_size in _LABEL_FONT_CACHE:
        return _LABEL_FONT_CACHE[font_size]
    font = None
    for path, idx in _LABEL_FONT_CANDIDATES:
        try:
            font = (ImageFont.truetype(path, font_size, index=idx)
                    if idx is not None else ImageFont.truetype(path, font_size))
            break
        except Exception:
            continue
    if font is None:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
    _LABEL_FONT_CACHE[font_size] = font
    return font


_LABEL_FONT_CACHE = {}


def _label_font_candidates():
    cands = []
    wf = "C:/Windows/Fonts"
    if os.path.isdir(wf):
        cands += [
            (os.path.join(wf, "msyh.ttc"), 0),
            (os.path.join(wf, "simhei.ttf"), None),
            (os.path.join(wf, "simsun.ttc"), 0),
            (os.path.join(wf, "NotoSansSC-VF.ttf"), None),
        ]
    for p in ("/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc",
              "/Library/Fonts/Arial Unicode.ttf"):
        if os.path.exists(p):
            cands.append((p, 0))
    for pat in ("/usr/share/fonts/**/NotoSansCJK*.ttc",
                "/usr/share/fonts/**/wqy-zenhei.ttc",
                "/usr/share/fonts/**/wqy-microhei.ttc",
                "/usr/share/fonts/**/NotoSansSC*.ttf"):
        hit = glob.glob(pat, recursive=True)
        if hit:
            cands.append((hit[0], None))
    return cands


_LABEL_FONT_CANDIDATES = _label_font_candidates()


def _render_label_bar(text, width, font_size=24, color=(255, 255, 255),
                      bg_color=(0, 0, 0)):
    """Render a standalone label strip (RGBA, width × strip_h) placed below an image.
    bg_color may be (R,G,B) for a solid band or (R,G,B,A) with A=0 for transparent."""
    margin = max(font_size // 4, 4)
    font = _make_label_font(font_size)

    # Measure ink height on a tiny canvas to size the strip first.
    meas = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
    th = (meas[3] - meas[1]) if meas else font_size
    strip_h = th + 2 * margin

    bar = Image.new("RGBA", (max(int(width), 1), strip_h), bg_color)
    bd = ImageDraw.Draw(bar)
    cx = int(width) // 2
    # Default anchor is top-left; textbbox gives the ink box relative to (0,0).
    # Place the ink's top-left so the ink block is centered in the strip.
    ink = bd.textbbox((0, 0), text, font=font)
    ink_h = ink[3] - ink[1]
    top = (strip_h - ink_h) // 2 - ink[1]
    left = cx - (ink[2] - ink[0]) // 2 - ink[0]
    bd.text((left, top), text, fill=color, font=font)
    return bar

# ─────────────────────────────────────────────
#  AnimaImageGrid (Enhanced with text labels)
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
                "Show Labels": (
                    ["True", "False"],
                    {"default": "True"},
                ),
                "Label Color": (
                    ["White", "Black", "Yellow", "Cyan", "Magenta", "Red", "Green", "Blue"],
                    {"default": "Black"},
                ),
                "Label Background": (
                    ["Black", "White", "Gray", "Red", "Green", "Blue", "Transparent"],
                    {"default": "White"},
                ),
            },
            "optional": {
                "LoRA Names": ("LORA_NAMES", {"tooltip": "Auto-filled from Anima XY Sampler — LoRA names in image order"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "grid"
    CATEGORY = "Anima/LoRA Comparison"

    LABEL_COLOR_MAP = {
        "White": (255, 255, 255),
        "Black": (0, 0, 0),
        "Yellow": (255, 255, 0),
        "Cyan": (0, 255, 255),
        "Magenta": (255, 0, 255),
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 0, 255),
    }
    
    LABEL_BG_MAP = {
        "Black": (0, 0, 0),
        "White": (255, 255, 255),
        "Gray": (128, 128, 128),
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 0, 255),
        "Transparent": (0, 0, 0, 0),  # Will be handled specially
    }

    def grid(self, **kwargs):
        img_tensor = kwargs["Image"]
        Direction = kwargs.get("Direction", "Horizontal")
        Gap = int(kwargs.get("Gap", 0))
        Show_Labels = kwargs.get("Show Labels", kwargs.get("Show_Labels", "True"))
        Label_Color = kwargs.get("Label Color", kwargs.get("Label_Color", "White"))
        Label_Background = kwargs.get("Label Background", kwargs.get("Label_Background", "Black"))
        LoRA_Names = kwargs.get("LoRA Names", kwargs.get("LoRA_Names"))
        n = img_tensor.shape[0]
        # Gap area is transparent (alpha = 0); labels keep their own background.

        # Parse lora names (with extension stripped)
        lora_names = []
        if LoRA_Names:
            lora_names = [_strip_model_ext(name) for name in LoRA_Names.strip().split('\n') if name.strip()]

        show_labels = (Show_Labels == "True") and bool(lora_names)
        label_font_pct = 10.0  # fixed: font size = 10% of image width

        # Build per-image units: [image | label bar below], no occlusion
        unit_list = []
        for i in range(n):
            img_pil = _tensor_to_pil(img_tensor[i])
            if show_labels:
                label_text = lora_names[i] if i < len(lora_names) else f"Image {i+1}"
                bar = _render_label_bar(
                    label_text,
                    width=img_pil.width,
                    font_size=max(8, int(round(img_pil.width * label_font_pct / 100.0))),
                    color=self.LABEL_COLOR_MAP.get(Label_Color, (255, 255, 255)),
                    bg_color=self.LABEL_BG_MAP.get(Label_Background, (0, 0, 0)),
                )
                # unit is RGBA so the gap above can stay transparent
                unit = Image.new("RGBA", (img_pil.width, img_pil.height + bar.height), (0, 0, 0, 0))
                unit.paste(img_pil.convert("RGBA"), (0, 0))
                unit.paste(bar, (0, img_pil.height))
            else:
                unit = img_pil.convert("RGBA")
            unit_list.append(_pil_to_tensor(unit).squeeze(0))

        # Create grid from units
        if Direction == "Horizontal":
            max_h = max(u.shape[0] for u in unit_list)
            total_w = sum(u.shape[1] for u in unit_list) + Gap * (n - 1)
            canvas = torch.zeros(max_h, total_w, 4, dtype=img_tensor.dtype, device=img_tensor.device)
            # alpha defaults to 0 (transparent) — gap areas show through

            x = 0
            for u in unit_list:
                h, w = u.shape[0], u.shape[1]
                y_off = (max_h - h) // 2
                canvas[y_off:y_off+h, x:x+w, :] = u
                x += w + Gap
        else:
            max_w = max(u.shape[1] for u in unit_list)
            total_h = sum(u.shape[0] for u in unit_list) + Gap * (n - 1)
            canvas = torch.zeros(total_h, max_w, 4, dtype=img_tensor.dtype, device=img_tensor.device)
            # alpha defaults to 0 (transparent) — gap areas show through

            y = 0
            for u in unit_list:
                h, w = u.shape[0], u.shape[1]
                x_off = (max_w - w) // 2
                canvas[y:y+h, x_off:x_off+w, :] = u
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
    "AnimaImageGrid": "Anima Image Grid (with Labels)",
}
