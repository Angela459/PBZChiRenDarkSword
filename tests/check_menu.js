"use strict";
// Execute the installed menu's actual discovery, validation and row builder.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const root = process.env.PBZ_TEST_ROOT || path.join(__dirname, "..");
const id = "PBZChiRenDarkSword";
const config = fs.readFileSync(path.join(root, id + ".config.json"), "utf8");
const descriptor = fs.readFileSync(path.join(root, id + ".modsmenu.json"), "utf8");
assert.deepEqual(JSON.parse(config), {Enabled:true});
assert.equal(JSON.parse(descriptor).version, "1.0");
assert.equal(JSON.parse(descriptor).settings, undefined); // the bool generates one row, never a Restore defaults action
const corePath = process.argv[2];
assert(corePath, "Pass the PBZ Mods Menu core main.js path");
const installed = fs.readFileSync(corePath, "utf8");
new vm.Script(installed, {filename:corePath});

function verify(core) {
    const checkedStart = core.indexOf('        const TYPES = ');
    const checkedEnd = core.indexOf('        // ---- registry:', checkedStart);
    const discoveryStart = core.indexOf('        const ue4ss = ');
    const discoveryEnd = core.indexOf('        // ---- mods that publish', discoveryStart);
    const rowsStart = core.indexOf('                const folded = ', core.indexOf('        function build(panel)'));
    const rowsEnd = core.indexOf('                for (const it of items)', rowsStart);
    assert(checkedStart > 0 && checkedEnd > checkedStart && discoveryEnd > discoveryStart && rowsEnd > rowsStart);
    const table = JSON.parse(/const PBZ_MM_ZH = (.*);/.exec(core)[1]);
    const files = new Map([
        ["ue4ss/Mods/mods.txt", id + " : 1\n"],
        ["ue4ss/Mods/" + id + "/" + id + ".config.json", config],
        ["ue4ss/Mods/" + id + "/" + id + ".modsmenu.json", descriptor],
        ["ue4ss/Mods/PBZModsMenuBridge/mods-index.txt", "; Acks=1\n" + id + "\n"]
    ]);
    const context = {
        LANGS:["en","zh-Hans","zh-Hant"], PBZ_MM_ZH:table,
        PBZ_MM_TAB:"PBZModsMenu", PBZ_MM_ABOUT:{}, PBZ_MM_HELP:{}, PBZ_MM_SLIDERS:{}, PBZ_MM_HEADING_FOLD:true,
        PBZ_MM_BRIDGE_INDEX:"PBZModsMenuBridge/mods-index.txt",
        abs:v=>v, storeRel:()=>"", store:()=>"steam", load:p=>files.get(p), pbzLog(){}, note(){},
        UE:{BlueprintPathsLibrary:{FileExists:p=>files.has(p)}},
        fromRaw(s,v){ assert.equal(s.type,"toggle"); return typeof v === "boolean" ? v : undefined; },
        label:(s,v)=>v?"On":"Off", header(){throw Error("Unexpected nested heading");}
    };
    vm.createContext(context);
    vm.runInContext(core.slice(checkedStart,checkedEnd) + core.slice(discoveryStart,discoveryEnd) +
        '\nglobalThis.discover=ue4ssMod;globalThis.names=ue4ssNames;globalThis.localized=inLang;',context);
    context.pick=value=>context.localized(value,"zh-Hans");
    const makeRows=vm.runInContext('(function(mod, foldedIds){const S={folded:new Set(foldedIds)};\n' +
        core.slice(rowsStart,rowsEnd) + '\nreturn items;})',context);
    const mod=context.discover(id);
    assert.equal(mod.id,"ue4ss/"+id);
    assert.equal(context.localized(mod.title,"zh-Hans"),"炽♂刃音效");
    assert.equal(mod.settings.length,1);
    assert.equal(mod.settings[0].key,"Enabled");
    assert.equal(mod.settings[0].type,"toggle");
    assert.equal(mod.settings[0].generated,true);
    assert.equal(context.localized(mod.settings[0].label,"zh-Hans"),"启用");
    assert.deepEqual(Array.from(makeRows(mod,[]),r=>r.kind),["header","value"]);
    assert.deepEqual(Array.from(makeRows(mod,[mod.id]),r=>r.kind),["header"]);
    assert(Array.from(context.names()).includes(id));
    files.delete("ue4ss/Mods/mods.txt");
    assert(Array.from(context.names()).includes(id)); // enabled.txt-only mods are enumerated by the bridge
    files.delete("ue4ss/Mods/PBZModsMenuBridge/mods-index.txt");
    assert.equal(context.discover(id).settings[0].type,"readonly");
    console.log("PASS native JSON auto-discovery: own section, one translated toggle, no restore row; Bridge-less mode is read-only");
}

verify(installed);
// Remove our former registered-JS extension to prove this does not require a menu-core patch.
const stock = installed.replace(/            \/\/ A separate mod section[^\n]*\n            mod\.singleToggleSection[^\n]*\n                && mod\.settings[^\n]*\n/, "")
    .replace('!mod.singleToggleSection && !folded','!folded');
verify(stock);
console.log("PASS stock menu behavior is sufficient; no JavaScript registration file or core patch required");
