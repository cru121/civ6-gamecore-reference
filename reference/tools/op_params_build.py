"""Generate data/op_params.json (what each operation/command parameter means) and enrich data/operations.json parameter lists.

Sources: parameter enums (Linux DWARF), how the game's own Lua fills them (linux_depot/out/op_param_usage.json), handler parameter
structs (Linux DWARF ClassParameters, already in operations.json) and name conventions. Every statement is labelled verified (seen in
game scripts or code) or inferred (from the name)."""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')


def P(*a):
    return os.path.join(ROOT, *a)


E = {}
for l in open(P('linux_depot', 'out', 'enums.jsonl'), encoding='utf8'):
    j = json.loads(l)
    E[j['name']] = j
usage = json.load(open(P('linux_depot', 'out', 'op_param_usage.json')))
ENUMS = {'PlayerOperations': 'GameCore::Player::Operations::Parameters::ParameterTypes',
         'UnitOperationTypes': 'GameCore::Unit::Operations::Parameters::ParameterTypes',
         'UnitCommandTypes': 'GameCore::Unit::Commands::Parameters::ParameterTypes',
         'CityOperationTypes': 'GameCore::City::Operations::Parameters::ParameterTypes',
         'CityCommandTypes': 'GameCore::City::Commands::Parameters::ParameterTypes'}

DB = {'TECH': 'Technologies', 'CIVIC': 'Civics', 'BELIEF': 'Beliefs', 'RESOURCE': 'Resources', 'RELIGION': 'Religions', 'DISTRICT': 'Districts',
      'BUILDING': 'Buildings', 'UNIT': 'Units', 'PROJECT': 'Projects', 'IMPROVEMENT': 'Improvements', 'ROUTE': 'Routes', 'PROMOTION': 'UnitPromotions',
      'GOVERNOR': 'Governors', 'GOVERNOR_PROMOTION': 'GovernorPromotions', 'GREAT_PERSON_INDIVIDUAL': 'GreatPersonIndividuals', 'YIELD': 'Yields',
      'WMD': 'WMDs', 'EMERGENCY': 'Emergencies', 'COMMEMORATION': 'CommemorationTypes', 'RESOLUTION': 'Resolutions'}

# fixed meanings: name -> (summary, kind)
FIXED = {
    'PARAM_FLAGS': ('Bit flags for the operation; the meaning of the bits depends on the operation.', 'flags'),
    'PARAM_MODIFIERS': ('Modifier flags. For unit operations combine UnitOperationMoveModifiers.* values (for example ATTACK, MOVE_IGNORE_UNEXPLORED_DEST); otherwise operation specific.', 'flags'),
    'PARAM_INSERT_MODE': ('Where the entry goes in the queue: one of the VALUE_* constants of the same Lua table.', 'constant'),
    'PARAM_DIRECTIVE': ('Selects a sub-variant of the operation or command (a directive constant specific to it).', 'constant'),
    'PARAM_NAME': ('A name string.', 'string'),
    'PARAM_RELIGION_CUSTOM_NAME': ('The player-chosen name of the religion.', 'string'),
    'PARAM_CORPORATION_CUSTOM_NAME': ('The player-chosen name of the corporation.', 'string'),
    'PARAM_PLAYER_ONE': ('Id of the first player involved (usually the acting player).', 'player-id'),
    'PARAM_PLAYER_TWO': ('Id of the second player involved (the target or counterpart).', 'player-id'),
    'PARAM_OTHER_PLAYER': ('Id of the other player the operation is directed at.', 'player-id'),
    'PARAM_PLAYER': ('Player id.', 'player-id'),
    'PARAM_PLAYER0': ('Id of the first player involved.', 'player-id'),
    'PARAM_TEAM_ONE': ('Id of the first team involved.', 'team-id'),
    'PARAM_TEAM_TWO': ('Id of the second team involved.', 'team-id'),
    'PARAM_CITY_ONE': ('Id of the first city involved (the value returned by city:GetID()).', 'city-id'),
    'PARAM_CITY_TWO': ('Id of the second city involved.', 'city-id'),
    'PARAM_CITY_SRC': ('Id of the city the great work is taken from (city:GetID()).', 'city-id'),
    'PARAM_CITY_DEST': ('Id of the city the great work goes to (city:GetID()).', 'city-id'),
    'PARAM_BUILDING_SRC': ('Building type index (row index in the Buildings table) of the building the great work is taken from.', 'db-index'),
    'PARAM_BUILDING_DEST': ('Building type index of the building the great work goes to.', 'db-index'),
    'PARAM_GREAT_WORK_INDEX': ('Great work list index: the index of the work in the game-wide great work list (as returned by Cities:GetGreatWorkInSlot), not the row in the GreatWorks table.', 'index'),
    'PARAM_SLOT': ('Slot index inside the destination building.', 'index'),
    'PARAM_UNIT_ID': ('Id of the unit (unit:GetID()).', 'unit-id'),
    'PARAM_PLOT_ONE': ('Index of the first plot involved.', 'plot-index'),
    'PARAM_PLOT_TWO': ('Index of the second plot involved.', 'plot-index'),
    'PARAM_MOMENT_ID': ('Id of the historic moment.', 'id'),
    'PARAM_WORLD_CONGRESS_VOTES': ('Number of favor points spent on the vote (the game passes the sum, or votes times direction).', 'number'),
    'PARAM_RESOLUTION_SELECTION': ('Index of the chosen target or option set (0-based; the game passes target - 1).', 'index'),
    'PARAM_RESOLUTION_OPTION': ('The chosen outcome (A or B) of the resolution.', 'constant'),
    'PARAM_DISCUSSION_TYPE': ('Type of the discussion item.', 'id'),
    'PARAM_QUEUE_LOCATION': ('Position in the city production queue.', 'queue-index'),
    'PARAM_QUEUE_SOURCE_LOCATION': ('Position the queue entry is moved from.', 'queue-index'),
    'PARAM_QUEUE_DESTINATION_LOCATION': ('Position the queue entry is moved to.', 'queue-index'),
    'PARAM_IS_EXCLUSION_TEST': ('Flag used when testing whether an item would be excluded from the queue (meaning not determined).', 'boolean'),
    'PARAM_PLOT_PURCHASE': ('The plot to buy (supplied by the interface mode; plot index).', 'plot-index'),
    'PARAM_MANAGE_CITIZEN': ('The plot whose citizen assignment is changed (supplied by the interface mode).', 'plot-index'),
    'PARAM_SWAP_TILE_OWNER': ('The plot whose owner city is swapped (supplied by the interface mode).', 'plot-index'),
    'PARAM_RANGED_ATTACK': ('The target of the ranged attack (supplied by the interface mode).', 'plot-index'),
    'PARAM_OPERATION_TYPE': ('Hash of the unit operation to perform (for example the hash of a build action).', 'hash'),
    'PARAM_PRODUCTION_TYPE': ('Kind of production item.', 'constant'),
    'PARAM_MILITARY_FORMATION_TYPE': ('Military formation: one of the MilitaryFormationTypes constants (for example STANDARD_MILITARY_FORMATION, CORPS_MILITARY_FORMATION).', 'constant'),
    'PARAM_EMERGENCY_TYPE': ('The emergency being answered.', 'id'),
    'PARAM_COMMEMORATION_TYPE': ('The chosen commemoration.', 'id'),
    'PARAM_RESOLUTION_TYPE': ('Hash of the World Congress resolution.', 'hash'),
    'PARAM_YIELD_TYPE': ('Yield type (for example YieldTypes.GOLD or YieldTypes.FAITH, or the index of a row of the Yields table).', 'db-index'),
}


def describe(table, name):
    u = usage['params'].get('%s.%s' % (table, name), [])
    form = None
    if any('.Hash' in x or x.endswith('Hash') or 'hash' in x.lower() for x in u):
        form = 'hash'
    elif any('.Index' in x for x in u):
        form = 'index'
    m = re.match(r'^PARAM_(.+?)(\d)?_TYPE$', name)
    rec = {'value': {'kind': None}}
    if name in FIXED:
        s, k = FIXED[name]
        rec['summary'], rec['value']['kind'] = s, k
        if k in ('db-index', 'hash') and form:
            rec['value']['form'] = form
    elif m and m.group(1) in DB:
        tbl = DB[m.group(1)]
        which = ' (the %s one of the pair)' % ('first' if m.group(2) == '0' else 'second') if m.group(2) in ('0', '1') else ''
        if form == 'hash':
            rec['summary'] = 'Type of the %s%s, given as the hash of its row in the %s table (row.Hash).' % (m.group(1).lower().replace('_', ' '), which, tbl)
            rec['value'] = {'kind': 'hash', 'db_table': tbl, 'form': 'hash'}
        elif form == 'index':
            rec['summary'] = 'Type of the %s%s, given as the index of its row in the %s table (row.Index).' % (m.group(1).lower().replace('_', ' '), which, tbl)
            rec['value'] = {'kind': 'db-index', 'db_table': tbl, 'form': 'index'}
        else:
            rec['summary'] = 'Type of the %s%s: a row of the %s table (the game passes the row hash for most types; check the examples).' % (m.group(1).lower().replace('_', ' '), which, tbl)
            rec['value'] = {'kind': 'db-type', 'db_table': tbl}
    elif re.match(r'^PARAM_([XY])(\d)?$', name):
        ax = 'x (column)' if name[6] == 'X' else 'y (row)'
        d = name[7:]
        rec['summary'] = 'Plot %s coordinate%s.' % (ax, ' of the %s plot' % ('first' if d == '0' else 'second') if d in ('0', '1') else '')
        rec['value']['kind'] = 'plot-coord'
    elif re.match(r'^PARAM_(UNIT|CITY)(\d)?_PLAYER$', name):
        mm = re.match(r'^PARAM_(UNIT|CITY)(\d)?_PLAYER$', name)
        rec['summary'] = 'Id of the player who owns the %s%s.' % (mm.group(1).lower(), ' (%s one)' % ('first' if mm.group(2) == '0' else 'second') if mm.group(2) in ('0', '1') else '')
        rec['value']['kind'] = 'player-id'
    elif re.match(r'^PARAM_(UNIT|CITY)(\d)?_ID$', name):
        mm = re.match(r'^PARAM_(UNIT|CITY)(\d)?_ID$', name)
        rec['summary'] = 'Id of the %s%s (the value returned by %s:GetID()).' % (mm.group(1).lower(), ' (%s one)' % ('first' if mm.group(2) == '0' else 'second') if mm.group(2) in ('0', '1') else '', mm.group(1).lower())
        rec['value']['kind'] = mm.group(1).lower() + '-id'
    elif re.match(r'^PARAM_DATA(\d)$', name):
        rec['summary'] = 'Generic data slot %s; the meaning depends on the command (the game uses it for booleans passed as 1 or 0).' % name[-1]
        rec['value']['kind'] = 'generic'
    else:
        rec['summary'] = None
        rec['value']['kind'] = 'unknown'
    rec['examples'] = u[:4]
    return rec


params = []
by_id = {}
for table, cpp in ENUMS.items():
    for n, v in E[cpp]['values']:
        if not n.startswith('PARAM_'):
            continue
        d = describe(table, n)
        status = 'verified' if d['examples'] else 'inferred'
        ev = []
        if d['examples']:
            ev.append({'kind': 'game-script', 'note': 'filled by the game\'s own Lua scripts (examples listed)'})
        ev.append({'kind': 'dwarf', 'note': 'parameter id from the %s parameter enum' % table})
        if not d['examples']:
            ev.append({'kind': 'static-analysis', 'note': 'meaning inferred from the name'})
        rec = {'id': 'param:%s.%s' % (table, n), 'table': table, 'name': n, 'hash': '0x%08x' % (v & 0xffffffff), 'summary': d['summary'] or 'Meaning not determined.',
               'value': d['value'], 'examples': d['examples'], 'used_by': [], 'status': status, 'evidence': ev}
        params.append(rec)
        by_id[rec['id']] = rec

# enrich operations
ops = json.load(open(os.path.join(OUT, 'operations.json'), encoding='utf8'))


def snake_member(m):
    s = re.sub(r'^(?:e|i|b|ui|k|sz|x)(?=[A-Z])', '', m)
    return 'PARAM_' + re.sub(r'(?<!^)(?=[A-Z])', '_', s).upper()


for o in ops:
    table = o['lua'].split('.')[0]
    uses = usage['ops'].get(o['lua'], {})
    plist = {}
    for p in o['parameters']:
        nm = p['name'] if p['name'].startswith('PARAM_') else snake_member(p['name'])
        plist[nm] = {'name': nm, **({'cpp_name': p['name'], 'cpp_type': p.get('type')} if not p['name'].startswith('PARAM_') else {})}
    for nm in uses:
        plist.setdefault(nm, {'name': nm})
    for nm, rec in plist.items():
        pid = 'param:%s.%s' % (table, nm)
        if pid in by_id:
            rec['param'] = pid
            if o['id'] not in by_id[pid]['used_by']:
                by_id[pid]['used_by'].append(o['id'])
        if nm in uses:
            rec['game_examples'] = uses[nm][:3]
    o['parameters'] = list(plist.values())
json.dump(ops, open(os.path.join(OUT, 'operations.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(params, open(os.path.join(OUT, 'op_params.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
import collections
print(len(params), 'parameters;', dict(collections.Counter(p['status'] for p in params)), '; unknown meaning:', [p['name'] for p in params if p['summary'].startswith('Meaning')][:20])
print('ops with at least one example:', sum(1 for o in ops if any(x.get('game_examples') for x in o['parameters'])), 'of', len(ops))
