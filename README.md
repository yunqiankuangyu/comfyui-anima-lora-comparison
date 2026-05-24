# ComfyUI Anima LoRA XY

批量 LoRA 对比测试插件，适用于 Anima（Cosmos-based）模型。

Batch LoRA comparison plugin for Anima (Cosmos-based) models in ComfyUI.

## 节点 / Nodes

| 节点 | 说明 |
|------|------|
| **Anima 模型加载器** | UNET + CLIP + VAE 一体化加载 |
| **Anima LoRA 列表** | 下拉选择 LoRA，统一权重，支持最多 20 个 |
| **Anima XY 采样器** | 遍历 LoRA 列表，每个 LoRA 生成一张图 |
| **Anima 图像排版** | 多图拼接，支持横排/竖排、调整间距和颜色 |

## 安装 / Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yunqiankuangyu/comfyui-anima-lora-xy.git
```

或通过 [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) 搜索 `Anima LoRA XY` 安装。

## 使用 / Usage

### 基本接线

```
[Anima 模型加载器] → 模型 / CLIP / VAE
        ↓
  CLIPTextEncode(正向) ─→ positive ─┐
  CLIPTextEncode(反向) ─→ negative ─┤
  EmptyLatentImage ───→ latent ─────┤
  ModelSamplingAuraFlow ─→ 模型 ────┤
                                     ↓
  [Anima LoRA 列表] → LoRA列表 ──→ [Anima XY 采样器] → 图像列表
                                                      ↓
                                              [Anima 图像排版] → PreviewImage
```

### LoRA 列表示例

在 Anima LoRA 列表节点中：
- `lora_count`：设置要对比的 LoRA 数量（1-20）
- `lora_1` ~ `lora_N`：下拉选择 LoRA 文件
- `strength`：所有 LoRA 共享的统一权重

### 图像排版

- **方向**：左右排列 / 上下排列
- **间距**：0-256 像素
- **颜色**：黑色、白色、灰色、红色、绿色、蓝色

## 许可证 / License

MIT
