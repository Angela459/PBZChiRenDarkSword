"use strict";
// Installed with an absolute mod path by install.ps1; no menu-core changes.
const MOD_ROOT = null;
const ID = "PBZChiRenDarkSword";
const UE = require("ue"), host = require("puerts");
const K = UE.KismetSystemLibrary;
const root = MOD_ROOT;
if (!root) throw new Error("Menu entry must be installed through Menu/install.ps1");
const read = (path) => {
    const ref = host.$ref("");
    if (!UE.EasyCsv.LoadStringFromLocalFile(path, ref)) throw new Error("Cannot read " + path);
    return String(host.$unref(ref)).replace(/^\uFEFF/, "");
};
const write = (path, text) => {
    if (!UE.EasyCsv.SaveStringToFileWithFullPath(text, path)) throw new Error("Cannot save " + path);
};
const configPath = root + "/" + ID + ".config.json";
const values = JSON.parse(read(configPath));
if (values.PlayOriginal === undefined) values.PlayOriginal = false;
if (typeof values.Enabled !== "boolean" || typeof values.PlayOriginal !== "boolean" || !Number.isInteger(values.Volume) || values.Volume < 0 || values.Volume > 200)
    throw new Error("Invalid audio settings");
const descriptor = JSON.parse(read(root + "/" + ID + ".modsmenu.json"));
const bridge = root + "/../PBZModsMenuBridge/mods-index.txt";
exports.stop = () => {};
// A Bridge already exposes the same JSON. Otherwise register a writable script section.
if (!UE.BlueprintPathsLibrary.FileExists(bridge)) {
    // Lua reads this exact menu file. Never overwrite a saved selection on start.
    const file = ID + ".txt";
    const menuPath=K.ConvertToAbsolutePath(K.GetProjectContentDirectory() + "Paks/~mods/" + file);
    if (!UE.BlueprintPathsLibrary.FileExists(menuPath))
        write(menuPath, "; ChiRen audio menu\r\nEnabled=" + (values.Enabled ? "On" : "Off") + "\r\nVolume=" + values.Volume + "\r\nPlayOriginal=" + (values.PlayOriginal ? "On" : "Off") + "\r\n");
    else {
        const current = read(menuPath);
        if (!/^\s*PlayOriginal\s*=/m.test(current))
            write(menuPath, current.replace(/[\r\n]*$/, "") + "\r\nPlayOriginal=Off\r\n");
    }
    const accepted = (globalThis.PBZModsMenu ||= []).push(Object.assign({}, descriptor, {
        id: ID, file
    }));
    if (accepted === false) throw new Error("Menu rejected ChiRen audio settings");
}
exports.ready = true;
