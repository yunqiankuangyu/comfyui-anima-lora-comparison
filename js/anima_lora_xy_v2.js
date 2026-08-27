import { app } from "../../scripts/app.js";

const MAX_SLOTS = 20;
let _loraCache = null;

// ── Chinese input/widget/output labels (self-contained, no external translator) ──
const ANIMA_ZH = {
  AnimaModelLoader: {
    title: "Anima 模型加载器",
    inputs: {
      "UNET Model": "UNET模型",
      "Weight Precision": "权重精度",
      "CLIP Model": "CLIP模型",
      "CLIP Type": "CLIP类型",
      "CLIP Device": "CLIP设备",
      "VAE Model": "VAE模型",
    },
    outputs: { MODEL: "模型", CLIP: "CLIP", VAE: "VAE" },
  },
  AnimaLoraList: {
    title: "Anima LoRA 列表",
    inputs: {
      Strength: "权重",
      "LoRA Count": "LoRA数量",
      lora_data: "LoRA数据",
      "Apply Mode": "应用模式",
    },
    outputs: { LORA_LIST: "LoRA列表" },
  },
  AnimaXYSampler: {
    title: "Anima XY 采样器",
    inputs: {
      MODEL: "模型",
      Positive: "正向提示",
      Negative: "反向提示",
      Latent: "潜空间",
      VAE: "VAE",
      Seed: "种子",
      Steps: "步数",
      CFG: "CFG",
      Sampler: "采样器",
      Scheduler: "调度器",
      Denoise: "降噪",
      "LoRA List": "LoRA列表",
    },
    outputs: { IMAGE: "图像", LORA_NAMES: "LoRA名称" },
  },
  AnimaImageGrid: {
    title: "Anima 图像排版",
    inputs: {
      Image: "图像",
      Direction: "方向",
      Gap: "间距",
      "Show Labels": "显示标签",
      "Label Color": "标签颜色",
      "Label Background": "标签背景",
      "LoRA Names": "LoRA名称",
    },
    outputs: { IMAGE: "图像" },
  },
};

// ── Locale detection ──
// Confirmed from frontend source (settingStore-*.js / GraphView-*.js):
//   - The live language lives in ComfyUI's setting store, NOT localStorage.
//     localStorage["Comfy.Settings.Comfy.Locale"] is ALWAYS null (verified by probe).
//   - Read it via app.extensionManager.setting.get("Comfy.Locale") (reactive,
//     returns "zh" / "en" / "zh-TW" / ... exactly — locale codes, NOT "zh-CN").
//   - <html lang> is NOT updated on switch, and app.userLocale does not exist.
//     Skill 铁律第4条: never use <html lang> / app.userLocale.
// Empty (unset) → English (ComfyUI's default language).
function _getLang() {
  let lang = "";
  try {
    // Primary, authoritative source: ComfyUI setting store.
    if (app && app.extensionManager && app.extensionManager.setting) {
      lang = app.extensionManager.setting.get("Comfy.Locale") || "";
    }
  } catch (e) {}
  return String(lang).replace(/["']/g, "").toLowerCase();
}

// Chinese UI ("zh"/"zh-TW"/"chinese") → inject Chinese.
// English ("en"/"english") OR empty (unset = ComfyUI default English) → leave native.
function _isChineseLocale() {
  const lang = _getLang();
  if (!lang) return false;            // unset → English default
  if (lang.startsWith("en") || lang.includes("english")) return false;
  return lang.includes("zh") || lang.includes("chinese");
}

// Apply / restore labels based on current language.
// When Chinese: inject Chinese (storing the original English first).
// When not Chinese: restore the stored original English — never stale Chinese.
function _applyAnimaLabels(node) {
  const map = ANIMA_ZH[node.constructor?.comfyClass || node.constructor?.type];
  if (!map) return;
  const zh = _isChineseLocale();

  // input sockets
  if (node.inputs) {
    for (const it of node.inputs) {
      if (!(it.name in (map.inputs || {}))) continue;
      if (zh) {
        if (it._animaOrigLabel === undefined) it._animaOrigLabel = it.label;
        it.label = map.inputs[it.name];
      } else if (it._animaOrigLabel !== undefined) {
        it.label = it._animaOrigLabel;
      }
    }
  }
  // widgets (parameters)
  if (node.widgets) {
    for (const w of node.widgets) {
      if (!w || !w.name) continue;
      let target = null;
      if (w.name in (map.inputs || {})) target = map.inputs[w.name];
      else if (/^lora_\d+$/.test(w.name)) target = "LoRA " + w.name.split("_")[1];
      if (target === null) continue;
      if (zh) {
        if (w._animaOrigLabel === undefined) w._animaOrigLabel = w.label;
        w.label = target;
      } else if (w._animaOrigLabel !== undefined) {
        w.label = w._animaOrigLabel;
      }
    }
  }
  // output sockets
  if (node.outputs) {
    for (const ot of node.outputs) {
      if (!(ot.name in (map.outputs || {}))) continue;
      if (zh) {
        if (ot._animaOrigLabel === undefined) ot._animaOrigLabel = ot.label;
        ot.label = map.outputs[ot.name];
      } else if (ot._animaOrigLabel !== undefined) {
        ot.label = ot._animaOrigLabel;
      }
    }
  }
  if (node.graph) node.graph.setDirtyCanvas(true, true);
}

// Re-run label logic across all existing anima nodes (used on language switch).
function _applyAllAnimaNodes() {
  try {
    const nodes = (app.graph && app.graph.nodes) || [];
    for (const n of nodes) {
      const cls = n.constructor?.comfyClass || n.constructor?.type;
      if (cls && cls in ANIMA_ZH) _applyAnimaLabels(n);
    }
  } catch (e) {}
}

async function getLoraList(forceRefresh = false) {
    if (forceRefresh) _loraCache = null;
    if (_loraCache) return _loraCache;
    try {
        const resp = await fetch("/models/loras");
        _loraCache = resp.ok ? await resp.json() : [];
    } catch {
        _loraCache = [];
    }
    return _loraCache;
}

app.registerExtension({
    name: "anima.lora_comparison",

    async init() {
        await getLoraList();
        // ComfyUI stores the live language in its setting store
        // (app.extensionManager.setting.get("Comfy.Locale")), NOT localStorage
        // (verified null). It does NOT emit a DOM event on switch, so we poll
        // (cheap) and re-apply labels when the value changes. Never rely on
        // <html lang> / app.userLocale (they don't update) — skill 铁律第4条.
        let _lastLang = _getLang();
        setInterval(() => {
            const cur = _getLang();
            if (cur !== _lastLang) {
                _lastLang = cur;
                _applyAllAnimaNodes();
            }
        }, 1000);

        // ── Debug probe (opt-in) ──
        // Only shows when URL has ?anima_probe=1. Renders a fixed black/green
        // overlay reporting the live locale value + our Chinese/English decision,
        // so the user can screenshot without opening DevTools.
        if (location.search.includes("anima_probe=1")) {
            const pre = document.createElement("pre");
            pre.style.cssText =
                "position:fixed;left:8px;bottom:8px;z-index:99999;margin:0;" +
                "padding:8px 10px;background:#000;color:#0f0;font:12px/1.4 monospace;" +
                "white-space:pre-wrap;max-width:60vw;pointer-events:none;opacity:.9;";
            document.body.appendChild(pre);
            const _render = () => {
                let storeVal = "<unavailable>";
                try {
                    if (app && app.extensionManager && app.extensionManager.setting)
                        storeVal = app.extensionManager.setting.get("Comfy.Locale");
                } catch (e) { storeVal = "<err>"; }
                pre.textContent =
                    "[anima probe]\n" +
                    "setting store Comfy.Locale = " + JSON.stringify(storeVal) + "\n" +
                    "_getLang() = " + JSON.stringify(_getLang()) + "\n" +
                    "=> inject Chinese? " + (_isChineseLocale() ? "YES" : "NO (English/native)");
            };
            _render();
            setInterval(_render, 1000);
        }
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        // Chinese label injection for ALL anima nodes (self-contained, locale-aware)
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnNodeCreated?.apply(this, arguments);
            // Run after dynamic widgets (AnimaLoraList) settle
            const self = this;
            requestAnimationFrame(() => _applyAnimaLabels(self));
            setTimeout(() => _applyAnimaLabels(self), 60);
        };

        if (nodeData.name !== "AnimaLoraList") return;
        // ---- lifecycle hooks ----
        // (onNodeCreated already wrapped above for Chinese labels; just add init logic)
        const origOnNodeCreatedInner = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnNodeCreatedInner?.apply(this, arguments);
            if (!this.properties) this.properties = {};
            if (!this.properties.anima_selections) this.properties.anima_selections = {};
            var self = this;
            requestAnimationFrame(() => self._animaInit());
        };

        const origOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            origOnConfigure?.apply(this, arguments);

            // Restore selections from lora_data widget value (primary source)
            var dataW = this.widgets?.find((w) => w.name === "lora_data");
            if (dataW?.value) {
                try {
                    var parsed = JSON.parse(dataW.value);
                    if (Object.keys(parsed).length > 0) {
                        this.properties.anima_selections = parsed;
                    }
                } catch {}
            }

            // Fallback: also try from saved properties (backwards compat)
            if (!Object.keys(this.properties.anima_selections || {}).length && data.properties?.anima_selections) {
                this.properties.anima_selections = JSON.parse(
                    JSON.stringify(data.properties.anima_selections)
                );
            }

            if (data.properties?.anima_strength !== undefined) {
                this.properties.anima_strength = data.properties.anima_strength;
            }

            // Delay init to let ComfyUI restore widget values first
            var self = this;
            setTimeout(() => self._animaInit(), 50);
        };

        // ---- sync: read all combos → write lora_data + properties ----
        nodeType.prototype._animaSync = function () {
            var countW = this.widgets?.find((w) => w.name === "LoRA Count");
            var count = countW
                ? Math.min(Math.max(countW.value, 1), MAX_SLOTS)
                : 1;

            var sels = {};
            for (var i = 1; i <= count; i++) {
                var w = this.widgets?.find((x) => x.name === "lora_" + i);
                if (w && w.value && w.value !== "(none)") {
                    sels["lora_" + i] = w.value;
                }
            }
            this.properties.anima_selections = sels;

            var dataW = this.widgets?.find((w) => w.name === "lora_data");
            if (dataW) dataW.value = JSON.stringify(sels);

            var strengthW = this.widgets?.find((w) => w.name === "Strength");
            if (strengthW)
                this.properties.anima_strength = strengthW.value;
        };

        // ---- init ----
        nodeType.prototype._animaInit = function () {
            if (this._animaReady) {
                this._animaRebuild(true);
                return;
            }
            this._animaReady = true;

            var dataW = this.widgets?.find((w) => w.name === "lora_data");
            if (dataW) {
                // Hide visually but KEEP serialize=true so the value persists in workflow
                dataW.hidden = true;
                dataW.computeSize = () => [0, -4];
            }

            var strengthW = this.widgets?.find((w) => w.name === "Strength");
            if (strengthW) {
                strengthW.serialize = false;
                if (this.properties?.anima_strength !== undefined) {
                    strengthW.value = this.properties.anima_strength;
                }
            }

            var countW = this.widgets?.find((w) => w.name === "LoRA Count");
            if (countW) {
                var self = this;
                var origCb = countW.callback;
                countW.callback = function (v) {
                    origCb?.call(this, v);
                    self._animaRebuild(false);
                    self._animaSync();
                };
            }

            this._animaRebuild(false);

            // Fallback: if live widgets are empty after rebuild, force-write from saved properties
            var saved = this.properties?.anima_selections;
            if (saved && Object.keys(saved).length > 0) {
                var _hasData = false;
                for (var i = 1; i <= 20; i++) {
                    var w = this.widgets?.find((x) => x.name === "lora_" + i);
                    if (w && w.value && w.value !== "(none)") { _hasData = true; break; }
                }
                if (!_hasData) {
                    for (var i = 1; i <= 20; i++) {
                        var w = this.widgets?.find((x) => x.name === "lora_" + i);
                        if (w && saved["lora_" + i]) w.value = saved["lora_" + i];
                    }
                    this._animaSync();
                }
            }
        };

        // ---- rebuild ----
        // fromLoad=true: seed from properties only (ignore live widgets)
        // fromLoad=false: read live widgets, extend by inheritance
        nodeType.prototype._animaRebuild = function (fromLoad) {
            this._animaRebuilding = true;

            var comboList = ["(none)", ...(_loraCache || [])];
            var countW = this.widgets?.find((w) => w.name === "LoRA Count");
            var count = countW
                ? Math.min(Math.max(countW.value, 1), MAX_SLOTS)
                : 2;

            var saved = this.properties?.anima_selections || {};
            var ordered = [];

            if (fromLoad) {
                for (var i = 1; i <= count; i++) {
                    if (saved["lora_" + i]) ordered.push(saved["lora_" + i]);
                }
            } else {
                // Read current live widgets
                var live = [];
                for (var i = 1; i <= MAX_SLOTS; i++) {
                    var w = this.widgets?.find(function (x) {
                        return x.name === "lora_" + i;
                    });
                    if (w && w.value && w.value !== "(none)") live.push(w.value);
                }
                var prevCount = this._animaPrevCount ?? count;
                var keep = Math.min(live.length, prevCount, count);
                for (var i = 0; i < keep; i++) ordered.push(live[i]);
                this._animaPrevCount = count;
            }

            // Extend by inheriting last slot
            while (ordered.length < count) {
                ordered.push(
                    ordered.length ? ordered[ordered.length - 1] : "(none)"
                );
            }
            if (ordered.length > count) ordered.length = count;

            // Remove all existing lora widgets
            for (var i = this.widgets.length - 1; i >= 0; i--) {
                if (/^lora_\d+$/.test(this.widgets[i].name)) {
                    this.widgets.splice(i, 1);
                }
            }

            var countIdx = this.widgets.findIndex(
                (w) => w.name === "LoRA Count"
            );

            // Create new lora widgets
            for (var i = 1; i <= count; i++) {
                var name = "lora_" + i;
                var value = ordered[i - 1];

                var w = this.addWidget(
                    "combo",
                    name,
                    value,
                    () => {
                        if (!this._animaRebuilding) this._animaSync();
                    },
                    { values: comboList }
                );
                w.serialize = false;

                // Reorder: place after LoRA Count
                var wIdx = this.widgets.indexOf(w);
                var targetIdx = countIdx + i;
                if (wIdx !== targetIdx) {
                    this.widgets.splice(wIdx, 1);
                    this.widgets.splice(targetIdx, 0, w);
                }
            }

            this._animaRebuilding = false;

            // ★ CRITICAL: Force-set widget values AFTER all adds/reorders.
            // LiteGraph may restore old values during addWidget.
            for (var i = 1; i <= count; i++) {
                var w = this.widgets.find(function (x) {
                    return x.name === "lora_" + i;
                });
                if (w) w.value = ordered[i - 1];
            }

            var sz = this.computeSize();
            this.size[0] = Math.max(this.size[0], sz[0]);
            this.size[1] = sz[1];
            if (this.graph) this.graph.setDirtyCanvas(true, true);
            _applyAnimaLabels(this);
        };

        // ---- R key refresh ----
        nodeType.prototype.refreshComboInNode = async function (defs) {
            await getLoraList(true);
            this._animaRebuild(true);
        };
    },
});
