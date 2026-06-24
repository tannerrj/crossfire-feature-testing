# CFBank.py - CFBank class
#
# Copyright (C) 2002 Joris Bontje
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# This module stores bank account information.

import Crossfire
import CFSqlDb as cfdb

class CFBank:
    def __init__(self):
        self.bankdb = cfdb.open()

    def init_schema(self):
        self.bankdb.execute("CREATE TABLE IF NOT EXISTS bank_accounts ('name' TEXT PRIMARY KEY, 'balance' INT);")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def ensure(self, user):
        self.bankdb.execute("INSERT OR IGNORE INTO bank_accounts VALUES (?, 0)", (user,))

    def deposit(self, user, amount):
        if amount > 0:
            self.ensure(user)
            self.bankdb.execute("UPDATE bank_accounts SET balance = balance + ? WHERE name=?", (amount, user))

    def withdraw(self, user, amount):
        if self.getbalance(user) - amount < 0:
            return 0
        else:
            self.bankdb.execute("UPDATE bank_accounts SET balance = balance - ? WHERE name=?", (amount, user))
            return 1

    def getbalance(self, user):
        self.convert_legacy_balance(user)
        c = self.bankdb.cursor()
        c.execute("SELECT balance FROM bank_accounts WHERE name=?", (user,))
        result = c.fetchone()
        if result is not None:
            return result[0]
        else:
            return 0

    def remove_account(self, user):
        self.bankdb.execute("DELETE FROM bank_accounts WHERE name=?", (user,))

    def close(self):
        self.bankdb.commit()
        self.bankdb.close()

    def convert_legacy_balance(self, name):
        """Move a player's balance from the player file to the bank."""
        player = Crossfire.FindPlayer(name)
        if player is None:
            return
        balance_str = player.ReadKey("balance")
        try:
            old_balance = int(balance_str)
            Crossfire.Log(Crossfire.LogInfo, "Converting bank account for %s with %d silver" % (name, old_balance))
            self.deposit(name, old_balance)
        except ValueError:
            pass
        player.WriteKey("balance", None, 0)

def open():
    return CFBank()
