# Changelog

本文件记录 `comfyui-anima-lora-comparison` 的所有重要变更。
格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号遵循语义化版本。

## [0.1.4] - 2026-11-06

### 新增
- **Apply Mode 自动切换（3.8B 场景）**：当加载的模型为 3.8B（52-block）且所选 LoRA 非 3.8B 层（如 Base/1.0 的 28-block LoRA、2.9B 的 40-block LoRA）时，自动将 Apply Mode 从 Standard 切换为 Anima 3.8B Bridge 并联动 Bridge 插件，用户不再需要手动在列表末行切换。
- 新增 `detect_lora_blocks()`：仅读取 safetensors 头部（不加载权重）识别 LoRA 的 block 层数（28/40/52），结果按 路径+mtime 缓存。

### 修复
- Bridge 插件缺失时给出明确报错，并附带 ComfyUI-Anima-3.8B-LoRA-Bridge 安装链接（不再抛出裸 `ImportError`）。

### 说明
- 2.9B（40-block）与 28-block LoRA 的组合仍由外部 blocksPatch / loraPatch 插件在 Standard 模式下自动处理，本版本不做改动。
- 版本号提升至 `0.1.4`。

## [0.1.3] - 2026-11-06

### 修复
- **LoRA 数量槽位在 ComfyUI ≥ 0.43 下错位**：新版前端改写了 `widgets_values` 的还原逻辑（位置/名字映射），导致 `LoRA Count` 输入框被还原成 `lora_data` 的 JSON 对象，进而使动态 LoRA 列表在重启/重载后无法生成（`Math.max({},1)` 得到 `NaN`，循环一次都不执行）。
- 修复方式：节点不再依赖 `LoRA Count` 的 widget 值来取数量，而是从保存的 `properties.anima_selections`（走对象式还原，不受位置错位影响）反推最大 `lora_N` 序号确定数量，并在检测到异常时自愈写回。
- `nodes.py` 的 `generate()` 对 `LoRA Count` 增加 `int()` 防御，避免异常输入在服务端崩溃。

### 维护
- 版本号提升至 `0.1.3`。

## [0.1.2] - 2026-08

### 新增
- README 新增 **Anima-2.9B 支持** 章节：区分两种情形
  - 情形一：LoRA 在 2.9B 上训练（原生 40-block LoRA）→ `Apply Mode` 选 **Standard**，无需额外插件。
  - 情形二：LoRA 在 Anima-Base v1.0/v1.1 训练（28-block LoRA）但在 2.9B 出图 → `Apply Mode` 仍选 **Standard**，并需同时安装 `ComfyUI-Anima-2.9B-blocksPatch` 与 `ComfyUI-Anima-2.9B-loraPatch` 两个加载期补丁。
- README 新增 **Anima 3.8B Bridge 模式** 说明：与 `ComfyUI-Anima-3.8B-LoRA-Bridge` 联动，让不同 Anima 变体训练的 LoRA 在其他变体上运行（自动重映射 LoRA 层）。

### 修复
- **i18n 语言检测**：由读取 `localStorage`（始终为 null）改为读取 ComfyUI setting store，修复中文化注入在部分环境下失效的问题。
- `AnimaModelLoader` 兼容 ComfyUI 0.33+ 的 kwargs 调用方式。
- LoRA 选择记忆：节点重载（`fromLoad=true`）/ 刷新 / 重启后，通过 LiteGraph `properties` + `setTimeout` 回退恢复选择，不再依赖 `widgets_values` 索引顺序。

### 文档
- 中英文 README 同步；`INPUT_TYPES` 描述对齐（移除不存在的 Color / Label Font Size 项，修正 Bridge 链接）。
- 为 `AnimaImageGrid` 的文字标注功能补充中英文文档。

### 维护
- 版本号提升至 `0.1.2`。
- 停止追踪 `node.zip` 构建产物（`.gitignore` 排除）。

## [0.1.1] - 2026-08

### 新增
- `AnimaImageGrid` 支持图片底部**文字标注**：CJK 字体 + RGBA 透明标签条；接入 `LORA_NAMES` 可自动跟随对应 LoRA 名称，无需手动输入。

### 修复
- LoRA 选择持久化，并跨刷新 / 重启同步。

## [0.1.0] - 2026-08

### 初始版本
- 四个节点：
  - **Anima Model Loader**：UNET + CLIP + VAE 一体化加载。
  - **Anima LoRA List**：下拉选择 LoRA、统一强度，最多 20 个；JS 动态创建槽位；支持 `Apply Mode`（Standard / Anima 3.8B Bridge）。
  - **Anima XY Sampler**：遍历 LoRA 列表逐张出图，输出 `IMAGE` 与各图对应 `LORA_NAMES`。
  - **Anima Image Grid**：多图拼接（水平 / 垂直），可调间距。
- LoRA 列表记忆使用 LiteGraph `properties` 存储（`lora_data` 隐藏字段作为旧工作流兼容备份）。
- 收录 ComfyUI Manager（搜索 `comfyui-anima-lora-comparison`）。
