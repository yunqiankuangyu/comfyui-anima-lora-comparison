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
        // ---- lifecycle hooks ----
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origOnNodeCreated?.apply(this, arguments);
            if (!this.properties) this.properties = {};
            if (!this.properties.anima_selections) this.properties.anima_selections = {};
            var self = this;
            requestAnimationFrame(() => self._animaInit());
        };

        const origOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            origOnConfigure?.apply(this, arguments);
            if (data.properties?.anima_selections) {
                this.properties.anima_selections = JSON.parse(
                    JSON.stringify(data.properties.anima_selections)
                );
            }
            if (data.properties?.anima_strength !== undefined) {
                this.properties.anima_strength = data.properties.anima_strength;
            }
            var self = this;
            requestAnimationFrame(() => self._animaInit());
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
                dataW.hidden = true;
                dataW.computeSize = () => [0, -4];
                dataW.type = "hidden";
                dataW.serialize = false;
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
                };
            }

            if (dataW?.value) {
                try {
                    var parsed = JSON.parse(dataW.value);
                    if (Object.keys(parsed).length > 0) {
                        this.properties.anima_selections = parsed;
                    }
                } catch {}
            }

            this._animaRebuild(false);
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

            // Sync to lora_data + properties
            this._animaSync();

            var sz = this.computeSize();
            this.size[0] = Math.max(this.size[0], sz[0]);
            this.size[1] = sz[1];
            if (this.graph) this.graph.setDirtyCanvas(true, true);
        };

        // ---- R key refresh ----
        nodeType.prototype.refreshComboInNode = async function (defs) {
            await getLoraList(true);
            this._animaRebuild(true);
        };
    },
});
