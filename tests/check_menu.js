"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const release = Boolean(process.env.PBZ_TEST_ROOT);
const source = fs.readFileSync(path.join(process.env.PBZ_TEST_ROOT || path.join(__dirname, ".."), "Menu/main.js"), "utf8");
function load(registry) {
    const writes = [];
    const context = {
        exports: {},
        PBZModsMenu: registry,
        require(name) {
            assert.equal(name, "ue");
            return {
                KismetSystemLibrary: {
                    ConvertToAbsolutePath: value => value,
                    GetProjectSavedDirectory: () => "Saved/"
                },
                EasyCsv: { SaveStringToFileWithFullPath(text, file) { writes.push({ text, file }); return true; } }
            };
        }
    };
    vm.createContext(context);
    vm.runInContext(source, context, {filename:"main.js"});
    return {context,writes};
}
const waiting = [];
const pending = load(waiting);
assert.equal(waiting.length, 1);
const descriptor = waiting[0];
assert.equal(descriptor.id, "PBZChiRenAudioReplace");
assert.equal(descriptor.file, "PBZChiRenAudioReplace.txt");
assert.equal(descriptor.title["zh-Hans"], "炽♂刃音效");
assert.equal(descriptor.singleToggleSection, true);
assert.equal(descriptor.settings.length, 1);
assert.equal(descriptor.settings[0].type, "toggle");
assert.equal(descriptor.settings[0].default, true);
assert.equal(descriptor.settings[0].key, "Enabled");
assert.equal(descriptor.settings[0].label["zh-Hans"], "启用");
assert.equal(descriptor.version, "1.0");
if (!release) {
    descriptor.onChange("Enabled", "Off");
    assert(pending.writes.at(-1).text.includes("Enabled=Off"));
} else {
    assert.equal(descriptor.onChange, undefined);
    assert.equal(pending.writes.length, 0);
}
pending.context.exports.stop();
const count = pending.writes.length;
if (!release) descriptor.onChange("Enabled", "On");
assert.equal(pending.writes.length, count);
assert.equal(pending.context.__PBZLoaderEntries.PBZChiRenAudioReplace, undefined);
console.log("PASS ExampleMod-style registration before menu startup; one persisted toggle, stop cleans up callbacks");
let registered;
const running = load({push(value) { registered=value; return true; }});
assert.equal(running.context.exports.ready, true);
assert.equal(registered.id, descriptor.id);
assert.equal(registered.file, descriptor.file);
assert.equal(running.context.setInterval, undefined);
assert.equal(running.context.RegisterKeyBind, undefined);
console.log("PASS registration after menu startup; no key bindings or input polling");

// Run the real menu descriptor validation and item generation, without Unreal UI.
// This catches a descriptor flag being dropped or a hidden/restore row reappearing.
const corePath = process.argv[2];
assert(corePath, "Pass the patched PBZ Mods Menu core main.js path");
const core = fs.readFileSync(corePath, "utf8");
new vm.Script(core, {filename: corePath});
const checkedStart = core.indexOf('        const TYPES = ');
const checkedEnd = core.indexOf('        // ---- registry:', checkedStart);
const rowsStart = core.indexOf('                const folded = ', core.indexOf('        function build(panel)'));
const rowsEnd = core.indexOf('                for (const it of items)', rowsStart);
assert(checkedStart > 0 && checkedEnd > checkedStart && rowsStart > checkedEnd && rowsEnd > rowsStart);
const context = {
    LANGS: ["en", "zh-Hans", "zh-Hant"],
    PBZ_MM_TAB: "PBZModsMenu", PBZ_MM_ABOUT: {}, PBZ_MM_HELP: {}, PBZ_MM_SLIDERS: {},
    PBZ_MM_ZH: {strings: {}, templates: {}}, PBZ_MM_HEADING_FOLD: true,
    note() {},
    fromRaw(s, value) { assert.equal(s.type, "toggle"); return value; },
    pick: value => typeof value === "object" ? value["zh-Hans"] || value.en : value,
    label: (setting, value) => value ? "On" : "Off",
    header() { throw Error("Unexpected heading for a registered mod"); }
};
vm.createContext(context);
vm.runInContext(core.slice(checkedStart, checkedEnd) + '\nglobalThis.validate = checkMod;', context);
const generate = '(function(mod, foldedIds){ const S={folded:new Set(foldedIds)};\n'
    + core.slice(rowsStart, rowsEnd) + '\nreturn items; })';
const makeRows = vm.runInContext(generate, context);
const mod = context.validate(descriptor, "registered");
assert.equal(mod.singleToggleSection, true);
const rows = makeRows(mod, []);
assert.deepEqual(Array.from(rows, r => r.kind), ["header", "value"]);
assert.equal(rows[0].s.label["zh-Hans"], "炽♂刃音效");
assert.equal(rows[1].s.type, "toggle");
assert.equal(rows[1].s.label["zh-Hans"], "启用");
assert.deepEqual(Array.from(makeRows(mod, [mod.id]), r => r.kind), ["header"]);
const normal = context.validate({...descriptor, id:"ExampleMod", singleToggleSection:false}, "registered");
assert.deepEqual(Array.from(makeRows(normal, []), r => r.kind), ["header", "value", "restore"]);
assert.deepEqual(Array.from(makeRows(normal, [normal.id]), r => r.kind), ["header"]);
const multi = context.validate({...descriptor, settings:[...descriptor.settings, {...descriptor.settings[0],key:"Other"}]}, "registered");
assert.equal(multi.singleToggleSection, false);
console.log("PASS real menu row builder: own section at same level as Settings/other mods, only one toggle, no Restore defaults");
