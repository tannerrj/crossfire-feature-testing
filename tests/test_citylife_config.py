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

# Paths to sibling Crossfire repositories used by the source-level checks.
# Expected layout:  <parent>/crossfire-crossfire-arch/
#                   <parent>/crossfire-crossfire-server/
#                   <parent>/crossfire-feature-testing/   ← this project
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cf_root      = os.path.dirname(_project_root)
ARCH_DIR      = os.path.join(_cf_root, 'crossfire-crossfire-arch')
SERVER_DIR    = os.path.join(_cf_root, 'crossfire-crossfire-server')
INIT_CPP      = os.path.join(SERVER_DIR, 'server', 'init.cpp')
CITYLIFE_CPP  = os.path.join(SERVER_DIR, 'server', 'modules', 'citylife.cpp')

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

    # -----------------------------------------------------------------------
    # Archetype cross-reference (Bug 2 prevention)
    #
    # get_npc() calls try_find_archetype() and return NULL when a name is not
    # in the server's loaded arch set.  add_npc_to_point() dereferences that
    # NULL without a guard -- a crash.  Verify every arch name in
    # world.citylife exists in the crossfire-arch library so that get_npc()
    # will never return NULL for this config.
    # -----------------------------------------------------------------------
    section('Archetype cross-reference (Bug 2: crash on unknown archetype)')

    if not os.path.isdir(ARCH_DIR):
        print('  SKIP  arch library not found at %s' % ARCH_DIR)
    else:
        known_archs = set()
        for dirpath, _dirs, files in os.walk(ARCH_DIR):
            for fname in files:
                if fname.endswith('.arc'):
                    with open(os.path.join(dirpath, fname), 'r', errors='replace') as fh:
                        for line in fh:
                            if line.startswith('Object '):
                                known_archs.add(line[7:].strip())

        check('arch library loaded (%d archetypes found)' % len(known_archs),
              len(known_archs) > 0)

        citylife_archs = sorted(set(a for m in maps.values() for a in m['archetypes']))
        missing = [a for a in citylife_archs if a not in known_archs]

        check('all %d unique archetypes in world.citylife exist in the arch library'
              % len(citylife_archs),
              len(missing) == 0)
        for a in missing:
            print('    unknown archetype: %s' % a)

    # -----------------------------------------------------------------------
    # Server init order (Bug 1: init_modules must precede init_library)
    #
    # citylife_init() registers the .citylife asset collector hook.
    # assets_add_collector_hook() must be called before load_assets() runs
    # (inside init_library()), otherwise the hook fires too late and no zone
    # data is ever parsed -- citylife silently becomes a no-op.
    # -----------------------------------------------------------------------
    section('Server init order (Bug 1: init_modules before init_library)')

    if not os.path.isfile(INIT_CPP):
        print('  SKIP  server/init.cpp not found at %s' % INIT_CPP)
    else:
        with open(INIT_CPP) as fh:
            init_lines = fh.readlines()

        # Match indented function calls only -- skips definitions and declarations.
        _call_re  = lambda name: re.compile(r'^\s+' + re.escape(name) + r'\s*\([^)]*\)\s*;')
        _modules_re = _call_re('init_modules')
        _library_re = _call_re('init_library')

        modules_lines = [i + 1 for i, l in enumerate(init_lines) if _modules_re.match(l)]
        library_lines = [i + 1 for i, l in enumerate(init_lines) if _library_re.match(l)]

        check('init_modules() call found in server/init.cpp',
              len(modules_lines) > 0)
        check('init_library() call found in server/init.cpp',
              len(library_lines) > 0)

        if modules_lines and library_lines:
            ml = modules_lines[0]
            ll = library_lines[0]
            check('init_modules() (line %d) is called before init_library() (line %d) '
                  '-- if reversed, citylife hook is registered too late and no NPCs spawn'
                  % (ml, ll),
                  ml < ll)

    # -----------------------------------------------------------------------
    # Null guard in add_npc_to_point (Bug 2: latent crash)
    #
    # add_npc_to_zone() correctly checks get_npc() for NULL before use.
    # add_npc_to_point() does not, so a NULL return (bad archetype name)
    # causes a crash on every ~40th EVENT_CLOCK tick once citylife is active.
    # -----------------------------------------------------------------------
    section('Null guard in add_npc_to_point (Bug 2: latent null dereference)')

    if not os.path.isfile(CITYLIFE_CPP):
        print('  SKIP  server/modules/citylife.cpp not found at %s' % CITYLIFE_CPP)
    else:
        with open(CITYLIFE_CPP) as fh:
            cpp_lines = fh.readlines()

        # Extract the body of add_npc_to_point by scanning from its opening
        # brace to the matching closing brace.
        body_lines = []
        depth      = 0
        in_func    = False
        func_sig_re = re.compile(r'\badd_npc_to_point\b[^;]*\{')

        for line in cpp_lines:
            if not in_func:
                if func_sig_re.search(line):
                    in_func = True
                    depth = line.count('{') - line.count('}')
                    body_lines.append(line)
            else:
                body_lines.append(line)
                depth += line.count('{') - line.count('}')
                if depth == 0:
                    break

        check('add_npc_to_point function body located in citylife.cpp',
              len(body_lines) > 0)

        if body_lines:
            body = ''.join(body_lines)
            has_get_npc   = 'get_npc(' in body
            has_null_guard = bool(re.search(r'if\s*\(\s*!\s*npc\s*\)', body) or
                                  re.search(r'if\s*\(\s*npc\s*==\s*(NULL|nullptr)\s*\)', body))

            check('add_npc_to_point calls get_npc()',
                  has_get_npc)
            check('add_npc_to_point has null guard after get_npc() '
                  '-- missing guard crashes server when archetype is invalid',
                  has_null_guard)

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
