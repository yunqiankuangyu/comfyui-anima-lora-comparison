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

### Anima-2.9B Support

This plugin also supports Anima-2.9B (the 40-block depth-expanded model). Depending on which model your LoRA was trained on, there are two cases:

**Case 1: LoRA trained on Anima-2.9B (native 40-block LoRA)**
- Load the 2.9B model in Anima Model Loader
- Set Apply Mode to **Standard**
- No extra plugins needed; just generate normally

**Case 2: LoRA trained on Anima-Base v1.0 / v1.1 (28-block LoRA), but generating on the 2.9B model**
- Keep Apply Mode at **Standard**
- You must ALSO install both of the following load-time patches (both required, neither alone is enough). They remap the 28-block LoRA weights onto the 2.9B 40-block layout:
  1. [ComfyUI-Anima-2.9B-blocksPatch](https://github.com/sparklingcoffee777/ComfyUI-Anima-2.9B-blocksPatch) — makes ComfyUI correctly recognize the 2.9B 40-block architecture (otherwise the model loads truncated as 28 blocks)
  2. [ComfyUI-Anima-2.9B-loraPatch](https://github.com/sparklingcoffee777/ComfyUI-Anima-2.9B-loraPatch) — remaps the 28-block LoRA layer indices to their 2.9B positions
- These patches are ComfyUI load-time monkey-patches that add no canvas nodes, so at the node level you still use Standard; the cross-block remapping is handled underneath by them

> Note: Case 1 uses a native 2.9B LoRA whose architecture matches the model, so Standard suffices. The two patches in Case 2 apply only to the "old LoRA + 2.9B model" combo and are unrelated to Case 1.

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
