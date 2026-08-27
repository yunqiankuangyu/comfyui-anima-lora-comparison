<table><tr><td><h1>ComfyUI Anima LoRA Comparison</h1></td><td align="right" valign="middle"><a href="README.md">中文</a></td></tr></table>

Batch LoRA comparison plugin for Anima (Cosmos-based) models in ComfyUI.

> Current version: **v0.1.2**

## Nodes

| Node | Description |
|------|-------------|
| **Anima Model Loader** | UNET + CLIP + VAE all-in-one loader |
| **Anima LoRA List** | Select LoRA from dropdown, unified strength, up to 20. Supports Apply Mode (Standard / Anima 3.8B Bridge) |
| **Anima XY Sampler** | Iterate LoRA list, generate one image per LoRA, and output the corresponding LoRA names |
| **Anima Image Grid (with Labels)** | Multi-image layout (horizontal/vertical), adjustable gap, with bottom text labels that auto-follow LoRA names |

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yunqiankuangyu/comfyui-anima-lora-comparison.git
```

Or install via [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) — search for `comfyui-anima-lora-comparison`.

## Usage

### Basic Wiring

![Workflow Example](image.png)

### Anima Model Loader

- `UNET Model`: select the Anima UNET model file
- `Weight Precision`: weight precision (e.g. fp16 / fp32)
- `CLIP Model`: select the CLIP model
- `CLIP Type`: CLIP type
- `CLIP Device`: device for CLIP
- `VAE Model`: select the VAE
- Outputs: `MODEL` / `CLIP` / `VAE`

### Anima LoRA List

- `Strength`: unified strength for all LoRAs
- `LoRA Count`: number of LoRAs to compare (1-20)
- `lora_1` ~ `lora_N`: select LoRA files from dropdown (dynamic slots, count set by LoRA Count)
- `lora_data`: LoRA dataset (optional input)
- `Apply Mode`: choose between Standard and Anima 3.8B Bridge (see below)
- Output: `LORA_LIST`

### Anima 3.8B Bridge Mode

This plugin supports integration with [ComfyUI-Anima-3.8B-LoRA-Bridge](https://github.com/Lakeside529/ComfyUI-Anima-3.8B-LoRA-Bridge) to run **LoRAs trained on different Anima model variants on other variants**.

**When to use Bridge mode:**
- Your LoRA was trained on a different Anima model variant than the one you're loading
- Bridge mode remaps the LoRA layers to match the loaded model's architecture

**When to use Standard mode:**
- Your LoRA matches the architecture of the loaded model (no remapping needed)

**Requirements for Bridge mode:**
1. Install [ComfyUI-Anima-3.8B-LoRA-Bridge](https://github.com/Lakeside529/ComfyUI-Anima-3.8B-LoRA-Bridge) in `custom_nodes/`
2. Load the target model in Anima Model Loader
3. Select "Anima 3.8B Bridge" in the Apply Mode dropdown

### Anima XY Sampler

- `MODEL` / `Positive` / `Negative` / `Latent` / `VAE`: wired from upstream nodes
- `Seed` / `Steps` / `CFG` / `Sampler` / `Scheduler` / `Denoise`: sampling parameters
- `LoRA List` (optional): connect to the `LORA_LIST` output of Anima LoRA List
- Outputs: `IMAGE` (grid) / `LORA_NAMES` (LoRA name per image, auto-fed downstream)

### Anima Image Grid

- `Image`: connect to the `IMAGE` output of Anima XY Sampler
- `Direction`: Horizontal / Vertical
- `Gap`: 0-256 pixels (transparent gap)
- `Show Labels`: whether to show bottom text labels (True/False)
- `Label Color`: label text color (White, Black, Yellow, Cyan, Magenta, Red, Green, Blue)
- `Label Background`: label background color (Black, White, Gray, Red, Green, Blue, Transparent)
- `LoRA Names` (optional): connect `LORA_NAMES` for automatic labeling (zero manual config); leave empty to show "Image 1", "Image 2", etc.

#### Text Label Feature

**Available since v0.1.1**: Add text labels at the bottom of images to easily identify which LoRA each image corresponds to.

**How to use:**
1. Connect the `LORA_NAMES` output of Anima XY Sampler to this node's `LoRA Names` (recommended, zero manual config)
2. Or manually enter LoRA names in the `LoRA Names` box, one per line, in the same order as the images
3. Set `Show Labels` to "True"
4. Adjust label color and background for the best visual effect

The generated images will show the corresponding LoRA names at the bottom — no more guessing which image came from which LoRA!

## License

MIT
