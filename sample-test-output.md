# Sample Test Output

Output from running both test suites against the Crossfire feature testing
project. Captured 2026-06-24 on Python 3.13.

The two `FAIL` results at the end of `test_citylife_config.py` are
**intentional** — they confirm two known bugs in the current Crossfire server
codebase (see commit message for `f3d0a46` for details). They are not errors
in the test suite.

---

```
$ python3 tests/test_feature_systems.py

--- Banking System (CFBank) ---
  PASS  new account starts at zero balance
  PASS  deposit 1000 silver records correctly
  PASS  second deposit accumulates to 1500
  PASS  withdraw 400 succeeds
  PASS  balance after withdrawal is 1100
  PASS  overdraft withdrawal fails (returns 0)
  PASS  balance unchanged after failed overdraft
  PASS  second player has independent account
  PASS  Alice balance unaffected by Bob deposit
  PASS  removed account reports zero balance
  PASS  deposit of zero is a no-op

--- Postal System (CFMail) ---
  PASS  mailbox starts empty
  PASS  one mailscroll queued for Alice
  PASS  second letter increments count to 2
  PASS  Bob has one newsletter waiting
  PASS  receive returns both messages
  PASS  first message is mailscroll type 1
  PASS  first message sender is Bob
  PASS  first message body contains greeting
  PASS  second message sender is Carol
  PASS  Alice mailbox is empty after receive
  PASS  Bob receives newsletter type 2
  PASS  Bob mailbox empty after receive
  PASS  receiving from empty mailbox returns empty list

--- Message Boards (CFBoard) ---
  PASS  new board starts with no posts
  PASS  three posts on board after writes
  PASS  post 1 author is Alice
  PASS  post 2 author is Bob
  PASS  post 2 body matches
  PASS  post 3 body matches
  PASS  getauthor returns Bob for post 2
  PASS  deleting post 2 returns 1
  PASS  two posts remain after deletion
  PASS  remaining posts are both by Alice
  PASS  deleting nonexistent post returns 0
  PASS  different board name starts empty
  PASS  second board has its own entry
  PASS  original board unaffected by second board write

--- Citylife / Player Log (CFLog) ---
  PASS  unknown player has no log record
  PASS  created player has a record
  PASS  initial login count is 0
  PASS  initial kick count is 0
  PASS  initial muzzle count is 0
  PASS  last kick date starts as never
  PASS  login count incremented to 1
  PASS  IP address recorded
  PASS  login count accumulated to 3
  PASS  IP updated to most recent address
  PASS  kick count incremented to 1
  PASS  kick date recorded (no longer never)
  PASS  muzzle count accumulated to 2
  PASS  second player record created independently
  PASS  Alice record intact after Bob creation
  PASS  removed player has no record
  PASS  Alice record intact after Bob removal
  PASS  last_login parses stored timestamp

--- Guild System (CFGuilds) ---
  PASS  unknown guild has no record
  PASS  add_guild returns 1
  PASS  new guild record exists
  PASS  new guild status is inactive
  PASS  new guild points are 0
  PASS  new guild quest points are 0
  PASS  establish returns 1
  PASS  established guild status is active
  PASS  founded date is set
  PASS  guild points updated to 300
  PASS  guild quest points updated to 50
  PASS  guild status changed to suspended
  PASS  invalid status string rejected (returns 0)
  PASS  fresh guild has no members
  PASS  add_member returns 1
  PASS  member count is 1
  PASS  two members listed
  PASS  Alice appears in member list
  PASS  Bob appears in member list
  PASS  member info returned for Alice
  PASS  Alice initial rank is Initiate
  PASS  Alice initial status is good
  PASS  Alice initial demerits are 0
  PASS  promote returns 1
  PASS  Alice rank is now Novice
  PASS  Alice promoted all the way to GuildMaster
  PASS  cannot promote past GuildMaster (returns 0)
  PASS  demote Novice Bob returns 1
  PASS  Bob rank is now Initiate
  PASS  cannot demote below Initiate (returns 0)
  PASS  Bob has 7 demerits
  PASS  Bob has 3 demerits after removal
  PASS  demerits capped at 100
  PASS  Bob status changed to suspended
  PASS  invalid member status rejected (returns 0)
  PASS  member quest points recorded
  PASS  Bob dues recorded
  PASS  guild points increased by dues amount (300 + 150 = 450)
  PASS  remove_member returns 1
  PASS  member count after Alice removal is 1
  PASS  Alice info is gone
  PASS  Bob record unaffected by Alice removal
  PASS  SearchGuilds finds Bob in Mages guild
  PASS  SearchGuilds returns 0 for non-member

==================================================
Results: 100 passed, 0 failed out of 100

$ python3 tests/test_citylife_config.py

--- File and parser ---
  PASS  fixtures/world.citylife exists
  PASS  file parses without errors
  PASS  13 map entries parsed

--- Required fields (all maps) ---
  PASS  all maps have population > 0
  PASS  all maps have at least one spawn zone
  PASS  all maps have at least one spawn point
  PASS  all maps have at least one archetype

--- Zone coordinate validity ---
  PASS  all zones have sx < ex (non-zero width)
  PASS  all zones have sy < ey (non-zero height)
  PASS  all zone sx and sy are >= 0
  PASS  all zone ex and ey are >= 0
  PASS  all zone ex values are <= 50 (map width)
  PASS  all zone ey values are <= 50 (map height)

--- Spawn point validity ---
  PASS  all spawn points have x >= 0
  PASS  all spawn points have y >= 0
  PASS  all spawn points have x < 50
  PASS  all spawn points have y < 50

--- Archetype name validity ---
  PASS  all archetype names are non-empty strings
  PASS  all archetype names contain no whitespace

--- Map path format ---
  PASS  all map paths begin with /world/
  PASS  all map paths match /world/world_NNN_NNN pattern

--- Scorn city coverage ---
  PASS  /world/world_104_115 present
  PASS  /world/world_105_115 present
  PASS  /world/world_104_116 present
  PASS  /world/world_105_116 present
  PASS  Scorn maps include c_man archetype
  PASS  Scorn maps include c_woman archetype
  PASS  Scorn maps include guard archetype
  PASS  Scorn maps include child archetype

--- Navar city coverage ---
  PASS  /world/world_121_116 present
  PASS  /world/world_122_116 present
  PASS  /world/world_121_117 present
  PASS  /world/world_122_117 present
  PASS  Navar maps include elf_man archetype
  PASS  Navar maps include courier archetype
  PASS  Navar maps include halfling archetype
  PASS  Navar maps include sailor archetype

--- Scorn County fall-through (world_105_116) ---
  PASS  world_105_116 population overridden to 8 by Scorn County block
  PASS  world_105_116 has 5 zones (1 city + 4 county)
  PASS  world_105_116 has 12 spawn points (4 city + 8 county)
  PASS  world_105_116 includes both town arch (c_man) and rural arch (farmer)

--- Other city coverage ---
  PASS  Darcap (/world/world_116_102) present
  PASS  Darcap has 3 zones
  PASS  Darcap has 19 spawn points
  PASS  Port Joseph (/world/world_101_114) present
  PASS  Port Joseph includes pirate archetype
  PASS  Port Joseph includes sailor archetype
  PASS  Stoneville (/world/world_103_127) present
  PASS  Wolfsburg (/world/world_128_109) present
  PASS  Wolfsburg includes merchant archetype
  PASS  Santo Dominion (/world/world_102_108) present
  PASS  Santo Dominion includes merchant archetype

--- Archetype cross-reference (Bug 2: crash on unknown archetype) ---
  PASS  arch library loaded (5448 archetypes found)
  PASS  all 22 unique archetypes in world.citylife exist in the arch library

--- Server init order (Bug 1: init_modules before init_library) ---
  PASS  init_modules() call found in server/init.cpp
  PASS  init_library() call found in server/init.cpp
  FAIL  init_modules() (line 1147) is called before init_library() (line 1128) -- if reversed, citylife hook is registered too late and no NPCs spawn

--- Null guard in add_npc_to_point (Bug 2: latent null dereference) ---
  PASS  add_npc_to_point function body located in citylife.cpp
  PASS  add_npc_to_point calls get_npc()
  FAIL  add_npc_to_point has null guard after get_npc() -- missing guard crashes server when archetype is invalid

==================================================
Results: 58 passed, 2 failed out of 60
Failed:
  - init_modules() (line 1147) is called before init_library() (line 1128) -- if reversed, citylife hook is registered too late and no NPCs spawn
  - add_npc_to_point has null guard after get_npc() -- missing guard crashes server when archetype is invalid
```
