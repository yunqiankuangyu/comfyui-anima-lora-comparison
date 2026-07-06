# ComfyUI Anima LoRA Comparison

Batch LoRA comparison plugin for Anima (Cosmos-based) models in ComfyUI.

## Nodes

| Node | Description |
|------|-------------|
| **Anima Model Loader** | UNET + CLIP + VAE all-in-one loader |
| **Anima LoRA List** | Select LoRA from dropdown, unified strength, up to 20 |
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

### Image Grid

- **Direction**: Horizontal / Vertical
- **Gap**: 0-256 pixels
- **Color**: Black, White, Gray, Red, Green, Blue

## License

MIT
