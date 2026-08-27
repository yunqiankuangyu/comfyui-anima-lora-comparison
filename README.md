<table><tr><td><h1>ComfyUI Anima LoRA Comparison</h1></td><td align="right" valign="middle"><a href="README_EN.md">English</a></td></tr></table>

Anima（Cosmos 系列）模型的批量 LoRA 对比插件。

> 当前版本：**v0.1.2**

## 节点

| 节点 | 说明 |
|------|------|
| **Anima Model Loader** | UNET + CLIP + VAE 一体化加载器 |
| **Anima LoRA List** | 下拉选择 LoRA，统一强度，最多 20 个。支持 Apply Mode（Standard / Anima 3.8B Bridge） |
| **Anima XY Sampler** | 遍历 LoRA 列表，每个 LoRA 生成一张图，并输出对应 LoRA 名称 |
| **Anima Image Grid (with Labels)** | 多图拼接（水平/垂直），可调间距，支持图片底部文字标注（自动跟随 LoRA 名称） |

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yunqiankuangyu/comfyui-anima-lora-comparison.git
```

或通过 [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) 安装——搜索 `comfyui-anima-lora-comparison`。

## 使用方法

### 基本接线

![工作流示例](image.png)

### Anima Model Loader

- `UNET Model`：选择 Anima UNET 模型文件
- `Weight Precision`：权重精度（如 fp16 / fp32）
- `CLIP Model`：选择 CLIP 模型
- `CLIP Type`：CLIP 类型
- `CLIP Device`：CLIP 运行设备
- `VAE Model`：选择 VAE
- 输出：`MODEL` / `CLIP` / `VAE`

### Anima LoRA List 节点

- `Strength`：所有 LoRA 统一强度
- `LoRA Count`：要对比的 LoRA 数量（1-20）
- `lora_1` ~ `lora_N`：下拉选择 LoRA 文件（动态槽位，数量由 LoRA Count 决定）
- `lora_data`：LoRA 数据集（可选输入）
- `Apply Mode`：选择 Standard 或 Anima 3.8B Bridge（见下文）
- 输出：`LORA_LIST`

### Anima 3.8B Bridge 模式

本插件支持与 [ComfyUI-Anima-3.8B-LoRA-Bridge](https://github.com/Lakeside529/ComfyUI-Anima-3.8B-LoRA-Bridge) 联动，**让不同 Anima 模型变体训练的 LoRA 在其他变体上运行**。

**何时使用 Bridge 模式：**
- 你的 LoRA 训练时用的模型与当前加载的模型不是同一个变体
- Bridge 模式会自动重映射 LoRA 层以匹配当前加载模型的架构

**何时使用 Standard 模式：**
- 你的 LoRA 与当前加载的模型架构一致（无需重映射）

**Bridge 模式使用条件：**
1. 安装 [ComfyUI-Anima-3.8B-LoRA-Bridge](https://github.com/Lakeside529/ComfyUI-Anima-3.8B-LoRA-Bridge) 到 `custom_nodes/`
2. 在 Anima Model Loader 中加载目标模型
3. 在 Apply Mode 下拉菜单中选择 "Anima 3.8B Bridge"

### Anima XY Sampler 节点

- `MODEL` / `Positive` / `Negative` / `Latent` / `VAE`：来自上游节点的连接
- `Seed` / `Steps` / `CFG` / `Sampler` / `Scheduler` / `Denoise`：采样参数
- `LoRA List`（可选）：接入 Anima LoRA List 的 `LORA_LIST`
- 输出：`IMAGE`（拼接图） / `LORA_NAMES`（各图对应 LoRA 名称，自动传给下游）

### Anima Image Grid 节点

- `Image`：接入 Anima XY Sampler 的 `IMAGE`
- `Direction`：水平 / 垂直
- `Gap`：0-256 像素（透明间隙）
- `Show Labels`：是否显示图片底部文字标签（True/False）
- `Label Color`：标签文字颜色（White, Black, Yellow, Cyan, Magenta, Red, Green, Blue）
- `Label Background`：标签背景颜色（Black, White, Gray, Red, Green, Blue, Transparent）
- `LoRA Names`（可选）：接入 `LORA_NAMES` 即可自动标注，无需手动输入；留空则显示 "Image 1", "Image 2" 等

#### 文字标注功能

**v0.1.1 起支持**：在图片底部添加文字标签，轻松识别每张图对应的 LoRA。

**使用方法：**
1. 将 Anima XY Sampler 的 `LORA_NAMES` 输出接入本节点的 `LoRA Names`（推荐，零手工配置）
2. 或手动在 `LoRA Names` 输入框中逐行输入 LoRA 名称，顺序需与图片一致
3. 开启 `Show Labels` 为 "True"
4. 调整标签颜色和背景以获得最佳视觉效果

这样生成的图片底部会显示对应的 LoRA 名称，再也不用分不清哪张图是哪个 LoRA 做的了！

## 开源协议

MIT
