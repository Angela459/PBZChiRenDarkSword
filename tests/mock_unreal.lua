
files, printed, keys = {}, {}, {}
calls, fieldReads, propertyCalls = 0, {}, 0
clock, failFind, rootAlive = 1000, false, true
os.time = function() return clock end
os.date = function() return 'mock-session' end
print = function(message) printed[#printed+1] = message end
io.open = function(path, mode)
    if mode == 'r' and files[path] == nil then return nil end
    if mode == 'w' then files[path] = '' end
    files[path] = files[path] or ''
    return {
        write=function(_, value) files[path]=files[path]..value end,
        read=function() return files[path] end,
        flush=function() end, close=function() end,
    }
end
local function name(value) return {ToString=function() return value end} end
local function schema(fields)
    return {
        type=function() return 'UClass' end, IsValid=function() return true end,
        GetFullName=function() return 'Class Mock' end,
        GetSuperStruct=function() return nil end,
        ForEachProperty=function(_, callback)
            propertyCalls = propertyCalls+1
            for field, k in pairs(fields) do
                callback({GetFName=function() return name(field) end,
                    GetClass=function() return {GetFName=function() return name(k) end} end})
            end
        end,
    }
end
local function object(id, fields, values, alive)
    local cls = schema(fields)
    local methods = {
        type=function() return 'UObject' end,
        IsValid=function() return not alive or rootAlive end,
        GetFullName=function() return id end, GetClass=function() return cls end,
    }
    return setmetatable({}, {__index=function(_, field)
        if methods[field] then return methods[field] end
        if fields[field] then
            fieldReads[#fieldReads+1] = id..'.'..field
            return values[field]
        end
        error('UNDECLARED UObject field or method: '..field)
    end})
end
makeObject, makeSchema = object, schema
event = object('AkAudioEvent /Game/Audio/Charge', {ShortID='UInt32Property',
    EventCookedData='StructProperty'}, {ShortID=12345})
action = object('LGAAction_PlaySoundDefault Mock.Sound', {AkEvent='ObjectProperty'}, {AkEvent=event})
rowFields = {Action='ObjectProperty', StartTime='FloatProperty'}
row = setmetatable({}, {__index=function(_, field)
    if field=='type' then return function() return 'UScriptStruct' end end
    if field=='IsValid' then return function() return true end end
    if field=='Action' then return action end
    if field=='StartTime' then return 0.25 end
    error('UNDECLARED STRUCT field or UObject method: '..field)
end})
local array = {type=function() return 'TArray' end, ForEach=function(_, fn)
    fn(1, {type=function() return 'LocalUnrealParam' end, get=function() return row end})
end}
timeline = object('LGATimeline Mock.Main', {Actions='ArrayProperty'}, {Actions=array})
local rootId = 'GA_Hun_ChiRen_C_C Mock.BP_Renewal_Hun_C.ChiRen'
ability = object(rootId, {Main='ObjectProperty', ChargeCount='IntProperty', CanRelease='BoolProperty'},
    {Main=timeline, ChargeCount=0, CanRelease=false}, true)
local owner = object('BP_Renewal_Hun_C Mock.Player', {}, {})
local oldIndex = getmetatable(ability).__index
getmetatable(ability).__index = function(obj, field)
    if field=='GetOuter' then return function() return owner end end
    return oldIndex(obj, field)
end
FindAllOf = function(class)
    calls = calls+1
    assert(class=='GA_Hun_ChiRen_C_C', 'non-ultimate scan')
    if failFind then error('simulated native API rejection') end
    return {ability}
end
StaticFindObject = function(path)
    assert(path=='/Script/LegoAbility.LGAActionEvent')
    return schema(rowFields)
end
RegisterHook = function() error('Hooks must never be registered') end
Key={F7=7,F8=8}; ModifierKey={CONTROL=1,ALT=2}
RegisterKeyBind = function(key, modifiers, fn) keys[key]=fn end
LoopInGameThreadWithDelay = function(delay, fn) assert(delay==200); pump=fn; return 1 end
function advance(count)
    for i=1,count do clock=clock+0.2; pump() end
end
function report()
    local result=''
    for path, value in pairs(files) do
        if path:match('capture.log$') then result=result..value end
    end
    return result
end
