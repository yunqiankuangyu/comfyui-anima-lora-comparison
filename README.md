<table><tr><td><h1>ComfyUI Anima LoRA Comparison</h1></td><td align="right" valign="middle"><a href="README_EN.md">English</a></td></tr></table>

Anima（Cosmos 系列）模型的批量 LoRA 对比插件。

## 节点

| 节点 | 说明 |
|------|------|
| **Anima Model Loader** | UNET + CLIP + VAE 一体化加载器 |
| **Anima LoRA List** | 下拉选择 LoRA，统一强度，最多 20 个。支持 Apply Mode（Standard / Anima 3.8B Bridge） |
| **Anima XY Sampler** | 遍历 LoRA 列表，每个 LoRA 生成一张图 |
| **Anima Image Grid** | 多图拼接，水平/垂直，可调间距和颜色 |

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yunqiankuangyu/comfyui-anima-lora-comparison.git
```

或通过 [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) 安装——搜索 `comfyui-anima-lora-comparison`。

## 使用方法

### 基本接线

![工作流示例](image.png)

### LoRA List 节点

- `LoRA Count`：要对比的 LoRA 数量（1-20）
- `lora_1` ~ `lora_N`：下拉选择 LoRA 文件
- `Strength`：所有 LoRA 统一强度
- `Apply Mode`：选择 Standard 或 Anima 3.8B Bridge（见下文）

### Anima 3.8B Bridge 模式

本插件支持与 [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) 联动，**让不同 Anima 模型变体训练的 LoRA 在其他变体上运行**。

**何时使用 Bridge 模式：**
- 你的 LoRA 训练时用的模型与当前加载的模型不是同一个变体
- Bridge 模式会自动重映射 LoRA 层以匹配当前加载模型的架构

**何时使用 Standard 模式：**
- 你的 LoRA 与当前加载的模型架构一致（无需重映射）

**Bridge 模式使用条件：**
1. 安装 [comfyui-anima-3-8b-lora-bridge](https://github.com/user/comfyui-anima-3-8b-lora-bridge) 到 `custom_nodes/`
2. 在 Anima Model Loader 中加载目标模型
3. 在 Apply Mode 下拉菜单中选择 "Anima 3.8B Bridge"

### Image Grid 节点

- **Direction**：水平 / 垂直
- **Gap**：0-256 像素
- **Color**：Black, White, Gray, Red, Green, Blue

## 开源协议

MIT
