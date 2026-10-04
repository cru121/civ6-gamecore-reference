# crawl.lua

Read-only walk of the Lua object graph in a UI state: lists every method of every distinct class reachable from the roots (Game, Map, Players[0], a city, a unit, a plot).

    civ.py luastates 3000 ; civ.py luaon <busiest long-lived UI state>
    python runlua.py luatests/crawl.lua > crawl_out.txt

Output: one line per class: `<class id>|<path>|<method,method,...>`. Only methods listed in the `ZERO` table (empty in this bundle, fill it in) are called to reach further objects.
Read LESSONS.md section 5 first.
