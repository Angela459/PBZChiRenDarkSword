
files, printed = {}, {}
calls, fieldReads, propertyCalls = 0, {}, 0
clock, rootAlive = 1000, true
os.time = function() return clock end
os.date = function() return 'mock-session' end
print = function(message) printed[#printed+1] = message end
io.open = function(path, mode)
    if mode == 'r' and files[path] == nil then return nil end
    if mode == 'w' then files[path] = '' end
    files[path] = files[path] or ''
    return {
        write=function(_, value) files[path]=files[path]..value end,
        read=function(_, format)
            if format == '*l' then return files[path]:match('([^\r\n]*)') end
            return files[path]
        end,
        flush=function() return true end, close=function() return true end,
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
Key={}
