# ComfyUI Anima LoRA Comparison

Batch LoRA comparison plugin for Anima (Cosmos-based) models in ComfyUI.

## Nodes

| Node | Description |
|------|-------------|
| **Anima Model Loader** | UNET + CLIP + VAE all-in-one loader |
| **Anima LoRA List** | Select LoRA from dropdown, unified strength, up to 20. Supports Apply Mode (Standard / Anima 3.8B Bridge) |
| **Anima XY Sampler** | Iterate LoRA list, generate one image per LoRA |
| **Anima Image Grid** | Multi-image layout, horizontal/vertical, adjustable gap and color |

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

This plugin supports联动 with [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) to run **2B-trained LoRAs on the 3.8B (52-block) UNET**.

**When to use Bridge mode:**
- Your LoRA was trained on Anima 2B (the smaller model)
- You want to run it on Anima 3.8B (the larger 52-block model)
- Bridge mode remaps the LoRA layers to match the 3.8B architecture

**When to use Standard mode:**
- Your LoRA was natively trained on Anima 3.8B
- You're using LoRA that already targets the 52-block architecture
- Standard mode applies LoRA without remapping

**Requirements for Bridge mode:**
1. Install [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) in `custom_nodes/`
2. Load a 3.8B UNET (52 blocks) in the Anima Model Loader
3. Select "Anima 3.8B Bridge" in the Apply Mode dropdown

### Image Grid

- **Direction**: Horizontal / Vertical
- **Gap**: 0-256 pixels
- **Color**: Black, White, Gray, Red, Green, Blue

## License

MIT
