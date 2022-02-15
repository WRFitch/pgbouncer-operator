# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

from lib.charms.pgbouncer_operator.v0 import pgb


class TestPgb(unittest.TestCase):
    def test_generate_password(self):
        pw = pgb.generate_password()
        self.assertEqual(len(pw), 24)

    def test_generate_pgbouncer_ini(self):
        users = {"test1": "pw1", "test2": "pw2"}
        # This should be updated to mock a juju config object
        config = {
            "pgb_databases": "test-dbs",
            "pgb_listen_port": "4454",
            "pgb_listen_address": "4.4.5.4",
        }
        pgb_ini = pgb.generate_pgbouncer_ini(users, config)
        expected_pgb_ini = f"""[databases]
{config["pgb_databases"]}

[pgbouncer]
listen_port = {config["pgb_listen_port"]}
listen_addr = {config["pgb_listen_address"]}
auth_type = md5
auth_file = userlist.txt
logfile = pgbouncer.log
pidfile = pgbouncer.pid
admin_users = {",".join(users.keys())}"""
        self.assertEqual(pgb_ini, expected_pgb_ini)

    def test_generate_userlist(self):
        users = {"test1": "pw1", "test2": "pw2"}
        userlist = pgb.generate_userlist(users)
        expected_userlist = '''"test1" "pw1"
"test2" "pw2"'''
        self.assertEqual(userlist, expected_userlist)