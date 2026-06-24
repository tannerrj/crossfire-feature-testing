#!/usr/bin/env python3
"""
test_citylife_config.py -- Validate the world.citylife NPC spawn configuration.

Parses fixtures/world.citylife using the same logic as the C++ citylife server
module (server/modules/citylife.cpp: load_citylife()) and checks that every
map entry is internally consistent and has coordinates within valid map bounds.

No running Crossfire server is required.

Usage (from the project root directory):
    python3 tests/test_citylife_config.py

Exit code 0 = all checks passed, 1 = one or more failures.
"""

import sys
import os
import re
import traceback

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

_passed   = 0
_failed   = 0
_failures = []

def check(description, condition):
    global _passed, _failed
    if condition:
        _passed += 1
        print('  PASS  %s' % description)
    else:
        _failed += 1
        _failures.append(description)
        print('  FAIL  %s' % description)

def section(title):
    print('\n--- %s ---' % title)

# ---------------------------------------------------------------------------
# Parser (mirrors load_citylife() in server/modules/citylife.cpp)
#
# Format:
#   Lines beginning with '#' or empty lines are ignored.
#   Each directive is:  keyword<space>value(s)
#   'map'        starts a new entry (or resumes an existing one)
#   'population' sets the max NPC count at map load (last value wins)
#   'zone'       appends a rectangular spawn region: sx sy ex ey
#   'point'      appends a spawn point: x y
#   'arch'       appends an NPC archetype name
#
# A directive block without a preceding 'map' line is a parse error.
# A 'map' line with an already-seen path resumes that entry (fall-through).
# ---------------------------------------------------------------------------

def parse_citylife(path):
    """
    Parse a .citylife file.

    Returns:
        maps   -- dict mapping map_path to:
                  { 'population': int,
                    'zones':      [(sx, sy, ex, ey), ...],
                    'points':     [(x, y), ...],
                    'archetypes': [str, ...] }
        errors -- list of parse-error strings (empty if clean)
    """
    maps    = {}
    current = None
    errors  = []

    with open(path, 'r') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip('\r\n')
            if not line or line[0] == '#':
                continue

            sp = line.find(' ')
            if sp == -1:
                errors.append('line %d: no value after keyword: %r' % (lineno, line))
                continue

            keyword = line[:sp]
            value   = line[sp + 1:]

            if keyword == 'map':
                if value not in maps:
                    maps[value] = {
                        'population': 0,
                        'zones':      [],
                        'points':     [],
                        'archetypes': [],
                    }
                current = maps[value]

            elif keyword == 'population':
                if current is None:
                    errors.append('line %d: population without preceding map' % lineno)
                else:
                    current['population'] = int(value)

            elif keyword == 'zone':
                parts = value.split()
                if len(parts) != 4:
                    errors.append('line %d: zone needs 4 values, got %d' % (lineno, len(parts)))
                elif current is None:
                    errors.append('line %d: zone without preceding map' % lineno)
                else:
                    sx, sy, ex, ey = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                    current['zones'].append((sx, sy, ex, ey))

            elif keyword == 'point':
                parts = value.split()
                if len(parts) != 2:
                    errors.append('line %d: point needs 2 values, got %d' % (lineno, len(parts)))
                elif current is None:
                    errors.append('line %d: point without preceding map' % lineno)
                else:
                    current['points'].append((int(parts[0]), int(parts[1])))

            elif keyword == 'arch':
                if current is None:
                    errors.append('line %d: arch without preceding map' % lineno)
                else:
                    current['archetypes'].append(value.strip())

            else:
                errors.append('line %d: unknown keyword %r' % (lineno, keyword))

    return maps, errors

# ---------------------------------------------------------------------------
# World map tile dimensions (Crossfire world maps are 50 x 50 tiles).
# spawn zones use half-open intervals: sx <= x < ex, so ex=50 is valid.
# spawn points are tile indices: 0 <= x < MAP_SIZE.
# ---------------------------------------------------------------------------

MAP_SIZE = 50

FIXTURES_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fixtures')
CITYLIFE_FILE = os.path.join(FIXTURES_DIR, 'world.citylife')

try:
    # -----------------------------------------------------------------------
    # File and parser
    # -----------------------------------------------------------------------
    section('File and parser')

    check('fixtures/world.citylife exists',
          os.path.isfile(CITYLIFE_FILE))

    maps, errors = parse_citylife(CITYLIFE_FILE)

    check('file parses without errors',
          len(errors) == 0)
    if errors:
        for e in errors[:5]:
            print('    parse error: %s' % e)

    check('13 map entries parsed',
          len(maps) == 13)

    # -----------------------------------------------------------------------
    # Required fields (all maps)
    # -----------------------------------------------------------------------
    section('Required fields (all maps)')

    check('all maps have population > 0',
          all(m['population'] > 0 for m in maps.values()))

    check('all maps have at least one spawn zone',
          all(len(m['zones']) > 0 for m in maps.values()))

    check('all maps have at least one spawn point',
          all(len(m['points']) > 0 for m in maps.values()))

    check('all maps have at least one archetype',
          all(len(m['archetypes']) > 0 for m in maps.values()))

    # -----------------------------------------------------------------------
    # Zone coordinate validity
    #
    # The C++ code places NPCs at:
    #   x = sx + rand % (ex - sx)   → valid tile range [sx, ex-1]
    #   y = sy + rand % (ey - sy)   → valid tile range [sy, ey-1]
    # so ex and ey are exclusive upper bounds; ex=50 / ey=50 is legal.
    # -----------------------------------------------------------------------
    section('Zone coordinate validity')

    all_zones = [(path, z) for path, m in maps.items() for z in m['zones']]

    check('all zones have sx < ex (non-zero width)',
          all(z[0] < z[2] for _, z in all_zones))

    check('all zones have sy < ey (non-zero height)',
          all(z[1] < z[3] for _, z in all_zones))

    check('all zone sx and sy are >= 0',
          all(z[0] >= 0 and z[1] >= 0 for _, z in all_zones))

    check('all zone ex and ey are >= 0',
          all(z[2] >= 0 and z[3] >= 0 for _, z in all_zones))

    check('all zone ex values are <= %d (map width)' % MAP_SIZE,
          all(z[2] <= MAP_SIZE for _, z in all_zones))

    check('all zone ey values are <= %d (map height)' % MAP_SIZE,
          all(z[3] <= MAP_SIZE for _, z in all_zones))

    # -----------------------------------------------------------------------
    # Spawn point validity
    # -----------------------------------------------------------------------
    section('Spawn point validity')

    all_points = [(path, p) for path, m in maps.items() for p in m['points']]

    check('all spawn points have x >= 0',
          all(p[0] >= 0 for _, p in all_points))

    check('all spawn points have y >= 0',
          all(p[1] >= 0 for _, p in all_points))

    check('all spawn points have x < %d' % MAP_SIZE,
          all(p[0] < MAP_SIZE for _, p in all_points))

    check('all spawn points have y < %d' % MAP_SIZE,
          all(p[1] < MAP_SIZE for _, p in all_points))

    # -----------------------------------------------------------------------
    # Archetype name validity
    # -----------------------------------------------------------------------
    section('Archetype name validity')

    all_archs = [a for m in maps.values() for a in m['archetypes']]

    check('all archetype names are non-empty strings',
          all(len(a) > 0 for a in all_archs))

    check('all archetype names contain no whitespace',
          all(not any(c.isspace() for c in a) for a in all_archs))

    # -----------------------------------------------------------------------
    # Map path format
    # -----------------------------------------------------------------------
    section('Map path format')

    _path_re = re.compile(r'^/world/world_\d+_\d+$')

    check('all map paths begin with /world/',
          all(p.startswith('/world/') for p in maps))

    check('all map paths match /world/world_NNN_NNN pattern',
          all(_path_re.match(p) for p in maps))

    # -----------------------------------------------------------------------
    # Scorn city coverage (4 world-map tiles)
    # -----------------------------------------------------------------------
    section('Scorn city coverage')

    SCORN_MAPS = [
        '/world/world_104_115',
        '/world/world_105_115',
        '/world/world_104_116',
        '/world/world_105_116',
    ]
    for mp in SCORN_MAPS:
        check('%s present' % mp, mp in maps)

    scorn_archs = set(a for mp in SCORN_MAPS if mp in maps for a in maps[mp]['archetypes'])
    check('Scorn maps include c_man archetype',   'c_man'   in scorn_archs)
    check('Scorn maps include c_woman archetype', 'c_woman' in scorn_archs)
    check('Scorn maps include guard archetype',   'guard'   in scorn_archs)
    check('Scorn maps include child archetype',   'child'   in scorn_archs)

    # -----------------------------------------------------------------------
    # Navar city coverage (4 world-map tiles)
    # -----------------------------------------------------------------------
    section('Navar city coverage')

    NAVAR_MAPS = [
        '/world/world_121_116',
        '/world/world_122_116',
        '/world/world_121_117',
        '/world/world_122_117',
    ]
    for mp in NAVAR_MAPS:
        check('%s present' % mp, mp in maps)

    navar_archs = set(a for mp in NAVAR_MAPS if mp in maps for a in maps[mp]['archetypes'])
    check('Navar maps include elf_man archetype',  'elf_man'  in navar_archs)
    check('Navar maps include courier archetype',  'courier'  in navar_archs)
    check('Navar maps include halfling archetype', 'halfling' in navar_archs)
    check('Navar maps include sailor archetype',   'sailor'   in navar_archs)

    # -----------------------------------------------------------------------
    # Scorn County fall-through (world_105_116)
    #
    # The world.citylife file intentionally shares the world_105_116 entry
    # between the Scorn city block and the Scorn County block.  The county
    # block overrides population (5 → 8) and appends 4 more zones and 8
    # more spawn points without opening a new 'map' stanza.
    # -----------------------------------------------------------------------
    section('Scorn County fall-through (world_105_116)')

    w = maps.get('/world/world_105_116', {})

    check('world_105_116 population overridden to 8 by Scorn County block',
          w.get('population') == 8)

    check('world_105_116 has 5 zones (1 city + 4 county)',
          len(w.get('zones', [])) == 5)

    check('world_105_116 has 12 spawn points (4 city + 8 county)',
          len(w.get('points', [])) == 12)

    check('world_105_116 includes both town arch (c_man) and rural arch (farmer)',
          'c_man' in w.get('archetypes', []) and 'farmer' in w.get('archetypes', []))

    # -----------------------------------------------------------------------
    # Other notable cities
    # -----------------------------------------------------------------------
    section('Other city coverage')

    check('Darcap (/world/world_116_102) present',
          '/world/world_116_102' in maps)
    check('Darcap has 3 zones',
          len(maps.get('/world/world_116_102', {}).get('zones', [])) == 3)
    check('Darcap has 19 spawn points',
          len(maps.get('/world/world_116_102', {}).get('points', [])) == 19)

    check('Port Joseph (/world/world_101_114) present',
          '/world/world_101_114' in maps)
    check('Port Joseph includes pirate archetype',
          'pirate' in maps.get('/world/world_101_114', {}).get('archetypes', []))
    check('Port Joseph includes sailor archetype',
          'sailor' in maps.get('/world/world_101_114', {}).get('archetypes', []))

    check('Stoneville (/world/world_103_127) present',
          '/world/world_103_127' in maps)

    check('Wolfsburg (/world/world_128_109) present',
          '/world/world_128_109' in maps)
    check('Wolfsburg includes merchant archetype',
          'merchant' in maps.get('/world/world_128_109', {}).get('archetypes', []))

    check('Santo Dominion (/world/world_102_108) present',
          '/world/world_102_108' in maps)
    check('Santo Dominion includes merchant archetype',
          'merchant' in maps.get('/world/world_102_108', {}).get('archetypes', []))

except Exception as exc:
    print('\nFATAL: unhandled exception -- %s' % exc)
    traceback.print_exc()
    _failed += 1

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = _passed + _failed
print('\n%s' % ('=' * 50))
print('Results: %d passed, %d failed out of %d' % (_passed, _failed, total))
if _failures:
    print('Failed:')
    for desc in _failures:
        print('  - %s' % desc)
sys.exit(0 if _failed == 0 else 1)
