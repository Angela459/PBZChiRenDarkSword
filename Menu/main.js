"use strict";
// Uses the ExampleMod registration contract. The menu owns persistence;
// the UE4SS audio module reads the same Enabled value on the game thread.
const ID = "PBZChiRenAudioReplace";
const FILE = ID + ".txt";
const entries = globalThis.__PBZLoaderEntries || (globalThis.__PBZLoaderEntries = Object.create(null));
if (entries[ID]) throw new Error(ID + " already started; restart the game");
entries[ID] = "starting";
let stopped = false;
const lines = [];
let logPath;
function log(message) {
    try {
        lines.push(new Date().toISOString() + " " + message);
        if (lines.length > 100) lines.shift();
        if (logPath) require("ue").EasyCsv.SaveStringToFileWithFullPath(lines.join("\r\n") + "\r\n", logPath);
    } catch (_) { }
}
exports.stop = function () {
    if (stopped) return;
    stopped = true;
    log("menu registration stopped");
    delete entries[ID];
};
try {
    const UE = require("ue");
    const K = UE.KismetSystemLibrary;
    if (!K || !UE.EasyCsv) throw new Error("Required menu APIs unavailable");
    logPath = K.ConvertToAbsolutePath(K.GetProjectSavedDirectory() + ID + "-menu-log.txt");
    const accepted = (globalThis.PBZModsMenu ||= []).push({
        id: ID,
        title: { en: "Chi♂Ren Audio", "zh-Hans": "炽♂刃音效", "zh-Hant": "熾♂刃音效" },
        singleToggleSection: true,
        description: {
            en: "Custom charge, ground impact, and enemy hit sounds.",
            "zh-Hans": "蓄力播放 10、02、09；砸地播放 01，满蓄命中敌人则跳过或停止本次 01，播放 12→11。",
            "zh-Hant": "蓄力播放 10、02、09；砸地播放 01，滿蓄命中敵人則跳過或停止本次 01，播放 12→11。"
        },
        version: "0.12.0",
        file: FILE,
        settings: [{
            key: "Enabled", type: "toggle", default: true,
            label: { en: "Enabled", "zh-Hans": "启用", "zh-Hant": "啟用" },
            help: {
                en: "On: custom charge, ground impact and enemy hit sounds. Off: restore the original sounds.",
                "zh-Hans": "开启：使用替换音效。关闭：恢复原版声音。选择会自动保存。",
                "zh-Hant": "開啟：使用替換音效。關閉：恢復原版聲音。選擇會自動儲存。"
            }
        }],
        onChange: (name, value) => {
            if (!stopped && name === "Enabled") log("Enabled=" + value);
        }
    });
    if (accepted === false) throw new Error("Menu rejected audio settings");
    entries[ID] = "loaded";
    exports.ready = true;
    log("registered; default=On; persistence=" + FILE);
} catch (error) {
    log("failed: " + (error && error.message || error));
    exports.stop();
    entries[ID] = "failed";
    throw error;
}
