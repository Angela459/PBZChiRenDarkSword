-- ChargeCount drives 10/02/09. A real ground sound is required for 01.
-- Ground plays 01 immediately unless this cast has hit; a later hit stops its 01.
local MOD="PBZChiRenAudioReplace"
local source=debug.getinfo(1,"S").source:gsub("^@","")
local root=(source:match("^(.*[\\/])") or "").."../"
local session=os.date("%Y%m%d-%H%M%S").."-"..math.random(100000,999999)
local output=io.open(root.."Runtime/run-"..session..".log","a")
local enabled,waiting,ability,lastActive=false,false,nil,false
local desired,ticks,faulted=true,0,false
local settingsPath=root.."../../../../../ProjectPBZ/Content/Paks/~mods/PBZChiRenAudioReplace.txt"
local patched,held,history={},{},{}
local timelineRegistered=false
local sequence,nextDiscover,nextHeartbeat,startedAt=0,0,0,0
local lastHostBeat,hostReadMiss=nil,false
local groundActions,bulletData,ipcFailures={},{},{}
local releaseBranch,groundBaseline=nil,0
local hitPlayed,dirtyCommands=false,false
local groundSeen,releaseClosed,hitSeen=false,false,{}
-- DEV-BEGIN
local hitDiagnostics={}
-- DEV-END
local targetRegistered=false
local targetWaitLogged=false
local releaseCharge=0
-- DEV-BEGIN
local hitCounts={marker=0,matched=0}
-- DEV-END
local previousCount,highestStage,released,releasePending=nil,0,false,false
local castStarted,chargeResetSeen,castSerial=false,false,0
local TARGETS={SFX_Combat_Hun_ChiRen_Fire_Charge=true,SFX_Combat_Hun_ChiRen_C_Full=true,
    SFX_Combat_Hun_ChiRen_Blade_Buff=true,SFX_Combat_Hun_ChiRen_C_Release_01=true,
    SFX_Combat_Hun_ChiRen_C_Release_02=true,SFX_Combat_Hun_ChiRen_C_Release_03=true}
local function log(s)
    if output then output:write(os.date("%Y-%m-%d %H:%M:%S").." "..s.."\n");output:flush() end
    print("["..MOD.."] "..s.."\n")
end
local function kind(v)
    if type(v)~="table" and type(v)~="userdata" then return type(v) end
    local ok,k=pcall(function() return v:type() end);return ok and k or "unknown"
end
local function unwrap(v)
    local k=kind(v)
    if k=="RemoteUnrealParam" or k=="LocalUnrealParam" then return v:get() end
    return v
end
local function valid(v)
    local k=kind(v)
    -- Actor-valued properties/returns use AActor wrappers on this UE4SS build.
    -- Struct values can also have IsValid(), so keep an explicit object allowlist.
    if k~="UObject" and k~="UClass" and k~="UFunction" and k~="AActor" then return false end
    local ok,x=pcall(function() return v:IsValid() end);return ok and x==true
end
local function full(v) return valid(v) and v:GetFullName() or "<invalid>" end
local function fields(v)
    if not valid(v) then return {} end
    local cls,result,seen=v:GetClass(),{},{}
    for _=1,12 do
        if not valid(cls) then break end
        local id=full(cls);if seen[id] then break end;seen[id]=true
        cls:ForEachProperty(function(p)
            local name=p:GetFName():ToString()
            if not result[name] then result[name]=p:GetClass():GetFName():ToString() end
        end)
        cls=cls:GetSuperStruct()
    end
    return result
end
local function readKnown(object,name)
    if not valid(object) then return nil end
    local prop=fields(object)[name]
    if prop=="ObjectProperty" or prop=="ObjectPtrProperty" or prop=="InterfaceProperty" then return unwrap(object[name]) end
end
-- DEV-BEGIN
local function diagnoseHit(reason,message)
    local count=hitDiagnostics[reason] or 0
    if count<4 then log("HIT_FILTER "..reason.." "..(message or "")) end
    hitDiagnostics[reason]=count+1
end
-- DEV-END
local function isCharacter(object)
    if not valid(object) then return false end
    local cls=object:GetClass()
    for _=1,12 do
        if not valid(cls) then break end
        local name=full(cls)
        if name:match("[%. ]Character$") or name:match("[%. ]PBZCharacter$") then return true end
        cls=cls:GetSuperStruct()
    end
    return false
end
local function fullChargeWindow()
    return enabled and ability and (released or releasePending) and not releaseClosed
        and releaseBranch=="Release_03" and releaseCharge>=3
end
local function startCast(reason,count)
    castSerial=castSerial+1;castStarted=true;chargeResetSeen=false
    highestStage,released,releasePending=0,false,false
    releaseBranch,releaseCharge=nil,0
    groundSeen,releaseClosed,hitPlayed=false,false,false
    hitSeen={}
-- DEV-BEGIN
    hitDiagnostics={}

    hitCounts={marker=0,matched=0}

    log("ULTIMATE_START ChargeCount="..tostring(count).." reason="..reason.." cast="..castSerial)
-- DEV-END
end
-- A release action spawns an emitter, whose event graph spawns damage bullets.
-- Follow only reflected bullet/event fields, with verified struct schema and budgets.
local function collectBulletData(rootData,branch)
    local schemaOk,schema=pcall(StaticFindObject,"/Script/SGameCombatSystem.BulletEventsData")
    local eventsVerified=false
    if schemaOk and schema then
        pcall(function() schema:ForEachProperty(function(p)
            if p:GetFName():ToString()=="Events" and p:GetClass():GetFName():ToString()=="ArrayProperty" then eventsVerified=true end
        end) end)
    end
    local seen,budget={},0
    local visit
    local function each(value,depth)
        if kind(value)~="TArray" then return end
        value:ForEach(function(index,ref)
            if index>32 then return true end
            visit(unwrap(ref),depth)
        end)
    end
    visit=function(object,depth)
        if depth>8 or budget>=96 or not valid(object) then return end
        local id=full(object)
        if seen[id] then return end
        seen[id]=true;budget=budget+1
        local props=fields(object)
        local cls=object:GetClass();local isData=false
        for _=1,12 do
            if not valid(cls) then break end
            if full(cls):match("[%. ]BulletDataBase$") then isData=true;break end
            cls=cls:GetSuperStruct()
        end
        -- Root identity is verified by the owning release action even on a
        -- stripped class schema; child assets must inherit BulletDataBase.
        if id==full(rootData) or isData then
            bulletData[id]=bulletData[id] or {};bulletData[id][branch]=true
-- DEV-BEGIN
            log("ULTIMATE_BULLET_DATA "..branch.." depth="..depth.." "..id)
-- DEV-END
        end
        for _,name in ipairs({"BulletData","BulletEventLibrary"}) do
            if props[name]=="ObjectProperty" then visit(object[name],depth+1) end
        end
        for _,name in ipairs({"Events","SubEvents"}) do
            if props[name]=="ArrayProperty" then each(object[name],depth+1) end
        end
        if eventsVerified then
            for _,name in ipairs({"StartEvents","PreAttackEvents","HitTargetEvents","HitWallEvents","MoveCompleteEvents",
                "InitializeEvents","DeflectedEvents","OnInitialize","OnStart","OnPreAttack","OnMovementComplete"}) do
                if props[name]=="StructProperty" then
                    local event=object[name]
                    if kind(event)=="UScriptStruct" then each(event.Events,depth+1) end
                end
            end
        end
    end
    local ok,err=pcall(visit,rootData,0)
    if not ok then log("HIT_DATA_GRAPH_PARTIAL "..tostring(err)) end
end
local function readText(name)
    local f=io.open(root.."Runtime/"..name,"r");if not f then return "" end
    local s=f:read("*a");f:close();return s or ""
end
local function writeText(name,s)
    local ok,err=pcall(function()
        local f,why=io.open(root.."Runtime/"..name,"w")
        if not f then error(tostring(why)) end
        local wrote,message=f:write(s);local closed,closeErr=f:close()
        if not wrote then error(tostring(message)) end
        if closed==nil and closeErr then error(tostring(closeErr)) end
    end)
    if ok then
        if ipcFailures[name] then log("IPC_WRITE_RECOVERED "..name) end
        ipcFailures[name]=nil
    elseif not ipcFailures[name] then
        ipcFailures[name]=os.clock();log("IPC_WRITE_RETRY "..name.." "..tostring(err))
    end
    return ok
end
local function readMenuSetting()
    local f=io.open(settingsPath,"rb")
    if not f then return nil end
    local s=f:read("*a");f:close()
    -- EasyCsv may write UTF-8 or UTF-16. Only an ASCII key/value is interpreted.
    if s:sub(1,2)=="\255\254" then
        s=s:sub(3):gsub("(.)\0","%1")
    elseif s:sub(1,2)=="\254\255" then
        s=s:sub(3):gsub("\0(.)","%1")
    else s=s:gsub("^\239\187\191","") end
    for line in (s.."\n"):gmatch("(.-)\n") do
        local value=line:match("^%s*[Ee][Nn][Aa][Bb][Ll][Ee][Dd]%s*=%s*([^;#\r\n]+)")
        if value then
            value=value:match("^%s*(.-)%s*$"):lower()
            if value=="on" or value=="true" or value=="1" or value=="yes" then return true end
            if value=="off" or value=="false" or value=="0" or value=="no" then return false end
            return nil -- don't change modes on an incomplete file write
        end
    end
end
local function command(value)
    sequence=sequence+1
    history[#history+1]=session.."|"..sequence.."|"..value
    if #history>128 then table.remove(history,1) end
    dirtyCommands=true
    if writeText("command.txt",table.concat(history,"\n").."\n") then dirtyCommands=false end
end
local function queueHit(enemy,via)
    local key=full(enemy)
    local now=os.clock()
    if hitSeen[key] and now-hitSeen[key]<0.05 then return end
    hitSeen[key]=now
-- DEV-BEGIN
    hitCounts.matched=hitCounts.matched+1
-- DEV-END
    hitPlayed=true -- suppress this cast's ground audio even before the timer runs
    command("hit:"..castSerial)
-- DEV-BEGIN
    log("PLAY sequence=12,11 stop_same_cast_01=true cast="..castSerial.." dispatch=callback reason=full-charge enemy contact "..key.." via="..via)
-- DEV-END
end
local function hostReady()
    -- Atomic replacement can briefly deny a Windows reader access. A failed read
    -- is not evidence that the player died; only expiry of its last verified beat is.
    local now=os.time()
    local ok,raw=pcall(readText,"ready.txt")
    local who,status,stamp
    if ok then who,status,stamp=raw:match("^([^|]+)|([^|]+)|(%d+)%s*$") end
    local at=tonumber(stamp)
    if who==session and status=="ready" and at and math.abs(now-at)<=10 then
        lastHostBeat=at
        if hostReadMiss then log("HOST_HEARTBEAT_RECOVERED") end
        hostReadMiss=false
        return true
    end
    local reason=not ok and "read error" or (not who and "missing/incomplete file"
        or (who~=session and "different session" or (status~="ready" and "not ready" or "stale timestamp")))
    if lastHostBeat and not hostReadMiss then
        log("HOST_HEARTBEAT_RETRY reason="..reason.." last_verified_age="..tostring(now-lastHostBeat))
        hostReadMiss=true
    end
    if lastHostBeat and math.abs(now-lastHostBeat)<=10 then return true end
    return false,reason.." last_verified_age="..tostring(lastHostBeat and now-lastHostBeat or "none")
end
local function restore()
    for _,item in ipairs(patched) do
        if valid(item.action) and valid(item.event) then
            local ok,err=pcall(function()
                if fields(item.action).AkEvent=="ObjectProperty" and not valid(item.action.AkEvent) then item.action.AkEvent=item.event end
            end)
            if not ok then log("ERROR restore "..tostring(err)) end
        end
    end
    patched={}
end
local function disable(reason)
    enabled,waiting,ability,lastActive=false,false,nil,false
    previousCount,highestStage,released,releasePending=nil,0,false,false
    castStarted,chargeResetSeen=false,false
    releaseBranch=nil
    groundSeen,releaseClosed,hitSeen=false,true,{}
    groundActions,bulletData={},{}
    restore();pcall(command,"quit");log("ORIGINAL "..reason.."; all edited references restored")
end
local function owned(v)
    if not valid(v) or full(v):find("Default__",1,true) then return false end
    local owner=v:GetOuter();return valid(owner) and full(owner):find("BP_Renewal_Hun",1,true)~=nil
end
local function registerTimelineHooks()
    if timelineRegistered then return true end
    if type(RegisterHook)~="function" then return false end
    for _,spec in ipairs({
        {path="/Script/LegoAbility.LegoAbility:PlayTimeline",field="Timeline",kind="ObjectProperty"},
        {path="/Script/LegoAbility.LegoAbility:PlayTimelineByName",field="TimelineName",kind="NameProperty"},
    }) do
        local ok,fn=pcall(StaticFindObject,spec.path)
        local index,paramKind,names=nil,nil,{}
        if ok and valid(fn) then
            local reflected=pcall(function() fn:ForEachProperty(function(p)
                local name=p:GetFName():ToString()
                if name~="ReturnValue" then
                    names[#names+1]=name
                    if name==spec.field then index=#names;paramKind=p:GetClass():GetFName():ToString() end
                end
            end) end)
            if not reflected then index=nil end
        end
        if index and paramKind==spec.kind then
            local path,targetIndex=spec.path,index
            local callback=function(context,...)
                if not enabled or not ability then return end
                local args={...}
                local checked,err=pcall(function()
                    local self=unwrap(context)
                    if not valid(self) or full(self)~=full(ability) then return end
                    local value=unwrap(args[targetIndex])
                    local name
                    if valid(value) then
                        local identity=full(value)
                        name=identity:match("%.(Release_0[123])$") or identity:match("%.(Main)$")
                        if not name then name=value:GetFName():ToString() end
                    elseif kind(value)=="FName" then name=value:ToString()
                    elseif type(value)=="string" then name=value end
                    if name=="Main" then
                        if released or releasePending or releaseClosed or not castStarted then startCast("Main timeline",ability.ChargeCount) end
                        return
                    end
                    if name and name:match("^Release_0[123]$") then
                        if not castStarted and not released then startCast("release before active sample",ability.ChargeCount) end
                        if released and chargeResetSeen then startCast("release after charge reset",ability.ChargeCount) end
                        if released then return end
                        releasePending=name -- only a marker; audio IPC happens on the game-thread timer
                        releaseBranch=name
                        releaseCharge=math.max(highestStage,ability.ChargeCount)
-- DEV-BEGIN
                        hitCounts={marker=0,matched=0}
-- DEV-END
                        groundSeen,releaseClosed,hitSeen,hitPlayed=false,false,{},false
                        local action=groundActions[name]
                        groundBaseline=valid(action) and action.PlayingID or 0
                    end
                end)
                if not checked then log("ERROR timeline callback "..tostring(err)) end
                -- Never override arguments, the function return value, or its gameplay result.
            end
            held[#held+1]=callback
            local registered,pre,post=pcall(RegisterHook,path,callback,function() end)
            if registered and type(pre)=="number" and type(post)=="number" then
                timelineRegistered=true
                log("HOOK release timeline "..path.." params="..table.concat(names,","))
            else log("HOOK_UNAVAILABLE "..path.." "..tostring(pre)) end
        else log("HOOK_UNAVAILABLE "..spec.path.." signature="..table.concat(names,",")) end
    end
    return timelineRegistered
end
-- Hook the game's hit-target Blueprint event, rather than a native damage method.
-- Enumerate only loaded classes: no asset loading and no guessed function names.
local function registerTargetHooks()
    if targetRegistered then return end
    local schema=StaticFindObject("/Script/SGameCombatSystem.BulletEventData")
    local actorVerified,bodyVerified,componentVerified,ownerVerified=false,false,false,false
    if schema then pcall(function() schema:ForEachProperty(function(p)
        if p:GetFName():ToString()=="EventActor" and p:GetClass():GetFName():ToString()=="ObjectProperty" then actorVerified=true end
        if p:GetFName():ToString()=="EventBody" and p:GetClass():GetFName():ToString()=="StructProperty" then bodyVerified=true end
    end) end) end
    local socketSchema=StaticFindObject("/Script/SGameUtils.ComponentSocket")
    if socketSchema then pcall(function() socketSchema:ForEachProperty(function(p)
        if p:GetFName():ToString()=="Component" and p:GetClass():GetFName():ToString()=="ObjectProperty" then componentVerified=true end
    end) end) end
    local getter=StaticFindObject("/Script/Engine.ActorComponent:GetOwner")
    if valid(getter) then
        local inputs,result=0,nil
        pcall(function() getter:ForEachProperty(function(p)
            if p:GetFName():ToString()=="ReturnValue" then result=p:GetClass():GetFName():ToString() else inputs=inputs+1 end
        end) end)
        ownerVerified=inputs==0 and result=="ObjectProperty"
    end
    local function eventTarget(data)
        local actor=unwrap(data.EventActor)
        if isCharacter(actor) then
-- DEV-BEGIN
            diagnoseHit("target fields","EventActor="..full(actor).." resolved=EventActor")
-- DEV-END
            return actor,"EventActor"
        end
        local component,owner
        if bodyVerified and componentVerified and ownerVerified then
            local body=unwrap(data.EventBody)
            if kind(body)=="UScriptStruct" or type(body)=="table" then
                component=unwrap(body.Component)
                if valid(component) then
                    local cls=component:GetClass()
                    for _=1,16 do
                        if not valid(cls) then break end
                        if full(cls):match("[%. ]ActorComponent$") then owner=unwrap(component:GetOwner());break end
                        cls=cls:GetSuperStruct()
                    end
                end
            end
        end
-- DEV-BEGIN
        diagnoseHit("target fields","EventActor="..full(actor).." actor_kind="..kind(actor).." EventBody.Component="..full(component).." component_owner="..full(owner))
-- DEV-END
        return owner,"EventBody.Component.GetOwner"
    end
    local function belongsToUltimate(bullet)
        local seen,player={},ability:GetOuter()
-- DEV-BEGIN
        local last="initial_kind="..kind(bullet)
-- DEV-END
        for _=1,8 do
            if not valid(bullet) or seen[full(bullet)] then break end
            seen[full(bullet)]=true
            local owner=readKnown(bullet,"BulletOwnerAvatar")
            local source=readKnown(bullet,"BulletSourceAbility")
            local data=readKnown(bullet,"BulletData")
            if not valid(data) then data=readKnown(bullet,"MyData") end
            local branch=bulletData[full(data)]
-- DEV-BEGIN
            last="bullet="..full(bullet).." owner="..full(owner).." ability="..full(source).." data="..full(data)
-- DEV-END
            if valid(source) and full(source)~=full(ability) then
-- DEV-BEGIN
                diagnoseHit("target different ability",full(source))
-- DEV-END
                return false
            end
            if full(owner)==full(player) and (full(source)==full(ability) or (branch and branch.Release_03)) then return true end
            bullet=readKnown(bullet,"ParentBullet")
        end
-- DEV-BEGIN
        diagnoseHit("target source",last)
-- DEV-END
        return false
    end
    local function inspect(cls)
        if not valid(cls) then return end
        local className=full(cls)
        local count=0
-- DEV-BEGIN
        local registered=0
-- DEV-END
        local ok,err=pcall(function() cls:ForEachFunction(function(fn)
            count=count+1;if count>96 then return true end
            if not valid(fn) then return end
            local path=full(fn):match("^Function (/.+)$")
            if not path or path:match(":([^:]+)$")~="Trigger" then return end
            local flags=fn:GetFunctionFlags()
            if type(flags)~="number" or (flags & 0x00110000)~=0 then return end
            local names,kinds={},{}
            fn:ForEachProperty(function(p)
                local name=p:GetFName():ToString()
                if name~="ReturnValue" then names[#names+1]=name;kinds[#kinds+1]=p:GetClass():GetFName():ToString() end
            end)
-- DEV-BEGIN
            log("HIT_API function="..path.." flags="..flags.." params="..table.concat(names,",").." types="..table.concat(kinds,","))
-- DEV-END
            -- A Blueprint override exists under /Asset/...; /Script methods may
            -- run directly in C++ and did not fire in the previous game logs.
            if path:sub(1,8)=="/Script/" then return end
            local bulletIndex,eventIndex
            for i,name in ipairs(names) do
                if name=="SourceBullet" and kinds[i]=="InterfaceProperty" then bulletIndex=i end
                if name=="EventData" and kinds[i]=="StructProperty" and actorVerified then eventIndex=i end
            end
            if not eventIndex or not bulletIndex then
                log("HIT_API_SKIP unverified hit parameter layout "..path);return
            end
-- DEV-BEGIN
            local calls=0
-- DEV-END
            local callback=function(context,...)
-- DEV-BEGIN
                calls=calls+1

                if calls<=3 then log("TARGET_CALLBACK raw="..calls.." path="..path.." full_charge="..tostring(fullChargeWindow())) end
-- DEV-END
                if not fullChargeWindow() then return end
-- DEV-BEGIN
                hitCounts.marker=hitCounts.marker+1
-- DEV-END
                local args={...}
                local checked,why=pcall(function()
                    local bullet=unwrap(args[bulletIndex])
                    local data=unwrap(args[eventIndex])
                    if kind(data)~="UScriptStruct" and type(data)~="table" then
-- DEV-BEGIN
                        diagnoseHit("target event type",kind(data))
-- DEV-END
                        return
                    end
                    local enemy,resolvedBy=eventTarget(data)
                    if not isCharacter(enemy) or full(enemy)==full(ability:GetOuter()) then
-- DEV-BEGIN
                        diagnoseHit("target actor",full(enemy))
-- DEV-END
                        return
                    end
                    if not belongsToUltimate(bullet) then return end
                    queueHit(enemy,"marker "..path.." target="..resolvedBy)
-- DEV-BEGIN
                    diagnoseHit("target callback","bullet_kind="..kind(bullet).." bullet="..full(bullet).." actor="..full(enemy))

                    diagnoseHit("target bullet","owner="..full(readKnown(bullet,"BulletOwnerAvatar")).." source="..full(readKnown(bullet,"BulletSourceAbility")).." data="..full(readKnown(bullet,"BulletData")))
-- DEV-END
                end)
                if not checked then log("ERROR hit callback "..tostring(why)) end
            end
            held[#held+1]=callback
            -- UE4SS's Blueprint hook uses its single script callback slot.
            local hooked,pre,post=pcall(RegisterHook,path,callback)
            if hooked and type(pre)=="number" and type(post)=="number" then
                targetRegistered=true
-- DEV-BEGIN
                registered=registered+1
-- DEV-END
                log("HOOK hit target "..path.." mode=script params="..table.concat(names,","))
            else log("TARGET_HOOK_UNAVAILABLE "..path.." "..tostring(pre)) end
        end) end)
        if not ok then log("TARGET_DISCOVERY_PARTIAL "..className.." "..tostring(err)) end
-- DEV-BEGIN
        log("HIT_API_CLASS "..className.." functions="..count.." registered="..registered.." body_schema="..tostring(bodyVerified and componentVerified).." owner_getter="..tostring(ownerVerified))
-- DEV-END
    end
    local marker=StaticFindObject("/PBZCombatAsset/Prototypes/Bullet/Events/PBZ_BulletEvent_MarkBulletHitTarget.PBZ_BulletEvent_MarkBulletHitTarget_C")
    if not valid(marker) and not targetWaitLogged then
        targetWaitLogged=true;log("TARGET_WAIT hit-marker Blueprint class not loaded; retrying without asset loads")
    end
    inspect(marker)
end
local function enable()
    if enabled or waiting then return end
    session=os.date("%Y%m%d-%H%M%S").."-"..math.random(100000,999999)
    history={};sequence=0;startedAt=os.time();nextHeartbeat=0;nextDiscover=0;waiting=true
    lastHostBeat,hostReadMiss=nil,false
    ipcFailures={};dirtyCommands=not writeText("command.txt","")
    writeText("heartbeat.txt",session.."|"..os.time())
    local exe,ipc=root.."AudioHost.exe",root.."Runtime"
    if exe:find("'",1,true) or ipc:find("'",1,true) then error("unsupported install path") end
    local ps="Start-Process -FilePath '"..exe.."' -ArgumentList @('"..ipc.."','"..session.."') -WindowStyle Hidden"
    os.execute('powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -Command "'..ps..'"')
    log("HOST_LAUNCH default replacement")
end
local function discover()
    local selected
    for _,v in ipairs(FindAllOf("GA_Hun_ChiRen_C_C") or {}) do if owned(v) then selected=v;break end end
    if not selected then return end
    local props=fields(selected)
    if props.bIsActive~="BoolProperty" or props.ChargeCount~="IntProperty" then error("unverified bIsActive/ChargeCount properties") end
    if ability and full(ability)==full(selected) then registerTargetHooks();return end
    if not registerTimelineHooks() then error("release timeline hook unavailable; originals left intact") end
    registerTargetHooks()
    restore()
    local prefix=full(selected):match("^%S+ (.+)$").."."
    local matches,counts={},{}
    groundActions,bulletData={},{}
    for _,action in ipairs(FindAllOf("GAA_PlaySound_Opt_C") or {}) do
        local actionName=full(action)
        if valid(action) and actionName:find(prefix,1,true) then
            local suffix=actionName:sub((actionName:find(prefix,1,true) or 0)+#prefix)
            if suffix:match("^Main%.") or suffix:match("^Release_0[123]%.") then
                if fields(action).AkEvent=="ObjectProperty" then
                    local event=action.AkEvent
                    local eventName=full(event)
                    local branch=suffix:match("^(Release_0[123])%.")
                    if branch and eventName:match("%.SFX_Combat_Special_LionDancer_HitGround_Stone_Light$")
                        and fields(action).PlayingID=="IntProperty" then
                        groundActions[branch]=action
-- DEV-BEGIN
                        log("GROUND_NODE "..branch.." "..actionName.." observe=PlayingID")
-- DEV-END
                    end
                    local short=eventName:match("%.(SFX_Combat_Hun_ChiRen_[%w_]+)$")
                    if short and TARGETS[short] and eventName:find("/Game/Wwise/Events/SFX/Combat/",1,true) then
                        matches[#matches+1]={action=action,event=event};counts[short]=(counts[short] or 0)+1
                    end
                end
            end
        end
    end
    local dataFound,actions=pcall(FindAllOf,"GAA_BulletBurstWithDeflect_C")
    for _,action in ipairs(dataFound and actions or {}) do
        if valid(action) and full(action):find(prefix,1,true) and fields(action).BulletData=="ObjectProperty" then
            local data=action.BulletData
            local branch=full(action):sub((full(action):find(prefix,1,true) or 0)+#prefix):match("^(Release_0[123])%.")
            if valid(data) and branch then collectBulletData(data,branch) end
        end
    end
    if not next(bulletData) then log("HIT_UNAVAILABLE ultimate bullet data not found; charge/ground audio remain enabled") end
    if (counts.SFX_Combat_Hun_ChiRen_Fire_Charge or 0)<2 or (counts.SFX_Combat_Hun_ChiRen_Blade_Buff or 0)<3 then
        log("WAIT charge actions incomplete; originals intact");return
    end
    for _,n in ipairs({"01","02","03"}) do
        if not counts["SFX_Combat_Hun_ChiRen_C_Release_"..n] then log("WAIT Release_"..n.." sound missing");return end
    end
    patched=matches
    for _,item in ipairs(patched) do
        item.action.AkEvent=nil
        if valid(item.action.AkEvent) then error("mute assignment failed") end
-- DEV-BEGIN
        log("MUTED "..full(item.action))
-- DEV-END
    end
    ability,lastActive=selected,selected.bIsActive==true
    previousCount=selected.ChargeCount
    highestStage=lastActive and previousCount or 0
    released=false;releasePending=false
    castStarted,chargeResetSeen=lastActive,false
    if lastActive then
        castSerial=castSerial+1
-- DEV-BEGIN
        log("CAST_RESUME cast="..castSerial.." ChargeCount="..previousCount)
-- DEV-END
    end
    releaseBranch,hitPlayed=nil,false
    groundSeen,releaseClosed,hitSeen=false,false,{}
    log("ARMED stage-driven; muted="..#matches.." initial_count="..tostring(previousCount))
end
local function sample()
    local current=ability.bIsActive==true
    local count=ability.ChargeCount
    if type(count)~="number" or count<0 or count>3 then error("ChargeCount outside verified 0..3: "..tostring(count)) end
    if current and released and count==0 and (previousCount or 0)>0 then
        chargeResetSeen=true
-- DEV-BEGIN
        log("CHARGE_RESET while active after release; awaiting new charge or Main timeline")
-- DEV-END
    end
    if current and released and chargeResetSeen and count>0 then
        startCast("charge resumed without inactive frame",count)
    elseif current and not lastActive and not releasePending and not castStarted then
        startCast("active transition",count)
    end
-- DEV-BEGIN
    if count~=previousCount then log("CHARGE_COUNT "..tostring(previousCount).." -> "..count.." active="..tostring(current)) end
-- DEV-END
    if current and not released and count>highestStage then
        -- No made-up intermediate timing if a native update jumps multiple levels.
-- DEV-BEGIN
        if count>highestStage+1 then log("STAGES_SKIPPED "..highestStage.." -> "..count) end
-- DEV-END
        highestStage=count
        command("play"..count)
-- DEV-BEGIN
        log("PLAY clip="..count.." reason=ChargeCount "..count)
-- DEV-END
    end
    if releasePending and not released then
        released=true
-- DEV-BEGIN
        log("RELEASE "..releasePending.." charge="..releaseCharge.." cast="..castSerial.." ground=01 unless hit; full-charge target replaces 01 with 12,11")
-- DEV-END
        releasePending=false
    end
    if releaseBranch and not groundSeen and not releaseClosed then
        local action=groundActions[releaseBranch]
        local playing=valid(action) and action.PlayingID or 0
        if type(playing)=="number" and playing~=0 and playing~=groundBaseline then
            groundSeen=true
-- DEV-BEGIN
            log("GROUND_SOUND PlayingID="..tostring(playing).." branch="..releaseBranch)
-- DEV-END
            if not hitPlayed then
                command("play4:"..castSerial)
-- DEV-BEGIN
                log("PLAY clip=4 reason=ground sound branch="..releaseBranch.." cast="..castSerial)
-- DEV-END
            end
        end
    end
    if not current and lastActive then
-- DEV-BEGIN
        log("ULTIMATE_END released="..tostring(released))
-- DEV-END
        if not released then command("stop") end -- cancellation is not a release
-- DEV-BEGIN
        log("HIT_COUNTS marker="..hitCounts.marker.." matched="..hitCounts.matched)
-- DEV-END
        releaseClosed=true
        castStarted,chargeResetSeen=false,false
        highestStage=0
    end
    previousCount,lastActive=count,current
end
local function tick()
    ticks=ticks+1
    if ticks==1 or ticks%5==0 then
        local requested=readMenuSetting()
        if requested~=nil and requested~=desired then
            desired=requested;faulted=false
            log("MENU Enabled="..tostring(desired))
            if not desired then disable("menu off") end
        end
    end
    if desired and not faulted and not enabled and not waiting then enable() end
    if not enabled and not waiting then return false end
    local now=os.time()
    if now>=nextHeartbeat and writeText("heartbeat.txt",session.."|"..now) then nextHeartbeat=now+1 end
    if dirtyCommands and writeText("command.txt",table.concat(history,"\n").."\n") then dirtyCommands=false end
    for name,at in pairs(ipcFailures) do
        if os.clock()-at>=10 then faulted=true;disable("IPC write timeout "..name);return false end
    end
    if waiting then
        if hostReady() then waiting=false;enabled=true;log("HOST_READY independent stage audio")
        elseif now-startedAt>10 then faulted=true;disable("host startup timeout; toggle menu off/on to retry") end
        return false
    end
    local ready,reason=hostReady()
    if not ready then faulted=true;disable("host heartbeat lost ("..tostring(reason).."); toggle menu off/on to retry");return false end
    if ability and not owned(ability) then
        restore();ability=nil;lastActive=false;releasePending=false
        castStarted,chargeResetSeen=false,false
        releaseBranch=nil
        groundSeen,releaseClosed,hitSeen=false,true,{}
        groundActions,bulletData={},{};command("stop");log("WORLD_CHANGE")
    end
    if now>=nextDiscover then nextDiscover=now+2;discover() end
    if ability and owned(ability) then sample() end
    return false
end
local function run()
    local ok,err=pcall(tick)
    if not ok then faulted=true;disable("error "..tostring(err)) end
    return false
end
held[#held+1]=run
if type(LoopInGameThreadWithDelay)=="function" then
    LoopInGameThreadWithDelay(50,run)
    log("LOADED v1.0 verified hit dispatched directly from callback; prewarmed hit voices; same-cast 01 cancellation")
else log("ERROR no game-thread timer; originals intact") end
