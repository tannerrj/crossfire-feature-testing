# CFMail.py - CFMail class
#
# Copyright (C) 2003 Todd Mitchell
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
# Rewritten to use CFSqlDb

import Crossfire
import CFSqlDb as cfdb

class CFMail:
    def __init__(self):
        self.maildb = cfdb.open()

    def init_schema(self):
        self.maildb.execute("CREATE TABLE IF NOT EXISTS mail ('recipient' TEXT, 'sender' TEXT, 'date' DATE, 'type' INT, 'message' TEXT);")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send(self, type, toname, fromname, message):
        # type: 1=mailscoll, 2=newsletter, 3=mailwarning
        self.maildb.execute("INSERT INTO mail VALUES (?, ?, datetime('now'), ?, ?);", (toname, fromname, type, message))

    def receive(self, toname):
        c = self.maildb.cursor()
        c.execute("SELECT type, sender, message FROM mail WHERE recipient=?;", (toname,))
        mail = list()
        for el in c.fetchall():
            mail.append(el)
        c.execute("DELETE FROM mail WHERE recipient=?;", (toname,))
        return mail

    def countmail(self, toname):
        c = self.maildb.cursor()
        c.execute("SELECT COUNT(*) FROM mail WHERE recipient=?;", (toname,))
        return c.fetchone()[0]

    def close(self):
        self.maildb.commit()
        self.maildb.close()
