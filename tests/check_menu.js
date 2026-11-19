"use strict";
// Execute the installed menu's actual discovery, validation and row builder.
const fs = require("fs"), path = require("path"), vm = require("vm"), assert = require("assert");
const root = process.env.PBZ_TEST_ROOT || path.join(__dirname, "..");
const id = "PBZChiRenDarkSword";
const config = fs.readFileSync(path.join(root, id + ".config.json"), "utf8");
const descriptor = fs.readFileSync(path.join(root, id + ".modsmenu.json"), "utf8");
assert.deepEqual(JSON.parse(config), {Enabled:true, Volume:100, PlayOriginal:false});
assert.equal(JSON.parse(descriptor).version, "1.1");
assert.equal(JSON.parse(descriptor).settings.length, 3);
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
        fromRaw(s,v){ return s.type === "toggle" ? (typeof v === "boolean" ? v : undefined) : (s.type === "number" && typeof v === "number" ? v : undefined); },
        label:(s,v)=>s.type === "toggle" ? (v?"On":"Off") : String(v), header(){throw Error("Unexpected nested heading");}
    };
    vm.createContext(context);
    vm.runInContext(core.slice(checkedStart,checkedEnd) + core.slice(discoveryStart,discoveryEnd) +
        '\nglobalThis.discover=ue4ssMod;globalThis.names=ue4ssNames;globalThis.localized=inLang;globalThis.validateMod=checkMod;',context);
    context.pick=value=>context.localized(value,"zh-Hans");
    const makeRows=vm.runInContext('(function(mod, foldedIds){const S={folded:new Set(foldedIds)};\n' +
        core.slice(rowsStart,rowsEnd) + '\nreturn items;})',context);
    const mod=context.discover(id);
    assert.equal(mod.id,"ue4ss/"+id);
    assert.equal(context.localized(mod.title,"zh-Hans"),"炽♂刃音效");
    assert.equal(mod.settings.length,3);
    assert.equal(mod.settings[0].key,"Enabled");
    assert.equal(mod.settings[0].type,"toggle");
    assert.equal(context.localized(mod.settings[0].label,"zh-Hans"),"启用");
    assert.equal(mod.settings[1].key,"PlayOriginal");
    assert.equal(mod.settings[1].type,"toggle");
    assert.equal(mod.settings[1].default,false);
    assert.equal(context.localized(mod.settings[1].label,"zh-Hans"),"同时播放原版音效");
    assert.equal(mod.settings[2].key,"Volume");
    assert.equal(mod.settings[2].type,"number");
    assert.equal(mod.settings[2].min,0);
    assert.equal(mod.settings[2].max,200);
    assert.equal(mod.settings[2].step,5);
    assert.deepEqual(Array.from(makeRows(mod,[]),r=>r.kind),["header","value","value","value","restore"]);
    assert.deepEqual(Array.from(makeRows(mod,[mod.id]),r=>r.kind),["header"]);
    assert(Array.from(context.names()).includes(id));
    files.delete("ue4ss/Mods/mods.txt");
    assert(Array.from(context.names()).includes(id)); // enabled.txt-only mods are enumerated by the bridge
    files.delete("ue4ss/Mods/PBZModsMenuBridge/mods-index.txt");
    assert(context.discover(id).settings.every(s=>s.type==="readonly"));

    // Exercise the actual script loaded by this installation, without a Bridge.
    const moduleRoot="/game/platform/steam/ue4ss/Mods/"+id;
    files.set(moduleRoot+"/"+id+".config.json", config);
    files.set(moduleRoot+"/"+id+".modsmenu.json", descriptor);
    const adapter=fs.readFileSync(path.join(root,"Menu/main.js"),"utf8")
        .replace("const MOD_ROOT = null;","const MOD_ROOT = "+JSON.stringify(moduleRoot)+";");
    let registration;
    const moduleContext={
        exports:{}, PBZModsMenu:{push(raw){registration=raw;return 1;}},
        require(name){
            if(name==="puerts") return {$ref:v=>({value:v}),$unref:r=>r.value};
            assert.equal(name,"ue");
            return {KismetSystemLibrary:{ConvertToAbsolutePath:p=>p,GetProjectSavedDirectory:()=>"/saved/",GetProjectContentDirectory:()=>"/content/"},
                BlueprintPathsLibrary:{FileExists:p=>files.has(p)},
                EasyCsv:{LoadStringFromLocalFile(p,ref){if(!files.has(p))return false;ref.value=files.get(p);return true;},
                    SaveStringToFileWithFullPath(text,p){files.set(p,text);return true;}}};
        }
    };
    vm.createContext(moduleContext);
    vm.runInContext(adapter,moduleContext);
    assert.equal(moduleContext.exports.ready,true);
    const registered=context.validateMod(registration,"registered",id);
    assert(registered);
    assert.equal(registered.store,undefined);
    assert.deepEqual(Array.from(registered.settings,s=>[s.key,s.type]),[["Enabled","toggle"],["PlayOriginal","toggle"],["Volume","number"]]);
    assert.equal(registered.settings[2].slider,true);
    assert.deepEqual(Array.from(makeRows(registered,[]),r=>r.kind),["header","value","value","value","restore"]);
    assert.equal(registration.onChange,undefined); // Lua reads the menu's real file directly.
    const menuPath="/content/Paks/~mods/"+id+".txt";
    assert(files.get(menuPath).includes("Volume=100\r\n"));
    assert(files.get(menuPath).includes("PlayOriginal=Off\r\n"));
    files.set(menuPath,"; ChiRen audio menu\r\nEnabled=On\r\nVolume=0\r\nPlayOriginal=On\r\n");
    moduleContext.exports.stop();
    const restarted=Object.assign({},moduleContext,{exports:{}});
    vm.createContext(restarted);
    vm.runInContext(adapter,restarted);
    assert(files.get(menuPath).includes("Volume=0\r\n"));
    assert(files.get(menuPath).includes("PlayOriginal=On\r\n"));
    files.set(menuPath,"; ChiRen audio menu\r\nEnabled=On\r\nVolume=75\r\n");
    const migration=Object.assign({},moduleContext,{exports:{}});
    vm.createContext(migration);
    vm.runInContext(adapter,migration);
    assert(files.get(menuPath).includes("Enabled=On\r\n"));
    assert(files.get(menuPath).includes("Volume=75\r\n"));
    assert(files.get(menuPath).includes("PlayOriginal=Off\r\n"));
    console.log("PASS no-Bridge registration, setting persistence and old menu TXT migration preserve existing values");
}

verify(installed);
// Remove our former registered-JS extension to prove this does not require a menu-core patch.
const stock = installed.replace(/            \/\/ A separate mod section[^\n]*\n            mod\.singleToggleSection[^\n]*\n                && mod\.settings[^\n]*\n/, "")
    .replace('!mod.singleToggleSection && !folded','!folded');
verify(stock);
console.log("PASS installed and stock menu cores; no core patch required");
