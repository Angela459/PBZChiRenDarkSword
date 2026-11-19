"""Offline Lua-to-native audio API mocks; no audio is played."""
import os
import subprocess
import tempfile
import time
import shutil
import wave
from pathlib import Path

TESTS=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('PBZ_TEST_ROOT',TESTS.parent))
RELEASE=bool(os.environ.get('PBZ_TEST_ROOT'))
from lupa.lua54 import LuaRuntime

MOCK=(TESTS/'mock_unreal.lua').read_text(encoding='utf-8')
SCRIPT=(ROOT/'Scripts/main.lua').read_text(encoding='utf-8')
assert 'os.execute' not in SCRIPT, 'Lua startup must not spawn a console process'
EXTRA=r'''
local function object(id,props,values,isRoot)
    local methods={type=function() return values.Kind or 'UObject' end,
        IsValid=function() return not isRoot or rootAlive end,
        GetFullName=function() return id end,GetClass=function() return values.Schema or makeSchema(props) end}
    return setmetatable({}, {__index=function(_,field)
        if methods[field] then return methods[field] end
        if field=='GetOuter' and values.Outer then return function() return values.Outer end end
        if field=='GetOuter' and isRoot then return function() return makeObject('BP_Renewal_Hun_C Mock.Owner',{}, {}) end end
        assert(props[field],'unknown read '..field);fieldReads[#fieldReads+1]=field;return values[field]
    end,__newindex=function(_,field,value) assert(props[field],'unknown write '..field);values[field]=value end})
end
makeTestObject=object
os.clock=function() return clock end
rootValues={bIsActive=false,ChargeCount=0}
ability=object('GA_Hun_ChiRen_C_C Mock.BP_Renewal_Hun_C.ChiRen',
    {bIsActive='BoolProperty',ChargeCount='IntProperty'},rootValues,true)
actions,events={},{}
local names={'Fire_Charge','Fire_Charge','C_Full','Blade_Buff','Blade_Buff','Blade_Buff','C_Release_01','C_Release_02','C_Release_03'}
for i,n in ipairs(names) do
    local short='SFX_Combat_Hun_ChiRen_'..n
    local event=object('AkAudioEvent /Game/Wwise/Events/SFX/Combat/Test/'..short..'.'..short,{}, {})
    local branch=i<=6 and 'Main' or ('Release_0'..(i-6))
    events[i]=event
    actions[i]=object('GAA_PlaySound_Opt_C Mock.BP_Renewal_Hun_C.ChiRen.'..branch..'.Sound'..i,
        {AkEvent='ObjectProperty'},{AkEvent=event})
end
otherEvent=object('AkAudioEvent Other.Heavy',{}, {})
actions[10]=object('GAA_PlaySound_Opt_C Mock.BP_Renewal_Hun_C.ChiRen.Release_03.Hit',
    {AkEvent='ObjectProperty'},{AkEvent=otherEvent})
missingOne,noHooks,missingAudio=false,false,false
local baseOpen=io.open
io.open=function(path,mode)
    local f=baseOpen(path,mode)
    if f then
        local write=f.write
        f.write=function(self,value) write(self,value);return self end
        f.close=function() return true end
    end
    return f
end
groundValues={PlayingID=0}
local groundEvent=object('AkAudioEvent /Game/Wwise/Events/SFX/Combat/Special/Monster_Special/LionDancer/SFX_Combat_Special_LionDancer_HitGround_Stone_Light.SFX_Combat_Special_LionDancer_HitGround_Stone_Light',{}, {})
groundValues.AkEvent=groundEvent
groundActions={}
for n=1,3 do
    groundActions[n]=object('GAA_PlaySound_Opt_C Mock.BP_Renewal_Hun_C.ChiRen.Release_0'..n..'.Ground',
        {PlayingID='IntProperty',AkEvent='ObjectProperty'},groundValues)
    actions[10+n]=groundActions[n]
end
ultimateData=object('PBZ_BulletData /Game/Bullets/ChiRenUltimate.ChiRenUltimate',{}, {})
bulletAction=object('GAA_BulletBurstWithDeflect_C Mock.BP_Renewal_Hun_C.ChiRen.Release_03.Burst',
    {BulletData='ObjectProperty'},{BulletData=ultimateData})
childData=object('PBZ_BulletData /Game/Bullets/ChiRenChild.ChiRenChild',{}, {})
bulletValues={BulletSourceAbility=ability,BulletOwnerAvatar=ability:GetOuter(),BulletData=childData}
liveBullet=object('PBZ_SweepTraceBullet Mock.Bullet',
    {BulletSourceAbility='ObjectProperty',BulletOwnerAvatar='ObjectProperty',BulletData='ObjectProperty'},bulletValues)

enemy={type=function() return 'AActor' end,IsValid=function() return true end,
    GetFullName=function() return 'BP_Monster_C Mock.Enemy' end,
    GetClass=function() return {type=function() return 'UClass' end,IsValid=function() return true end,
        GetFullName=function() return 'Class /Script/Engine.Character' end} end}
terrain=object('StaticMeshActor Mock.Ground',{}, {})
FindAllOf=function(cls)
    calls=calls+1
    if cls=='GA_Hun_ChiRen_C_C' then return {ability} end
    if cls=='GAA_BulletBurstWithDeflect_C' then return {bulletAction} end
    assert(cls=='GAA_PlaySound_Opt_C')
    if missingOne then local a={};for i=1,8 do a[i]=actions[i] end;return a end
    return actions
end
Key.F6=6
RegisterKeyBind=function() error('Audio replacement must not register hotkeys') end
LoopInGameThreadWithDelay=function(ms,fn) assert(ms==50);pump=fn;return 1 end
audioCommands={}
PBZ_PlayAudio=function(action,first,second)
    if missingAudio then return false end
    local value
    if action=='play' then value='play'..tostring(first)..(second and second>0 and ':'..second or '')
    elseif action=='hit' then value='hit:'..tostring(first)
    elseif action=='volume' then value='volume:'..tostring(first)
    elseif action=='stop' then value='stop'
    else return false end
    audioCommands[#audioCommands+1]='mock|'..tostring(#audioCommands+1)..'|'..value
    return true
end
menuInstallCalls={}
PBZ_RunHiddenPowerShell=function(script,root,version)
    menuInstallCalls[#menuInstallCalls+1]={script=script,root=root,version=version}
    files[root..'Menu/install-version.txt']=version..'\r\n'
    return true
end
nativeHooks={}
local function nativeFunction(parameters,path,flags)
    return {type=function() return 'UFunction' end,IsValid=function() return true end,
        GetFullName=function() return 'Function '..path end,
        GetFunctionFlags=function() return flags or 0x08000000 end,
        ForEachProperty=function(_,fn)
            for _,pair in ipairs(parameters) do
                local name,kind=pair[1],pair[2]
                fn({GetFName=function() return {ToString=function() return name end} end,
                    GetClass=function() return {GetFName=function() return {ToString=function() return kind end} end} end})
            end
        end}
end
markerClassPath='/PBZCombatAsset/Prototypes/Bullet/Events/PBZ_BulletEvent_MarkBulletHitTarget.PBZ_BulletEvent_MarkBulletHitTarget_C'
makeNativeFunction=nativeFunction
markerPath=markerClassPath..':Trigger'
markerClass=makeSchema({})
markerClass.GetFullName=function() return 'BlueprintGeneratedClass '..markerClassPath end
markerClass.ForEachFunction=function(_,fn)
    fn(nativeFunction({{'EntryPoint','IntProperty'}},markerClassPath..':ExecuteUbergraph_Test'))
    fn(nativeFunction({{'SourceBullet','InterfaceProperty'},{'EventData','StructProperty'},
        {'Temp_struct_Variable','StructProperty'},{'CallFunc_Conv_InterfaceToObject_ReturnValue','ObjectProperty'},
        {'CallFunc_IsValid_ReturnValue','BoolProperty'}},markerPath,214042624))
end
function eventData(target) return {type=function() return 'UScriptStruct' end,EventActor=target or enemy} end
StaticFindObject=function(path)
    if noHooks then return nil end
    if path:find('BulletEventsData',1,true) then return nil end
    assert(not path:find('OnDamage',1,true) and not path:find('EffectContextGet',1,true),'damage notification route must be removed')
    if path=='/Script/SGameCombatSystem.BulletEventData' then return makeSchema({EventActor='ObjectProperty',EventBody='StructProperty'}) end
    if path=='/Script/SGameUtils.ComponentSocket' then return makeSchema({Component='ObjectProperty',SocketName='NameProperty'}) end
    if path=='/Script/Engine.ActorComponent:GetOwner' then return nativeFunction({{'ReturnValue','ObjectProperty'}},path,1024) end
    if path==markerClassPath then return markerClass end
    assert(path=='/Script/LegoAbility.LegoAbility:PlayTimeline' or path=='/Script/LegoAbility.LegoAbility:PlayTimelineByName','unverified API lookup '..path)
    local byName=path:find('ByName',1,true)~=nil
    return {type=function() return 'UFunction' end,IsValid=function() return true end,
        ForEachProperty=function(_,fn)
            local pname=byName and 'TimelineName' or 'Timeline'
            fn({GetFName=function() return {ToString=function() return pname end} end,
                GetClass=function() return {GetFName=function() return {ToString=function() return byName and 'NameProperty' or 'ObjectProperty' end} end} end})
        end}
end
RegisterHook=function(path,pre,post)
    if path==markerPath then assert(post==nil,'Blueprint must use the script callback slot') end
    assert(not path:find('OnDamage',1,true),'OnDamage must never register')
    nativeHooks[path]=pre;return 1,2
end
function release(n)
    local timeline=object('LGATimeline Mock.BP_Renewal_Hun_C.ChiRen.Release_0'..n,{}, {})
    nativeHooks['/Script/LegoAbility.LegoAbility:PlayTimeline'](ability,timeline)
end
function mainTimeline()
    local timeline=object('LGATimeline Mock.BP_Renewal_Hun_C.ChiRen.Main',{}, {})
    nativeHooks['/Script/LegoAbility.LegoAbility:PlayTimeline'](ability,timeline)
end
function hit(target)
    nativeHooks[markerPath](nil,liveBullet,eventData(target))
end
function step(count)
    for i=1,count do clock=clock+0.05
        pump()
    end
end
function allLogs() local out=table.concat(printed);for path,value in pairs(files) do if path:match('%.log$') then out=out..value end end;return out end
function command() return table.concat(audioCommands,'\n')..(#audioCommands>0 and '\n' or '') end
function occurrences(s,word) local n=0;for _ in s:gmatch(word) do n=n+1 end;return n end
function menu(value,volume,original)
    local v=value=='On' and 'true' or (value=='Off' and 'false' or '')
    files['../PBZChiRenDarkSword.config.json']='{\n  \"Enabled\": '..v..',\n  \"Volume\": '..tostring(volume or 100)..',\n  \"PlayOriginal\": '..tostring(original==true)..'\n}'
end
'''

def runtime(initial=None,setup=None):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK);lua.execute(EXTRA)
    if setup:
        lua.execute(setup)
    if initial is not None:
        lua.globals().menu(initial)
    lua.execute(SCRIPT)
    return lua

# Reproduce the actual failed setup: UI file says zero, JSON still says 100.
menu_path='../'+'../../../../../ProjectPBZ/Content/Paks/~mods/PBZChiRenDarkSword.txt'
menu_bootstrap_path='../'+'../../../../../ProjectPBZ/Content/JavaScript/PBZModsMenu/bootstrap.js'
first_install=runtime(setup='files["' + menu_bootstrap_path + '"]="ready"')
assert first_install.eval('#menuInstallCalls')==1
assert first_install.eval('menuInstallCalls[1].version')=='v1.1'
assert first_install.eval("files['../Menu/install-version.txt']")=='v1.1\r\n'
installed_again=runtime(setup='files["' + menu_bootstrap_path + '"]="ready";files["../Menu/install-version.txt"]="v1.1\\r\\n"')
assert installed_again.eval('#menuInstallCalls')==0
print('PASS menu installer runs once, records its version and skips unchanged launches')

native_registration=runtime(setup="files['../../mods.txt']='OtherMod : 1\\r\\n'")
assert 'OtherMod : 1\r\nPBZChiRenNativeAudio : 1\r\n' in native_registration.eval("files['../../mods.txt']")
assert 'restart the game once' in native_registration.eval('allLogs()')
native_registration_again=runtime(setup="files['../../mods.txt']='OtherMod : 1\\r\\nPBZChiRenNativeAudio : 1\\r\\n'")
assert native_registration_again.eval("files['../../mods.txt']").count('PBZChiRenNativeAudio')==1
native_disabled=runtime(setup="files['../../mods.txt']='PBZChiRenNativeAudio : 0\\r\\n'")
assert native_disabled.eval("files['../../mods.txt']")=='PBZChiRenNativeAudio : 0\r\n'
assert 'explicitly disables' in native_disabled.eval('allLogs()')
print('PASS native UE4SS mod is auto-registered once; explicit disabled entry is preserved')

menu_lua=runtime()
menu_lua.globals().menuFilePath=menu_path
menu_lua.execute('menu("On",100);files[menuFilePath]="; ChiRen audio menu\\r\\nEnabled=On\\r\\nVolume=0\\r\\n";step(8)')
assert menu_lua.eval('command()').strip().endswith('|volume:0')
menu_lua.execute('files[menuFilePath]="Enabled=On\\r\\nVolume=35\\r\\n";step(5)')
assert menu_lua.eval('command()').strip().endswith('|volume:35')
menu_lua.execute('files[menuFilePath]="Enabled=On\\r\\nVolume=35\\r\\nPlayOriginal=On\\r\\n";step(5);assert(actions[1].AkEvent==events[1])')
menu_lua.execute('files[menuFilePath]="Enabled=On\\r\\nVolume=35\\r\\nPlayOriginal=Off\\r\\n";step(5);assert(actions[1].AkEvent==nil)')
menu_lua.execute('local before=command();files[menuFilePath]="Enabled=On\\r\\nVolume=";step(5);assert(command()==before)')
menu_lua.execute('files[menuFilePath]="Enabled=Off\\r\\nVolume=0\\r\\n";step(5);assert(actions[1].AkEvent==events[1])')
print('PASS menu TXT overrides JSON and toggles original sound live while preserving incomplete-write behavior')

lua=runtime()
lua.execute('step(8);assert(calls>0);for i=1,9 do assert(actions[i].AkEvent==nil) end;assert(actions[10].AkEvent==otherEvent)')
assert '|volume:100' in lua.eval('command()')
assert 'ARMED stage-driven' in lua.eval('allLogs()')
if not RELEASE:
    assert 'PlayTimeline params=Timeline' in lua.eval('allLogs()')
print('PASS native audio API available at startup; verified timeline signatures and nine muted refs')
lua.execute('menu("On",65);step(5);assert(command():match("volume:65"))')
print('PASS menu volume changes are sent to the live player')
original_lua=runtime()
original_lua.execute('step(8);for i=1,9 do assert(actions[i].AkEvent==nil) end;menu("On",65,true);step(5);for i=1,9 do assert(actions[i].AkEvent==events[i]) end')
original_lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=1;step(1);assert(command():match("play1"));assert(actions[1].AkEvent==events[1])')
original_lua.execute('menu("On",65,false);step(5);for i=1,9 do assert(actions[i].AkEvent==nil) end')
print('PASS original sound toggle preserves game audio while custom clips continue, then reapplies muting when switched off')
lua.execute('rootValues.bIsActive=true;step(1);assert(not command():find("play",1,true))')
for stage in [1,2,3]:
    lua.execute(f'rootValues.ChargeCount={stage};step(1)')
    assert lua.eval('command()').strip().endswith(f'play{stage}')
    lua.execute('step(10)')
    assert lua.eval(f'occurrences(command(),"play{stage}")')==1
lua.execute('release(3);step(1);assert(occurrences(command(),"play4")==0);release(3);step(8);assert(occurrences(command(),"play4")==0);groundValues.PlayingID=42;step(1);step(5)')
assert lua.eval('occurrences(command(),"play4")')==1
lua.execute('rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
assert lua.eval('occurrences(command(),"play4")')==1
if not RELEASE:
    assert 'GROUND_SOUND PlayingID=42' in lua.eval('allLogs()')
assert 'reason=full-charge miss confirmed at ability end' not in lua.eval('allLogs()')
print('PASS charge clips once each; full-charge ground plays 01 immediately with no extra sound at ability end')

lua.execute('rootValues.bIsActive=true;step(1);rootValues.ChargeCount=1;step(1);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
assert lua.eval('command()').strip().endswith('|stop')
assert lua.eval('occurrences(command(),"play4")')==1
print('PASS cancellation never plays release clip')

for attempt in range(8):
    lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=0;step(1)')
    for stage in [1,2,3]:
        lua.execute(f'rootValues.ChargeCount={stage};step(12)')
    lua.execute('release(3);step(1);groundValues.PlayingID=groundValues.PlayingID+1;step(1);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(12)')
assert lua.eval('occurrences(command(),"play4")')==9
assert lua.eval('occurrences(command(),"play1")')==10 # one earlier cancelled cast
assert 'ORIGINAL native audio C++ mod unavailable' not in lua.eval('allLogs()')
print('PASS repeated ultimates dispatch all four clips through the native C++ API')

# Ground and enemy damage are independent; low charge can only play ground audio.
for charge in [1,2]:
    before=lua.eval('occurrences(command(),"play4")')
    lua.execute(f'rootValues.bIsActive=true;rootValues.ChargeCount={charge};step(1);release({charge});step(1);hit();groundValues.PlayingID=groundValues.PlayingID+1;step(1)')
    assert lua.eval('occurrences(command(),"play4")')==before+1
    assert lua.eval('occurrences(command(),"|hit")')==0
    lua.execute('rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
print('PASS low-charge hits play only 01 at real ground sound, never 12->11')

# Real UE4SS logs showed AActor for both target and BulletOwnerAvatar. UObject
# wrappers returned by GetOuter still identify the same player by full name.
actor_lua=runtime(setup=r'''
bulletValues.BulletOwnerAvatar=makeTestObject(ability:GetOuter():GetFullName(),{}, {Kind='AActor'})
''')
actor_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);hit();step(1)')
assert actor_lua.eval('occurrences(command(),"|hit")')==1
if not RELEASE:
    assert 'actor=BP_Monster_C Mock.Enemy' in actor_lua.eval('allLogs()')
print('PASS actual AActor enemy and player-owner wrappers are valid; source ability still must match')

immediate_lua=runtime()
immediate_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);hit()')
assert '|hit:1' in immediate_lua.eval('command()')
if not RELEASE:
    assert 'dispatch=callback' in immediate_lua.eval('allLogs()')
immediate_lua.execute('step(1);assert(occurrences(command(),"|hit")==1)')
immediate_lua.execute('step(2);hit();assert(occurrences(command(),"|hit")==2);step(1);assert(occurrences(command(),"|hit")==2)')
print('PASS verified hit is submitted to the native audio API immediately and exactly once')

# Same trace as 18:28:32: count resets, then charges again while bIsActive never
# becomes false at a sample. The second cast must rearm and replay all nodes.
rapid_lua=runtime()
rapid_lua.execute('step(8);rootValues.bIsActive=true;step(1)')
for stage in [1,2,3]:
    rapid_lua.execute(f'rootValues.ChargeCount={stage};step(1)')
rapid_lua.execute('release(3);step(1);groundValues.PlayingID=1;step(1);hit();step(2);rootValues.ChargeCount=0;step(1)')
# Staying at zero alone must not prematurely erase the previous hit window.
rapid_lua.execute('hit();step(1)')
assert rapid_lua.eval('occurrences(command(),"|hit")')==2
for stage in [1,2,3]:
    rapid_lua.execute(f'rootValues.ChargeCount={stage};step(1)')
rapid_lua.execute('release(3);step(1);groundValues.PlayingID=2;step(1);hit();step(1)')
assert all(rapid_lua.eval(f'occurrences(command(),"play{i}")')==2 for i in [1,2,3,4])
assert rapid_lua.eval('occurrences(command(),"|hit")')==3
if not RELEASE:
    assert 'reason=charge resumed without inactive frame' in rapid_lua.eval('allLogs()')
print('PASS back-to-back casts with no inactive sample replay charge/ground/hit; count reset alone does not close prior hit window')

# A verified Main timeline can rearm even if polling skipped the zero counter.
rapid_lua.execute('rootValues.ChargeCount=0;mainTimeline();rootValues.ChargeCount=1;step(1);rootValues.ChargeCount=2;step(1);rootValues.ChargeCount=3;step(1);release(3);step(1);groundValues.PlayingID=3;step(1);hit();step(1)')
assert all(rapid_lua.eval(f'occurrences(command(),"play{i}")')==3 for i in [1,2,3,4])
assert rapid_lua.eval('occurrences(command(),"|hit")')==4
if not RELEASE:
    assert 'reason=Main timeline' in rapid_lua.eval('allLogs()')
rapid_lua.execute('mainTimeline();step(1);mainTimeline();step(1)')
assert rapid_lua.eval('occurrences(command(),"play3")')==4 # observed count once, never a duplicate from the second Main call
print('PASS Main timeline rearms repeated casts even when zero was not sampled; duplicate Main does not replay charge')

pending_lua=runtime()
pending_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);hit();rootValues.ChargeCount=0;mainTimeline();step(1)')
assert pending_lua.eval('occurrences(command(),"|hit")')==1
print('PASS an already verified hit is preserved if the next cast starts before the audio timer runs')

before=lua.eval('occurrences(command(),"play4")')
lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);hit();step(1);assert(occurrences(command(),"|hit")==0);release(3);step(1)')
lua.execute('hit(terrain);step(1);assert(occurrences(command(),"|hit")==0)')
lua.execute('bulletValues.BulletSourceAbility=otherEvent;hit();step(1);assert(occurrences(command(),"|hit")==0);bulletValues.BulletSourceAbility=ability')
lua.execute('bulletValues.BulletOwnerAvatar=enemy;hit();step(1);assert(occurrences(command(),"|hit")==0);bulletValues.BulletOwnerAvatar=ability:GetOuter()')
lua.execute('hit(ability:GetOuter());step(1);assert(occurrences(command(),"|hit")==0);hit();hit();step(1);assert(occurrences(command(),"|hit")==1)')
lua.execute('groundValues.PlayingID=groundValues.PlayingID+1;step(4);hit();step(1);assert(occurrences(command(),"|hit")==2)')
lua.execute('rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1);hit();step(2)')
assert lua.eval('occurrences(command(),"play4")')==before
assert lua.eval('occurrences(command(),"|hit")')==2
print('PASS full-charge hit before ground suppresses 01; repeated hits work; duplicates/terrain/self/unrelated source rejected')

for attempt in range(3):
    lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);step(1);groundValues.PlayingID=groundValues.PlayingID+1;step(1);hit();step(1);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
assert lua.eval('occurrences(command(),"|hit")')==5
assert lua.eval('occurrences(command(),"play4")')==before+3
print('PASS every subsequent late hit uses the cast number to cancel its earlier 01 and play 12->11')

lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);step(60);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
assert lua.eval('occurrences(command(),"play4")')==before+3
assert 'reason=ground fallback' not in lua.eval('allLogs()')
print('PASS missing ground sound never plays timed 01, even after 3 seconds or ability end')

# A real hit event is separate from the ground node and can arrive in the same tick.
target_lua=runtime()
target_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);groundValues.PlayingID=19;hit();step(1)')
assert target_lua.eval('occurrences(command(),"play4")')==0
assert target_lua.eval('occurrences(command(),"|hit")')==1
commands=target_lua.eval('command()')
assert '|play4' not in commands and '|hit:1' in commands
if not RELEASE:
    assert 'via=marker' in target_lua.eval('allLogs()')
target_lua.execute('hit();hit();step(1);assert(occurrences(command(),"|hit")==1);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
if not RELEASE:
    assert 'HIT_COUNTS marker=3 matched=1' in target_lua.eval('allLogs()')
for count in [1,2]:
    target_lua.execute(f'rootValues.bIsActive=true;rootValues.ChargeCount={count};step(1);release(3);hit();groundValues.PlayingID=groundValues.PlayingID+1;step(1);rootValues.bIsActive=false;rootValues.ChargeCount=0;step(1)')
assert target_lua.eval('occurrences(command(),"|hit")')==1
assert target_lua.eval('occurrences(command(),"play4")')==2
print('PASS same-tick full-charge hit suppresses 01; low charges keep immediate ground 01')

# A miss on the next cast must not inherit suppression from the previous hit.
target_lua.execute('rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);groundValues.PlayingID=27;step(1)')
assert target_lua.eval('occurrences(command(),"play4")')==3
assert target_lua.eval('occurrences(command(),"|hit")')==1
print('PASS full-charge miss on a later cast still plays 01 at ground, with no hit-confirmation delay')

resume_lua=runtime(setup='rootValues.bIsActive=true;rootValues.ChargeCount=3')
resume_lua.execute('step(8);release(3);hit();step(1)')
assert '|hit:1' in resume_lua.eval('command()')
print('PASS discovering an already active ultimate assigns a valid cast number')

cross_cast=runtime()
cross_cast.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);hit();rootValues.ChargeCount=0;mainTimeline();rootValues.ChargeCount=3;release(3);groundValues.PlayingID=1;step(1)')
assert '|play4:2' in cross_cast.eval('command()')
assert '|hit:1' in cross_cast.eval('command()') and '|hit:2' not in cross_cast.eval('command()')
print('PASS old queued hit keeps its cast number and does not suppress the next cast ground sound')

# Some events omit EventActor. Verify the reflected component-owner fallback
# as well as the real AActor-valued EventActor tested above.
body_lua=runtime(setup=r'''
ownerCalls=0
bodyOwner=enemy
local cls=makeSchema({})
cls.GetFullName=function() return 'Class /Script/Engine.ActorComponent' end
bodyComponent={type=function() return 'UObject' end,IsValid=function() return true end,
    GetFullName=function() return 'SkeletalMeshComponent Mock.Enemy.Mesh' end,
    GetClass=function() return cls end,
    GetOwner=function() ownerCalls=ownerCalls+1;return bodyOwner end}
local actorComponent=bodyComponent
function socketEvent()
    return {type=function() return 'UScriptStruct' end,EventActor=nil,
        EventBody={type=function() return 'UScriptStruct' end,Component=actorComponent}}
end
function socketHit() nativeHooks[markerPath](nil,liveBullet,socketEvent()) end
''')
body_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);socketHit();step(1)')
assert body_lua.eval('occurrences(command(),"|hit")')==1
if not RELEASE:
    assert 'target=EventBody.Component.GetOwner' in body_lua.eval('allLogs()')
body_lua.execute('step(2);bodyOwner=ability:GetOuter();socketHit();step(1);bodyOwner=terrain;socketHit();step(1)')
assert body_lua.eval('occurrences(command(),"|hit")')==1
body_lua.execute('bodyOwner=enemy;bulletValues.BulletSourceAbility=otherEvent;socketHit();step(1);bulletValues.BulletSourceAbility=ability')
assert body_lua.eval('occurrences(command(),"|hit")')==1
body_lua.execute('socketHit();step(1)')
assert body_lua.eval('occurrences(command(),"|hit")')==2
print('PASS real Trigger signature including Blueprint locals; null EventActor resolves component owner; self/terrain/unrelated source rejected')

missing_socket=runtime(setup=r'''
local baseFind=StaticFindObject
StaticFindObject=function(path)
    if path=='/Script/SGameUtils.ComponentSocket' then return nil end
    return baseFind(path)
end
function socketEvent() return {type=function() return 'UScriptStruct' end,EventActor=nil,
    EventBody=setmetatable({}, {__index=function() error('unverified body fields must not be read') end})} end
''')
missing_socket.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);nativeHooks[markerPath](nil,liveBullet,socketEvent());groundValues.PlayingID=1;step(1)')
assert missing_socket.eval('occurrences(command(),"|hit")')==0
assert missing_socket.eval('occurrences(command(),"play4")')==1
assert 'target callback error' not in missing_socket.eval('allLogs()')
if not RELEASE:
    assert 'body_schema=false' in missing_socket.eval('allLogs()')
print('PASS missing body schema never reads unverified struct fields; ground audio remains active')

parent_lua=runtime(setup=r'''
bulletValues.BulletSourceAbility=nil
bulletValues.BulletData=childData
local parent=makeTestObject('BP_PBZ_ProjectileEmitter_C Mock.Parent',
    {BulletOwnerAvatar='ObjectProperty',BulletSourceAbility='ObjectProperty',BulletData='ObjectProperty'},
    {BulletOwnerAvatar=ability:GetOuter(),BulletSourceAbility=ability,BulletData=ultimateData})
bulletValues.ParentBullet=parent
liveBullet=makeTestObject('PBZ_SweepTraceBullet Mock.Child',
    {BulletData='ObjectProperty',ParentBullet='InterfaceProperty'},bulletValues)
''')
parent_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);hit();step(1)')
assert parent_lua.eval('occurrences(command(),"|hit")')==1
print('PASS hit event from a child bullet resolves the actual ultimate emitter via ParentBullet')

missing_marker=runtime(setup=r'''
local baseFind=StaticFindObject
StaticFindObject=function(path)
    if path==markerClassPath then return nil end
    return baseFind(path)
end
''')
missing_marker.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);groundValues.PlayingID=1;step(1)')
assert missing_marker.eval('occurrences(command(),"|hit")')==0
assert missing_marker.eval('occurrences(command(),"play4")')==1
assert 'ORIGINAL error' not in missing_marker.eval('allLogs()')
print('PASS absent hit event leaves ground replacement active; OnDamage is never queried or hooked')

missing_marker.execute('local baseFind=StaticFindObject;StaticFindObject=function(path) if path==markerClassPath then return markerClass end;return baseFind(path) end;step(45);hit();step(1)')
assert missing_marker.eval('occurrences(command(),"|hit")')==1
print('PASS normal game asset loading makes the marker discoverable on a later scan without forced loads')

graph_lua=runtime(setup=r'''
local dataSchema=makeSchema({})
dataSchema.GetFullName=function() return 'Class /Script/SGameCombatSystem.BulletDataBase' end
local child=makeTestObject('PBZ_SweepTraceBulletData /Game/Child.Child',{}, {Schema=dataSchema})
local event=makeTestObject('BulletEvent_SubBullet Mock.Event',{BulletData='ObjectProperty'},{BulletData=child})
local array={type=function() return 'TArray' end,ForEach=function(_,fn) fn(1,event) end}
local events={type=function() return 'UScriptStruct' end,Events=array}
local root=makeTestObject('PBZ_ProjectileEmitterData /Game/Emitter.Emitter',{StartEvents='StructProperty'},{StartEvents=events})
bulletAction=makeTestObject('GAA_BulletBurstWithDeflect_C Mock.BP_Renewal_Hun_C.ChiRen.Release_03.Burst',
    {BulletData='ObjectProperty'},{BulletData=root})
bulletValues.BulletData=child;bulletValues.BulletSourceAbility=nil
local baseFind=StaticFindObject
StaticFindObject=function(path)
    if path=='/Script/SGameCombatSystem.BulletEventsData' then return makeSchema({Events='ArrayProperty'}) end
    return baseFind(path)
end
''')
graph_lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=3;step(1);release(3);step(1);hit();step(1);assert(occurrences(command(),"|hit")==1)')
if not RELEASE:
    assert 'depth=2 PBZ_SweepTraceBulletData /Game/Child.Child' in graph_lua.eval('allLogs()')
print('PASS reflected emitter StartEvents -> sub-bullet data graph matches full-charge child hit even without BulletSourceAbility')

lua.execute('menu("Off");step(5);for i=1,9 do assert(actions[i].AkEvent==events[i]) end;step(650);for i=1,9 do assert(actions[i].AkEvent==events[i]) end')
print('PASS menu Off restores originals and stays off')
lua.execute('menu("On");step(8);assert(actions[1].AkEvent==nil)')
print('PASS menu On re-enables stage replacement')

lua=runtime('Off');lua.execute('step(620);assert(calls==0 and not enabled)')
print('PASS saved Off prevents native scans and replacement after restart')

for encoding in ('utf-8-sig', 'utf-16-le', 'utf-16-be'):
    lua=runtime('Off')
    text='{\r\n  "Enabled": true,\r\n  "Volume": 100\r\n}\r\n'
    data=text.encode(encoding)
    if encoding=='utf-16-le': data=b'\xff\xfe'+data
    if encoding=='utf-16-be': data=b'\xfe\xff'+data
    lua.globals().encodedConfig=''.join(chr(b) for b in data)
    # Lua strings encode characters as UTF-8, so build the original bytes directly.
    lua.execute('encodedConfig=string.char('+','.join(str(b) for b in data)+')')
    lua.execute("files['../PBZChiRenDarkSword.config.json']=encodedConfig;step(8);assert(actions[1].AkEvent==nil)")
print('PASS UTF-8 BOM and UTF-16 menu settings decode correctly')

lua=runtime('Off');lua.execute('step(5);menu("O");step(5);assert(not enabled);menu("On");step(8);assert(actions[1].AkEvent==nil)')
print('PASS incomplete JSON menu writes preserve current setting')

for invalid in ('{"Enabled": "false"}', '{"Enabled": 0}', '{"Enabled": false,}', '{"Enabled": false}garbage', '{"Enabled": true, "Enabled": false}', '{"Enabled":true}'):
    lua=runtime('Off')
    lua.execute('step(5);assert(not enabled)')
    lua.globals().badConfig=invalid
    lua.execute("files['../PBZChiRenDarkSword.config.json']=badConfig;step(8);assert(not enabled)")
print('PASS malformed, duplicate-key and nonboolean JSON never changes the active mode')

for setup,expected in [('noHooks=true','release timeline hook unavailable'),
                       ('missingOne=true','WAIT Release_03')]:
    lua=runtime();lua.execute(setup+';step(850);assert(actions[1].AkEvent==events[1])')
    assert expected in lua.eval('allLogs()')
print('PASS missing hooks/actions leave original game sounds intact')

missing_audio=runtime(setup='PBZ_PlayAudio=nil')
missing_audio.execute('step(8);assert(not enabled and actions[1].AkEvent==events[1])')
assert 'native C++ audio mod unavailable' in missing_audio.eval('allLogs()')
print('PASS missing native C++ API keeps original game sounds intact')

unready_audio=runtime(setup='missingAudio=true')
unready_audio.execute('step(8);assert(not enabled and actions[1].AkEvent==events[1])')
assert 'native audio command failed' in unready_audio.eval('allLogs()')
print('PASS native audio initialization failure keeps original game sounds intact')

lua=runtime()
lua.execute('step(8);rootValues.bIsActive=true;rootValues.ChargeCount=1;step(1);assert(command():match("play1"));rootValues.ChargeCount=2;step(1);rootValues.ChargeCount=3;step(1);release(3);groundValues.PlayingID=50;step(1);hit();step(1)')
commands=lua.eval('command()')
assert '|play1' in commands and '|play2' in commands and '|play3' in commands
assert '|play4:1' in commands and '|hit:1' in commands
assert lua.eval('occurrences(command(),"|play4:1")==1')
assert lua.eval('occurrences(command(),"|hit:1")==1')
print('PASS native C++ bridge receives charge, cast-ground, hit, and stop commands in order')
