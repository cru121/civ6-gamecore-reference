"""Shared vocabulary for Lua value meanings: C++ type -> meaning, variable-name rules."""
import re


TABLES = {'Building': 'Buildings', 'District': 'Districts', 'Unit': 'Units', 'Improvement': 'Improvements', 'Resource': 'Resources', 'Feature': 'Features',
          'Terrain': 'Terrains', 'Continent': 'Continents', 'Civilization': 'Civilizations', 'Leader': 'Leaders', 'Era': 'Eras', 'Government': 'Governments',
          'Policy': 'Policies', 'Belief': 'Beliefs', 'Religion': 'Religions', 'Tech': 'Technologies', 'Civic': 'Civics', 'Project': 'Projects', 'Route': 'Routes',
          'Governor': 'Governors', 'GovernorPromotion': 'GovernorPromotions', 'UnitAbility': 'UnitAbilities', 'UnitPromotion': 'UnitPromotions',
          'UnitPromotionClass': 'UnitPromotionClasses', 'GreatPersonClass': 'GreatPersonClasses', 'GreatPersonIndividual': 'GreatPersonIndividuals',
          'GreatWork': 'GreatWorks', 'GreatWorkObject': 'GreatWorkObjectTypes', 'GreatWorkSlot': 'GreatWorkSlotTypes', 'Yield': 'Yields', 'Agenda': 'Agendas',
          'Trait': 'Traits', 'Specialty': 'Specialties', 'WMD': 'WMDs', 'Victory': 'Victories', 'Emergency': 'Emergencies', 'Resolution': 'Resolutions',
          'Disaster': 'RandomEvents', 'Notification': 'Notifications', 'Corporation': 'Corporations', 'Industry': 'Industries', 'Alliance': 'Alliances',
          'DiplomaticAction': 'DiplomaticActions', 'Formation': 'MilitaryFormations', 'Domain': 'Domains', 'Citizen': 'CitizenYields',
          'FreeCity': 'FreeCities', 'Boost': 'Boosts', 'CityState': 'MinorCivs', 'Commemoration': 'CommemorationTypes', 'Moment': 'Moments'}


def cpp_meaning(t):
    """Meaning of a C++ return type name, or None."""
    t = t.replace('GameCore::', '').strip()
    if t == 'PlayerTypes':
        return ('player-id', 'Id of a player (as in Players[id]).', None)
    if t == 'TeamTypes':
        return ('team-id', 'Id of a team.', None)
    if t == 'GreatWorkListIndex':
        return ('index', 'Great work list index: the index of a work in the game-wide great work list (not the row in the GreatWorks table).', None)
    if t in ('PlotIndex', 'PlotIndexType'):
        return ('plot-index', 'Plot index (as accepted by Map.GetPlotByIndex).', None)
    m = re.match(r'^(\w+?)Types$', t)
    if m:
        base = m.group(1)
        if base in TABLES:
            return ('db-index', 'Index of a row of the %s table (the value of GameInfo.%s[...].Index).' % (TABLES[base], TABLES[base]), TABLES[base])
        return ('db-index', 'Value of the %sTypes enum (a type index).' % base, None)
    return None


NAME_RULES = [
    (re.compile(r'(player|owner|civ)(id)?$|^i?player', re.I), 'player-id', 'Id of a player (the scripts name the result playerID / owner).'),
    (re.compile(r'city.*id$|^i?city$', re.I), 'city-id', 'Id of a city (the scripts name the result cityID).'),
    (re.compile(r'unit.*id$|^i?unit$', re.I), 'unit-id', 'Id of a unit (the scripts name the result unitID).'),
    (re.compile(r'plot.*(index|id)$|^i?plot$', re.I), 'plot-index', 'Plot index (the scripts name the result plotIndex / plotID).'),
    (re.compile(r'^(?:i|n)?[xX]$|[a-z][X]$|^plotx$'), 'plot-coord', 'Plot x coordinate (the scripts name the result x / plotX).'),
    (re.compile(r'^(?:i|n)?[yY]$|[a-z][Y]$|^ploty$'), 'plot-coord', 'Plot y coordinate (the scripts name the result y / plotY).'),
    (re.compile(r'turn', re.I), 'turn', 'A turn number (the scripts name the result turn).'),
    (re.compile(r'(count|num|number|amount|total)', re.I), 'count', 'A count or amount (the scripts name the result count / num / amount).'),
    (re.compile(r'hash$', re.I), 'hash', 'Hash of a database row (the scripts name the result hash).'),
]


def name_meaning(names, total):
    """names: [(var, count)]. Needs the most common names to agree on one rule."""
    votes = {}
    for v, c in names:
        stem = re.sub(r'^(?:e|i|b|k|p|n|m_|g_|l_)(?=[A-Z])', '', v)
        for rx, kind, text in NAME_RULES:
            if rx.search(stem) or rx.search(v):
                votes.setdefault((kind, text), 0)
                votes[(kind, text)] += c
                break
    if not votes:
        return None
    (kind, text), n = max(votes.items(), key=lambda x: x[1])
    return (kind, text) if n >= 0.6 * sum(c for _, c in names) else None


