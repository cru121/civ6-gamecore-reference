local ZERO = {}   -- FILL IN: names of methods you KNOW take no arguments (e.g. GetCulture = true). Only these are called while crawling; a wrong guess can fault natively.
-- Crawl the Lua object graph of a UI lua_State and list the methods of every distinct class (read-only: only zero-argument Get* methods that
-- return objects are called to reach further objects). Output: one line per class: <class id>|<path>|<method,method,...>
local classes, order, calls = {}, {}, 0
local MAXCALLS = 600
local SKIP = { GetMetatable = true, GetCityByID = false }

local function classOf(o)
  local t = type(o)
  if t ~= 'table' and t ~= 'userdata' then return nil end
  local ok, mt = pcall(getmetatable, o)
  if not ok or type(mt) ~= 'table' then return nil end
  local idx = mt.__index
  if type(idx) ~= 'table' then return nil end
  return tostring(idx), idx
end

local function methodsOf(idx)
  local out = {}
  for k, v in pairs(idx) do if type(v) == 'function' then out[#out + 1] = tostring(k) end end
  table.sort(out)
  return out
end

local queue = {}
local function visit(o, path, depth)
  local id, idx = classOf(o)
  if not id or classes[id] then return end
  classes[id] = { path = path, methods = methodsOf(idx) }
  order[#order + 1] = id
  queue[#queue + 1] = { o = o, path = path, depth = depth, id = id }
end

local function tryGet(o, name, path, depth)
  if calls >= MAXCALLS then return end
  calls = calls + 1
  CRAWL_LAST = path .. ':' .. name
  local ok, a, b = pcall(o[name], o)
  if ok then
    if type(a) == 'table' or type(a) == 'userdata' then visit(a, path .. ':' .. name .. '()', depth) end
  end
end

-- static tables (plain tables with function fields)
local function staticTable(name, t)
  if type(t) ~= 'table' then return end
  local m = {}
  for k, v in pairs(t) do if type(v) == 'function' then m[#m + 1] = tostring(k) end end
  table.sort(m)
  if #m > 0 then classes['static:' .. name] = { path = name, methods = m }; order[#order + 1] = 'static:' .. name end
end
local STATICS = { Game = Game, Map = Map, Players = Players, PlayerManager = PlayerManager, Cities = Cities, Units = Units, GameInfo = GameInfo,
                  Locale = Locale, Network = Network, UI = UI, Calendar = Calendar, Automation = Automation, GameConfiguration = GameConfiguration,
                  MapConfiguration = MapConfiguration, PlayerConfigurations = PlayerConfigurations, Teams = Teams, Controls = Controls, Input = Input,
                  Options = Options, Events = Events, LuaEvents = LuaEvents }
for n, t in pairs(STATICS) do staticTable(n, t) end

-- roots
local p = Players[0]
visit(p, 'Players[0]', 1)
visit(Players, 'Players', 1)
visit(Map, 'Map', 1)
visit(Game, 'Game', 1)
local cap
do local ok, c = pcall(function() return p:GetCities():GetCapitalCity() end); if ok then cap = c; visit(cap, 'capital', 1) end end
do local ok, u = pcall(function() for _, uu in p:GetUnits():Members() do return uu end end); if ok and u then visit(u, 'firstUnit', 1) end end
do local ok, pl = pcall(function() return Map.GetPlotByIndex(0) end); if ok and pl then visit(pl, 'plot0', 1) end end

local i = 1
while i <= #queue and calls < MAXCALLS do
  local q = queue[i]; i = i + 1
  if q.depth < 3 then
    for _, name in ipairs(classes[q.id].methods) do
      if ZERO[name] and not name:match('Next') and not name:match('Pop') and not name:match('Random') then tryGet(q.o, name, q.path, q.depth + 1) end
    end
  end
end

local lines = {}
for _, id in ipairs(order) do
  local c = classes[id]
  lines[#lines + 1] = id .. '|' .. c.path .. '|' .. table.concat(c.methods, ',')
end
lines[#lines + 1] = '#calls=' .. calls
return table.concat(lines, '\n')
