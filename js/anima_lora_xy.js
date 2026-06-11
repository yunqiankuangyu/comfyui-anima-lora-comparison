import { app } from "../../scripts/app.js";

const MAX_SLOTS = 20;
let _loraCache = null;

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
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "AnimaLoraList") return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnNodeCreated?.apply(this, arguments);
            if (!this.properties) this.properties = {};
            if (!this.properties.anima_selections) this.properties.anima_selections = {};

            const self = this;
            requestAnimationFrame(() => self._animaInit());
        };

        const origOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            origOnConfigure?.apply(this, arguments);
            if (data.properties?.anima_selections) {
                if (!this.properties) this.properties = {};
                this.properties.anima_selections = JSON.parse(JSON.stringify(data.properties.anima_selections));
            }
            if (data.properties?.anima_strength !== undefined) {
                if (!this.properties) this.properties = {};
                this.properties.anima_strength = data.properties.anima_strength;
            }
            const self = this;
            requestAnimationFrame(() => self._animaInit());
        };

        nodeType.prototype._animaInit = function () {
            if (this._animaReady) {
                this._animaRebuild();
                return;
            }
            this._animaReady = true;

            const dataW = this.widgets?.find((w) => w.name === "lora_data");
            if (dataW) {
                dataW.hidden = true;
                dataW.computeSize = () => [0, -4];
                dataW.type = "hidden";
                dataW.serialize = false;
            }

            const strengthW = this.widgets?.find((w) => w.name === "权重");
            if (strengthW) {
                strengthW.serialize = false;
                if (this.properties?.anima_strength !== undefined) {
                    strengthW.value = this.properties.anima_strength;
                }
            }

            const countW = this.widgets?.find((w) => w.name === "LoRA数量");
            if (countW) {
                const self = this;
                const origCb = countW.callback;
                countW.callback = function (v) {
                    origCb?.call(this, v);
                    self._animaRebuild();
                };
            }

            if (dataW?.value) {
                try {
                    const parsed = JSON.parse(dataW.value);
                    if (Object.keys(parsed).length > 0) {
                        this.properties.anima_selections = parsed;
                    }
                } catch {}
            }

            this._animaRebuild();
        };

        nodeType.prototype._animaRebuild = function () {
            this._animaRebuilding = true;

            const comboList = ["(none)", ...(_loraCache || [])];
            const countW = this.widgets?.find((w) => w.name === "LoRA数量");
            const count = countW
                ? Math.min(Math.max(countW.value, 1), MAX_SLOTS)
                : 2;

            const sels = this.properties?.anima_selections || {};

            for (const w of this.widgets) {
                if (/^lora_\d+$/.test(w.name) && w.value !== undefined && w.value !== "(none)") {
                    sels[w.name] = w.value;
                }
            }

            for (let i = this.widgets.length - 1; i >= 0; i--) {
                if (/^lora_\d+$/.test(this.widgets[i].name)) {
                    this.widgets.splice(i, 1);
                }
            }

            const countIdx = this.widgets.findIndex((w) => w.name === "LoRA数量");

            for (let i = 1; i <= count; i++) {
                const name = `lora_${i}`;
                const value = sels[name] || "(none)";

                const w = this.addWidget(
                    "combo",
                    name,
                    value,
                    () => {
                        if (!this._animaRebuilding) this._animaSync();
                    },
                    { values: comboList }
                );
                w.serialize = false;

                const wIdx = this.widgets.indexOf(w);
                const targetIdx = countIdx + i;
                if (wIdx !== targetIdx) {
                    this.widgets.splice(wIdx, 1);
                    this.widgets.splice(targetIdx, 0, w);
                }
            }

            this._animaRebuilding = false;
            this._animaSync();

            const sz = this.computeSize();
            this.size[0] = Math.max(this.size[0], sz[0]);
            this.size[1] = sz[1];
            if (this.graph) this.graph.setDirtyCanvas(true, true);
        };

        nodeType.prototype._animaSync = function () {
            const sels = {};
            for (const w of this.widgets) {
                if (/^lora_\d+$/.test(w.name) && w.value && w.value !== "(none)") {
                    sels[w.name] = w.value;
                }
            }
            if (!this.properties) this.properties = {};
            this.properties.anima_selections = sels;

            const strengthW = this.widgets?.find((w) => w.name === "权重");
            if (strengthW) this.properties.anima_strength = strengthW.value;

            const dataW = this.widgets?.find((w) => w.name === "lora_data");
            if (dataW) dataW.value = JSON.stringify(sels);
        };

        // 按 R 刷新时 ComfyUI 调用此方法
        nodeType.prototype.refreshComboInNode = async function (defs) {
            await getLoraList(true); // 强制刷新缓存
            this._animaRebuild();    // 用最新列表重建 combo
        };
    },
});
