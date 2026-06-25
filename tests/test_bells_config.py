#!/usr/bin/env python3
"""
test_bells_config.py -- Validate the world.bells city bell configuration.

Parses fixtures/world.bells using the same logic as the C++ cfcitybell server
module (server/modules/cfcitybell.cpp: load_bells()) and checks that every
region entry is internally consistent, covers all expected gods, and uses
valid god archetype names.

Also checks two confirmed server bugs against the server source:

  Bug A -- cfcitybell_close() calls all_regions.clear() instead of
           regions.clear(), wiping the server's entire region list on module
           shutdown.  Expected result: FAIL (unfixed upstream).

  Bug B -- The .bells collector hook is registered in cfcitybell_init(),
           which is called from init_modules(), which runs after
           init_library() (and therefore after load_assets()).  No .bells
           files are ever loaded.  Expected result: FAIL (unfixed upstream).

No running Crossfire server is required.

Usage (from the project root directory):
    python3 tests/test_bells_config.py

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
# Parser (mirrors load_bells() in server/modules/cfcitybell.cpp)
#
# Format:
#   Lines beginning with '#' or empty lines are ignored.
#   'region <name>'          starts a new region block.
#   'god1[,god2,...] <msg>'  maps one or more god names to a bell message.
#   '* <msg>'                sets the fallback message for the current region.
#
# A god-list line before any 'region' line is a parse error.
# ---------------------------------------------------------------------------

def parse_bells(path):
    """
    Parse a .bells file.

    Returns:
        regions -- dict mapping region_name (str) to:
                   { 'gods':     {god_name: message, ...},
                     'fallback': str or None }
        errors  -- list of parse-error strings (empty if clean)
    """
    regions = {}
    current = None
    errors  = []

    with open(path, 'r') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip('\r\n')
            if not line or line[0] == '#':
                continue

            sp = line.find(' ')
            if sp == -1:
                errors.append('line %d: no space separator: %r' % (lineno, line))
                continue

            keyword = line[:sp]
            value   = line[sp + 1:]

            if keyword == 'region':
                name    = value.strip()
                current = {'gods': {}, 'fallback': None}
                regions[name] = current
                continue

            if current is None:
                errors.append('line %d: entry before any region line: %r' % (lineno, line))
                continue

            for god in keyword.split(','):
                god = god.strip()
                if god == '*':
                    current['fallback'] = value
                else:
                    current['gods'][god] = value

    return regions, errors

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cf_root      = os.path.dirname(_project_root)

FIXTURES_DIR  = os.path.join(_project_root, 'fixtures')
BELLS_FILE    = os.path.join(FIXTURES_DIR, 'world.bells')
ARCH_DIR      = os.path.join(_cf_root, 'crossfire-crossfire-arch')
SERVER_DIR    = os.path.join(_cf_root, 'crossfire-crossfire-server')
CITYBELL_CPP  = os.path.join(SERVER_DIR, 'server', 'modules', 'cfcitybell.cpp')
INIT_CPP      = os.path.join(SERVER_DIR, 'server', 'init.cpp')

try:
    # -----------------------------------------------------------------------
    # File and parser
    # -----------------------------------------------------------------------
    section('File and parser')

    check('fixtures/world.bells exists',
          os.path.isfile(BELLS_FILE))

    regions, errors = parse_bells(BELLS_FILE)

    check('file parses without errors',
          len(errors) == 0)
    if errors:
        for e in errors[:5]:
            print('    parse error: %s' % e)

    check('3 regions parsed (scorn, darcap, navar)',
          len(regions) == 3)

    # -----------------------------------------------------------------------
    # Required fields (all regions)
    # -----------------------------------------------------------------------
    section('Required fields (all regions)')

    check('all regions have at least one god-specific entry',
          all(len(r['gods']) > 0 for r in regions.values()))

    check('all regions have a fallback (*) entry',
          all(r['fallback'] is not None for r in regions.values()))

    check('all god-specific messages are non-empty',
          all(len(msg) > 0
              for r in regions.values()
              for msg in r['gods'].values()))

    check('all fallback messages are non-empty',
          all(len(r['fallback']) > 0
              for r in regions.values()
              if r['fallback'] is not None))

    # -----------------------------------------------------------------------
    # Message format
    # -----------------------------------------------------------------------
    section('Message format')

    all_god_names = [god
                     for r in regions.values()
                     for god in r['gods']]

    check('all god names are non-empty and contain no whitespace',
          all(len(g) > 0 and not any(c.isspace() for c in g)
              for g in all_god_names))

    all_messages = ([msg for r in regions.values() for msg in r['gods'].values()] +
                    [r['fallback'] for r in regions.values() if r['fallback']])
    _unknown_pct = re.compile(r'%(?!god)')
    check('no unrecognized % sequences in messages (only %god is valid)',
          not any(_unknown_pct.search(m) for m in all_messages))

    # -----------------------------------------------------------------------
    # Scorn region
    # -----------------------------------------------------------------------
    section('Scorn region coverage')

    scorn = regions.get('scorn', {})

    check('scorn region defined',
          'scorn' in regions)

    SCORN_GODS = ['Devourers', 'Sorig', 'Ruggilli', 'Gaea', 'Mostrai',
                  'Lythander', 'Valriel', 'Gorokh']
    for god in SCORN_GODS:
        check('scorn has entry for %s' % god,
              god in scorn.get('gods', {}))

    check('scorn has fallback message',
          scorn.get('fallback') is not None)

    # -----------------------------------------------------------------------
    # Darcap region
    # -----------------------------------------------------------------------
    section('Darcap region coverage')

    darcap = regions.get('darcap', {})

    check('darcap region defined',
          'darcap' in regions)

    DARCAP_GODS = ['Devourers', 'Valkyrie']
    for god in DARCAP_GODS:
        check('darcap has entry for %s' % god,
              god in darcap.get('gods', {}))

    check('darcap has fallback message',
          darcap.get('fallback') is not None)

    # -----------------------------------------------------------------------
    # Navar region
    # -----------------------------------------------------------------------
    section('Navar region coverage')

    navar = regions.get('navar', {})

    check('navar region defined',
          'navar' in regions)

    NAVAR_GODS = ['Gorokh', 'Ruggilli', 'Sorig', 'Valkyrie', 'Valriel',
                  'Mostrai', 'Gaea']
    for god in NAVAR_GODS:
        check('navar has entry for %s' % god,
              god in navar.get('gods', {}))

    check('navar has fallback message',
          navar.get('fallback') is not None)

    # -----------------------------------------------------------------------
    # God archetype cross-reference
    #
    # determine_god() looks up the god's archetype by name.  If a god name
    # in world.bells does not match any type-50 (GOD) archetype Object name,
    # the bell message for that god is silently unreachable.
    # -----------------------------------------------------------------------
    section('God archetype cross-reference')

    if not os.path.isdir(ARCH_DIR):
        print('  SKIP  arch library not found at %s' % ARCH_DIR)
    else:
        god_archs = set()
        for dirpath, _dirs, files in os.walk(ARCH_DIR):
            for fname in files:
                if not fname.endswith('.arc'):
                    continue
                arc_path = os.path.join(dirpath, fname)
                current_obj  = None
                current_type = None
                with open(arc_path, 'r', errors='replace') as fh:
                    for line in fh:
                        line = line.rstrip()
                        if line.startswith('Object '):
                            current_obj  = line[7:].strip()
                            current_type = None
                        elif line.startswith('type '):
                            current_type = line[5:].strip()
                            if current_type == '50' and current_obj:
                                god_archs.add(current_obj)
                        elif line == 'end':
                            current_obj  = None
                            current_type = None

        check('arch library loaded (%d god archetypes found)' % len(god_archs),
              len(god_archs) > 0)

        bells_gods = sorted(set(all_god_names))
        missing = [g for g in bells_gods if g not in god_archs]

        check('all %d god names in world.bells match a type-50 archetype'
              % len(bells_gods),
              len(missing) == 0)
        for g in missing:
            print('    no type-50 archetype: %s' % g)

    # -----------------------------------------------------------------------
    # Bug A: cfcitybell_close() wipes server region list (server bug)
    #
    # cfcitybell_close() iterates over the module's `regions` map and deletes
    # each Region object, then calls all_regions.clear().  The module's map
    # is named `regions`; all_regions is the server-wide region list used by
    # every part of the game.  Calling all_regions.clear() on module close
    # destroys all game region data.  The correct call is regions.clear().
    #
    # Expected result: FAIL (unfixed in upstream server source).
    # -----------------------------------------------------------------------
    section('Bug A: cfcitybell_close() clears wrong container (server bug)')

    if not os.path.isfile(CITYBELL_CPP):
        print('  SKIP  server/modules/cfcitybell.cpp not found at %s' % CITYBELL_CPP)
    else:
        with open(CITYBELL_CPP) as fh:
            cpp_lines = fh.readlines()

        body_lines = []
        depth      = 0
        in_func    = False
        func_re    = re.compile(r'\bcfcitybell_close\b[^;]*\{')

        for line in cpp_lines:
            if not in_func:
                if func_re.search(line):
                    in_func = True
                    depth   = line.count('{') - line.count('}')
                    body_lines.append(line)
            else:
                body_lines.append(line)
                depth += line.count('{') - line.count('}')
                if depth == 0:
                    break

        check('cfcitybell_close() function body found in cfcitybell.cpp',
              len(body_lines) > 0)

        if body_lines:
            body = ''.join(body_lines)
            check('cfcitybell_close() calls regions.clear() not all_regions.clear() '
                  '-- calling all_regions.clear() destroys all server region data',
                  'regions.clear()' in body and 'all_regions.clear()' not in body)

    # -----------------------------------------------------------------------
    # Bug B: .bells hook registered after load_assets() (server bug)
    #
    # cfcitybell_init() calls assets_add_collector_hook(".bells", load_bells).
    # cfcitybell_init() is called from init_modules(), which runs after
    # init_library() (and therefore after load_assets()).  The hook fires too
    # late and no .bells files are ever loaded, so no bell messages are
    # configured and no bells ever ring.
    #
    # The fix is to register the .bells hook in add_server_collect_hooks()
    # (in server/init.cpp), alongside /materials and /races, before
    # init_library() is called.
    #
    # Expected result: FAIL (unfixed in upstream server source).
    # -----------------------------------------------------------------------
    section('Bug B: .bells hook registered after load_assets() (server bug)')

    if not os.path.isfile(INIT_CPP):
        print('  SKIP  server/init.cpp not found at %s' % INIT_CPP)
    else:
        with open(INIT_CPP) as fh:
            init_lines = fh.readlines()

        hook_body  = []
        depth      = 0
        in_func    = False
        hook_re    = re.compile(r'\badd_server_collect_hooks\b[^;]*\{')

        for line in init_lines:
            if not in_func:
                if hook_re.search(line):
                    in_func = True
                    depth   = line.count('{') - line.count('}')
                    hook_body.append(line)
            else:
                hook_body.append(line)
                depth += line.count('{') - line.count('}')
                if depth == 0:
                    break

        check('add_server_collect_hooks() body found in server/init.cpp',
              len(hook_body) > 0)

        if hook_body:
            body = ''.join(hook_body)
            check('.bells hook registered in add_server_collect_hooks() before '
                  'init_library() -- if absent, no .bells files are ever loaded',
                  '".bells"' in body or "'.bells'" in body or '.bells' in body)

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
