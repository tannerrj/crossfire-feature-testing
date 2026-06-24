#!/usr/bin/env python3
"""
test_feature_systems.py -- Standalone integration tests for Crossfire feature subsystems.

Tests CFBank, CFMail, CFBoard, CFLog (citylife), and CFGuilds by importing
their Python modules directly with a lightweight mock of the Crossfire C
extension.  No running server is required.

Usage (from the project root directory):
    python3 tests/test_feature_systems.py

Exit code 0 = all tests passed, 1 = one or more failures.
"""

import sys
import os
import tempfile
import shutil
import traceback

# ---------------------------------------------------------------------------
# Mock of the Crossfire C extension module.
# Must be installed into sys.modules before any lib/ module is imported,
# because CFDataFile and CFBoard compute class-level paths at import time
# using Crossfire.LocalDirectory().
# ---------------------------------------------------------------------------

class _Crossfire:
    LogDebug   = 0
    LogInfo    = 1
    LogWarning = 2
    LogError   = 3
    _tmpdir    = None   # set by test harness before imports

    @classmethod
    def LocalDirectory(cls):
        return cls._tmpdir

    @staticmethod
    def Log(level, msg):
        pass   # suppress server log output during tests

    @staticmethod
    def FindPlayer(name):
        # CFBank.convert_legacy_balance calls this; returning None is the safe path
        return None

    @staticmethod
    def DataDirectory():
        return ''

    @staticmethod
    def MapDirectory():
        return ''

sys.modules['Crossfire'] = _Crossfire

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
# Setup: create a temp directory and point the mock at it, then import
# feature modules (order matters due to class-level LocalDirectory() calls).
# ---------------------------------------------------------------------------

tmpdir = tempfile.mkdtemp(prefix='cf_test_')
_Crossfire._tmpdir = tmpdir

LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.insert(0, LIB_DIR)

try:
    # CFDataFile must come first: CFBoard and CFLog depend on its class-level path
    import CFDataFile   # datafiledir = join(LocalDirectory(), 'datafiles') at class time
    import CFBoard      # boarddb_file = join(LocalDirectory(), ...) at class time
    import CFSqlDb      # open() calls LocalDirectory() at call time -- no class-level issue
    import CFLog
    import CFMail
    import CFBank
    import CFGuilds

    # -----------------------------------------------------------------------
    # Banking System
    # -----------------------------------------------------------------------
    section('Banking System (CFBank)')

    with CFBank.CFBank() as bank:
        bank.init_schema()

        check('new account starts at zero balance',
              bank.getbalance('Alice') == 0)

        bank.deposit('Alice', 1000)
        check('deposit 1000 silver records correctly',
              bank.getbalance('Alice') == 1000)

        bank.deposit('Alice', 500)
        check('second deposit accumulates to 1500',
              bank.getbalance('Alice') == 1500)

        result = bank.withdraw('Alice', 400)
        check('withdraw 400 succeeds',
              result == 1)
        check('balance after withdrawal is 1100',
              bank.getbalance('Alice') == 1100)

        result = bank.withdraw('Alice', 9999)
        check('overdraft withdrawal fails (returns 0)',
              result == 0)
        check('balance unchanged after failed overdraft',
              bank.getbalance('Alice') == 1100)

        bank.deposit('Bob', 200)
        check('second player has independent account',
              bank.getbalance('Bob') == 200)
        check('Alice balance unaffected by Bob deposit',
              bank.getbalance('Alice') == 1100)

        bank.remove_account('Bob')
        check('removed account reports zero balance',
              bank.getbalance('Bob') == 0)

        bank.deposit('Alice', 0)
        check('deposit of zero is a no-op',
              bank.getbalance('Alice') == 1100)

    # -----------------------------------------------------------------------
    # Postal System
    # -----------------------------------------------------------------------
    section('Postal System (CFMail)')

    with CFMail.CFMail() as mail:
        mail.init_schema()

        check('mailbox starts empty',
              mail.countmail('Alice') == 0)

        mail.send(1, 'Alice', 'Bob', 'Hello from Bob')
        check('one mailscroll queued for Alice',
              mail.countmail('Alice') == 1)

        mail.send(1, 'Alice', 'Carol', 'Letter from Carol')
        check('second letter increments count to 2',
              mail.countmail('Alice') == 2)

        mail.send(2, 'Bob', 'Server', 'Monthly newsletter')
        check('Bob has one newsletter waiting',
              mail.countmail('Bob') == 1)

        messages = mail.receive('Alice')
        check('receive returns both messages',
              len(messages) == 2)
        check('first message is mailscroll type 1',
              messages[0][0] == 1)
        check('first message sender is Bob',
              messages[0][1] == 'Bob')
        check('first message body contains greeting',
              'Hello from Bob' in messages[0][2])
        check('second message sender is Carol',
              messages[1][1] == 'Carol')

        check('Alice mailbox is empty after receive',
              mail.countmail('Alice') == 0)

        bob_msgs = mail.receive('Bob')
        check('Bob receives newsletter type 2',
              bob_msgs[0][0] == 2)
        check('Bob mailbox empty after receive',
              mail.countmail('Bob') == 0)

        check('receiving from empty mailbox returns empty list',
              mail.receive('Nobody') == [])

    # -----------------------------------------------------------------------
    # Message Boards
    # -----------------------------------------------------------------------
    section('Message Boards (CFBoard)')

    with CFBoard.CFBoard() as board:
        check('new board starts with no posts',
              board.list('town_hall') == [])

        board.write('town_hall', 'Alice', 'Seeking adventurers for dungeon run')
        board.write('town_hall', 'Bob',   'Dragon spotted near old mines')
        board.write('town_hall', 'Alice', 'Reward: 500 gold pieces')

        posts = board.list('town_hall')
        check('three posts on board after writes',
              len(posts) == 3)
        check('post 1 author is Alice',
              posts[0][0] == 'Alice')
        check('post 2 author is Bob',
              posts[1][0] == 'Bob')
        check('post 2 body matches',
              posts[1][1] == 'Dragon spotted near old mines')
        check('post 3 body matches',
              posts[2][1] == 'Reward: 500 gold pieces')

        check('getauthor returns Bob for post 2',
              board.getauthor('town_hall', 2) == 'Bob')

        result = board.delete('town_hall', 2)
        check('deleting post 2 returns 1',
              result == 1)
        posts = board.list('town_hall')
        check('two posts remain after deletion',
              len(posts) == 2)
        check('remaining posts are both by Alice',
              posts[0][0] == 'Alice' and posts[1][0] == 'Alice')

        result = board.delete('town_hall', 99)
        check('deleting nonexistent post returns 0',
              result == 0)

        check('different board name starts empty',
              board.list('scorn_inn') == [])
        board.write('scorn_inn', 'Innkeeper', 'Rooms available nightly')
        check('second board has its own entry',
              len(board.list('scorn_inn')) == 1)
        check('original board unaffected by second board write',
              len(board.list('town_hall')) == 2)

    # -----------------------------------------------------------------------
    # Citylife / Player Log
    # -----------------------------------------------------------------------
    section('Citylife / Player Log (CFLog)')

    log = CFLog.CFLog()

    check('unknown player has no log record',
          log.info('Stranger') == 0)

    log.create('Alice')
    record = log.info('Alice')
    check('created player has a record',
          record != 0)
    check('initial login count is 0',
          int(record['Login_Count']) == 0)
    check('initial kick count is 0',
          int(record['Kick_Count']) == 0)
    check('initial muzzle count is 0',
          int(record['Muzzle_Count']) == 0)
    check('last kick date starts as never',
          record['Last_Kick_Date'] == 'never')

    log.login_update('Alice', '192.168.1.10')
    record = log.info('Alice')
    check('login count incremented to 1',
          int(record['Login_Count']) == 1)
    check('IP address recorded',
          record['IP'] == '192.168.1.10')

    log.login_update('Alice', '10.0.0.5')
    log.login_update('Alice', '10.0.0.5')
    check('login count accumulated to 3',
          int(log.info('Alice')['Login_Count']) == 3)
    check('IP updated to most recent address',
          log.info('Alice')['IP'] == '10.0.0.5')

    log.kick_update('Alice')
    record = log.info('Alice')
    check('kick count incremented to 1',
          int(record['Kick_Count']) == 1)
    check('kick date recorded (no longer never)',
          record['Last_Kick_Date'] != 'never')

    log.muzzle_update('Alice')
    log.muzzle_update('Alice')
    check('muzzle count accumulated to 2',
          int(log.info('Alice')['Muzzle_Count']) == 2)

    log.create('Bob')
    check('second player record created independently',
          log.info('Bob') != 0)
    check('Alice record intact after Bob creation',
          int(log.info('Alice')['Login_Count']) == 3)

    log.remove('Bob')
    check('removed player has no record',
          log.info('Bob') == 0)
    check('Alice record intact after Bob removal',
          log.info('Alice') != 0)

    parsed = log.last_login('Alice')
    check('last_login parses stored timestamp',
          parsed is not None)

    # -----------------------------------------------------------------------
    # Guild System
    # -----------------------------------------------------------------------
    section('Guild System (CFGuilds)')

    # -- CFGuildHouses: inter-guild registry --
    CFGuildHouses = CFGuilds.CFGuildHouses()

    check('unknown guild has no record',
          CFGuildHouses.info('Mages') == 0)

    result = CFGuildHouses.add_guild('Mages')
    check('add_guild returns 1',
          result == 1)
    record = CFGuildHouses.info('Mages')
    check('new guild record exists',
          record != 0)
    check('new guild status is inactive',
          record['Status'] == 'inactive')
    check('new guild points are 0',
          int(record['Points']) == 0)
    check('new guild quest points are 0',
          int(record['Quest_points']) == 0)

    result = CFGuildHouses.establish('Mages')
    check('establish returns 1',
          result == 1)
    record = CFGuildHouses.info('Mages')
    check('established guild status is active',
          record['Status'] == 'active')
    check('founded date is set',
          record['Founded_Date'] != 'never')

    CFGuildHouses.update_points('Mages', 300)
    check('guild points updated to 300',
          int(CFGuildHouses.info('Mages')['Points']) == 300)

    CFGuildHouses.add_questpoints('Mages', 50)
    check('guild quest points updated to 50',
          int(CFGuildHouses.info('Mages')['Quest_points']) == 50)

    CFGuildHouses.change_status('Mages', 'suspended')
    check('guild status changed to suspended',
          CFGuildHouses.info('Mages')['Status'] == 'suspended')

    result = CFGuildHouses.change_status('Mages', 'bogus_status')
    check('invalid status string rejected (returns 0)',
          result == 0)

    CFGuildHouses.change_status('Mages', 'active')

    # -- CFGuild: individual guild member management --
    guild = CFGuilds.CFGuild('Mages')

    check('fresh guild has no members',
          guild.count_members() == 0)

    result = guild.add_member('Alice', 'Initiate')
    check('add_member returns 1',
          result == 1)
    check('member count is 1',
          guild.count_members() == 1)

    guild.add_member('Bob', 'Novice')
    members = guild.list_members()
    check('two members listed',
          len(members) == 2)
    check('Alice appears in member list',
          'Alice' in members)
    check('Bob appears in member list',
          'Bob' in members)

    record = guild.info('Alice')
    check('member info returned for Alice',
          record != 0)
    check('Alice initial rank is Initiate',
          record['Rank'] == 'Initiate')
    check('Alice initial status is good',
          record['Status'] == 'good')
    check('Alice initial demerits are 0',
          int(record['Demerits']) == 0)

    result = guild.promote_member('Alice')
    check('promote returns 1',
          result == 1)
    check('Alice rank is now Novice',
          guild.info('Alice')['Rank'] == 'Novice')

    guild.promote_member('Alice')   # -> Guildman
    guild.promote_member('Alice')   # -> Journeyman
    guild.promote_member('Alice')   # -> Master
    guild.promote_member('Alice')   # -> GuildMaster
    check('Alice promoted all the way to GuildMaster',
          guild.info('Alice')['Rank'] == 'GuildMaster')

    result = guild.promote_member('Alice')
    check('cannot promote past GuildMaster (returns 0)',
          result == 0)

    result = guild.demote_member('Bob')
    check('demote Novice Bob returns 1',
          result == 1)
    check('Bob rank is now Initiate',
          guild.info('Bob')['Rank'] == 'Initiate')

    result = guild.demote_member('Bob')
    check('cannot demote below Initiate (returns 0)',
          result == 0)

    guild.add_demerits('Bob', 7)
    check('Bob has 7 demerits',
          int(guild.info('Bob')['Demerits']) == 7)

    guild.remove_demerits('Bob', 4)
    check('Bob has 3 demerits after removal',
          int(guild.info('Bob')['Demerits']) == 3)

    guild.add_demerits('Bob', 200)
    check('demerits capped at 100',
          int(guild.info('Bob')['Demerits']) == 100)

    guild.change_status('Bob', 'suspended')
    check('Bob status changed to suspended',
          guild.info('Bob')['Status'] == 'suspended')

    result = guild.change_status('Bob', 'invalid')
    check('invalid member status rejected (returns 0)',
          result == 0)

    guild.add_questpoints('Bob', 5)
    check('member quest points recorded',
          int(guild.info('Bob')['Quest_points']) == 5)

    guild.pay_dues('Bob', 150)
    check('Bob dues recorded',
          int(guild.info('Bob')['Dues']) == 150)
    fresh_houses = CFGuilds.CFGuildHouses()
    check('guild points increased by dues amount (300 + 150 = 450)',
          int(fresh_houses.info('Mages')['Points']) == 450)

    result = guild.remove_member('Alice')
    check('remove_member returns 1',
          result == 1)
    check('member count after Alice removal is 1',
          guild.count_members() == 1)
    check('Alice info is gone',
          guild.info('Alice') == 0)
    check('Bob record unaffected by Alice removal',
          guild.info('Bob') != 0)

    result = CFGuilds.SearchGuilds('Bob')
    check('SearchGuilds finds Bob in Mages guild',
          result == 'Mages')
    result = CFGuilds.SearchGuilds('Nobody')
    check('SearchGuilds returns 0 for non-member',
          result == 0)

except Exception as exc:
    print('\nFATAL: unhandled exception -- %s' % exc)
    traceback.print_exc()
    _failed += 1

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

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
