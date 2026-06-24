# Crossfire Feature Test Suite

[![Tests](https://github.com/tannerrj/crossfire-feature-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/tannerrj/crossfire-feature-testing/actions/workflows/ci.yml)

Standalone integration tests for the Python feature subsystems used by the
[Crossfire](http://crossfire.real-time.com/) game server's map scripts.

No running Crossfire server is required. The test suite mocks the Crossfire
C extension module and exercises the real Python library code directly against
a temporary on-disk database, then cleans up after itself.

## What Is Tested

| System | Module / File | Coverage |
|---|---|---|
| Banking | `CFBank` | deposit, accumulation, withdrawal, overdraft rejection, multiple accounts, account removal |
| Postal | `CFMail` | send types 1/2/3, count, receive empties queue, message body, empty-mailbox receive |
| Message Boards | `CFBoard` | write, list, getauthor, delete by id, invalid delete, independent board namespaces |
| Citylife / Player Log | `CFLog` | create, login count, IP tracking, kick and muzzle counters and dates, remove, timestamp parse |
| Guild System | `CFGuilds` | guild registry (add, establish, points, quest points, status), member CRUD, full rank ladder, rank floor/ceiling, demerits cap, dues updating guild points, SearchGuilds |
| Citylife NPC config | `fixtures/world.citylife` | parse correctness, required fields, zone/point bounds, archetype names, Scorn and Navar coverage, Scorn County fall-through |

100 checks across the five Python subsystems; 52 checks for the citylife NPC configuration.

## Requirements

- Python 3.8 or later
- No external packages; only standard library modules are used (`sqlite3`, `shelve`, `tempfile`, etc.)

## Running the Tests

From the project root directory:

```
python3 tests/test_feature_systems.py
```

Exit code `0` means all tests passed. Exit code `1` means one or more checks
failed; the summary printed at the end lists every failure by description.

## Project Structure

```
crossfire-feature-testing/
├── lib/                    Source modules under test (from crossfire-maps)
│   ├── CFBank.py           Banking system
│   ├── CFBoard.py          Message board system
│   ├── CFDataFile.py       Flat-file data storage (patched, see below)
│   ├── CFGuilds.py         Guild system
│   ├── CFLog.py            Player login/citylife log
│   ├── CFMail.py           Postal system
│   └── CFSqlDb.py          SQLite database helper
├── fixtures/
│   └── world.citylife          NPC spawn config (from crossfire-maps)
├── patches/
│   └── cfdatafile-putdata-fix.patch    Upstream bug fix patch
├── tests/
│   ├── test_feature_systems.py         Python subsystem tests (100 checks)
│   └── test_citylife_config.py         NPC spawn config tests (52 checks)
├── .github/
│   └── workflows/
│       └── ci.yml          GitHub Actions: runs tests on Python 3.8 through 3.12
├── CLAUDE.md               Claude Code project context
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

## How It Works

The Crossfire Python map scripts import a C extension module called `Crossfire`
that is only available inside a running Crossfire server process. The test
suite installs a lightweight Python mock of that module into `sys.modules`
before importing any library module. The mock satisfies two needs:

1. **Directory paths** -- `CFDataFile` and `CFBoard` evaluate
   `Crossfire.LocalDirectory()` at class definition time to set storage paths.
   The mock returns a `tempfile.mkdtemp()` directory created just before the
   import, so all file I/O goes to a throw-away location that is deleted when
   the tests finish.

2. **Player lookups** -- `CFBank.convert_legacy_balance` calls
   `Crossfire.FindPlayer(name)`. The mock returns `None`, which causes that
   function to return early without error.

No other Crossfire server facilities are needed by the tested subsystems.

## Bug Fix Included: CFDataFile.putData

`lib/CFDataFile.py` includes a fix for a bug present in the upstream
crossfire-maps source. The original `putData` method did:

```python
header = dic['#']
del dic['#']          # mutates the caller's dict in-place
index = list(dic.keys())
index.sort()
```

The `del dic['#']` removes the header key from `CFData.datadb` permanently.
Any second write through the same `CFData` instance raises `KeyError: '#'`.

The fix avoids mutating the dict:

```python
header = dic['#']
index = sorted(k for k in dic if k != '#')
```

A patch for the upstream repository has been submitted to the Crossfire
project. See [`patches/cfdatafile-putdata-fix.patch`](patches/cfdatafile-putdata-fix.patch).

## Upstream Relationship

The `lib/` modules are taken from the
[crossfire-maps](https://sourceforge.net/p/crossfire/code/HEAD/tree/maps/trunk/python/)
repository. This test suite is independent of that repository and is intended
to be run against whichever version of those modules you have locally.

## License

The library modules in `lib/` are copyright their respective authors and are
distributed under the GNU General Public License version 2 or later, the same
license as the Crossfire project. See [LICENSE](LICENSE) for the full text.

The test code in `tests/` is also released under GPL v2+.
