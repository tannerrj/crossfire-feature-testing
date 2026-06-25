# Crossfire Feature Test Suite

Standalone integration tests for the Python feature subsystems used by the
Crossfire game server's map scripts. No running Crossfire server is required.

## Running Tests

```
python3 tests/test_feature_systems.py
```

Exit 0 = all passed. Exit 1 = failures; summary printed at end.

## Project Layout

```
lib/                    Crossfire Python modules under test (from crossfire-maps)
  CFBank.py             Banking system (SQLite via CFSqlDb)
  CFBoard.py            Message board system (shelve)
  CFDataFile.py         Flat-file storage -- patched, see bug note below
  CFGuilds.py           Guild system (CFDataFile)
  CFLog.py              Player login / citylife log (CFDataFile)
  CFMail.py             Postal system (SQLite via CFSqlDb)
  CFSqlDb.py            SQLite connection helper
fixtures/
  world.citylife        NPC spawn configuration (from crossfire-maps)
  world.bells           City bell region configuration (from crossfire-maps)
tests/
  test_feature_systems.py   Python subsystem tests -- 100 checks
  test_citylife_config.py   NPC spawn config tests -- 60 checks
  test_bells_config.py      City bell config tests -- 38 checks
.github/workflows/
  ci.yml                GitHub Actions: Python 3.8 through 3.12
sample-test-output.md   Captured test run showing expected pass/fail results
```

## How the Mock Works

The lib/ modules import `Crossfire`, a C extension only available inside a
live server process. The test file installs a Python mock into `sys.modules`
before any lib/ import. The mock supplies:

- `LocalDirectory()` -- returns a `tempfile.mkdtemp()` path; all file I/O
  goes there and is deleted after the run
- `Log()` -- suppressed (no-op)
- `FindPlayer()` -- returns None (safe early-exit path in CFBank)
- `DataDirectory()`, `MapDirectory()` -- return empty string

CFDataFile and CFBoard evaluate `Crossfire.LocalDirectory()` at class
definition time, so the mock and tmpdir must be in place before those
modules are imported. Import order in the test file is intentional.

## Known Bug Fix in lib/CFDataFile.py

The upstream `putData` method called `del dic['#']` which mutated the
shared `CFData.datadb` dict in-place, causing `KeyError: '#'` on any second
write through the same instance. Fixed by replacing:

```python
del dic['#']
index = list(dic.keys())
index.sort()
```

with:

```python
index = sorted(k for k in dic if k != '#')
```

A patch has been submitted to the Crossfire project. See
`patches/cfdatafile-putdata-fix.patch` (unified diff, patch -p1) and
`patches/cfdatafile-putdata-writeup.txt` (Sourceforge bug report) in this
repository.

## Upstream Source

lib/ modules originate from the crossfire-maps repository:
https://sourceforge.net/p/crossfire/code/HEAD/tree/maps/trunk/python/

## License

GNU General Public License version 2 or later. See LICENSE.
