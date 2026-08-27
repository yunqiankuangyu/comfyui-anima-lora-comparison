<table><tr><td><h1>ComfyUI Anima LoRA Comparison</h1></td><td align="right" valign="middle"><a href="README.md">中文</a></td></tr></table>

Batch LoRA comparison plugin for Anima (Cosmos-based) models in ComfyUI.

## Nodes

| Node | Description |
|------|-------------|
| **Anima Model Loader** | UNET + CLIP + VAE all-in-one loader |
| **Anima LoRA List** | Select LoRA from dropdown, unified strength, up to 20. Supports Apply Mode (Standard / Anima 3.8B Bridge) |
| **Anima XY Sampler** | Iterate LoRA list, generate one image per LoRA |
| **Anima Image Grid** | Multi-image layout, horizontal/vertical, adjustable gap and color. **New: image text labels supported** |

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yunqiankuangyu/comfyui-anima-lora-comparison.git
```

Or install via [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) — search for `Anima LoRA XY`.

## Usage

### Basic Wiring

![Workflow Example](image.png)

### LoRA List

In the Anima LoRA List node:
- `LoRA Count`: number of LoRAs to compare (1-20)
- `lora_1` ~ `lora_N`: select LoRA files from dropdown
- `Strength`: unified strength for all LoRAs
- `Apply Mode`: choose between Standard and Anima 3.8B Bridge (see below)

### Anima 3.8B Bridge Mode

This plugin supports integration with [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) to run **LoRAs trained on different Anima model variants on other variants**.

**When to use Bridge mode:**
- Your LoRA was trained on a different Anima model variant than the one you're loading
- Bridge mode remaps the LoRA layers to match the loaded model's architecture

**When to use Standard mode:**
- Your LoRA matches the architecture of the loaded model (no remapping needed)

**Requirements for Bridge mode:**
1. Install [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) in `custom_nodes/`
2. Load the target model in Anima Model Loader
3. Select "Anima 3.8B Bridge" in the Apply Mode dropdown

### Image Grid

- **Direction**: Horizontal / Vertical
- **Gap**: 0-256 pixels
- **Color**: Black, White, Gray, Red, Green, Blue
- **Show Labels**: whether to show image labels (True/False)
- **Label Font Size**: label font size (8-72)
- **Label Color**: label text color (White, Black, Yellow, Cyan, Magenta, Red, Green, Blue)
- **Label Background**: label background color (Black, White, Gray, Red, Green, Blue, Transparent)
- **LoRA Names** (optional): input LoRA names, one per line, in the same order as the images. Leave empty to show "Image 1", "Image 2", etc.

#### Text Label Feature

**New in v0.1.1**: Add text labels at the bottom of images to easily identify which LoRA each image corresponds to.

**How to use:**
1. Enter LoRA names in the `LoRA Names` input box, one per line
2. Make sure the order matches the generated images
3. Set `Show Labels` to "True"
4. Adjust font size, color, and background for the best visual effect

**Example:**
```
lora_style1
lora_style2
lora_expression
```

The generated images will show the corresponding LoRA names at the bottom — no more guessing which image came from which LoRA!

## License

MIT
