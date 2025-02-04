# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postgres db relation hooks & helpers.

This relation creates the necessary databag information (an example is given below) for database
connections, and updates the config with the correct information for pgbouncer to connect to the
backend database. As a result, pretty much every part of this relation relies on the backend
relation being implemented first.

Both databags are used, because different legacy charms expect the data from different databags.

This relation uses the pgsql interface, omitting roles and extensions as they are unsupported in
the new postgres charm.

Some example relation data is below. All values are examples, generated in a running test instance.
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ relation (id: 4) ┃ psql                ┃ pgbouncer                                                       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ relation name    │ db                  │ db-admin                                                        │
│ interface        │ pgsql               │ pgsql                                                           │
│ leader unit      │ 0                   │ 0                                                               │
├──────────────────┼─────────────────────┼─────────────────────────────────────────────────────────────────┤
│ application data │ ╭─────────────────╮ │ ╭─────────────────────────────────────────────────────────────╮ │
│                  │ │ <empty>         │ │ │                                                             │ │
│                  │ ╰─────────────────╯ │ │  allowed-subnets  10.180.162.56/32                          │ │
│                  │                     │ │  allowed-units    psql/0                                    │ │
│                  │                     │ │  database         cli                                       │ │
│                  │                     │ │  host             10.180.162.4                              │ │
│                  │                     │ │  master           host=10.180.162.4 dbname=cli port=6432    │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  password         T6NX0iz1ZRHZF5kfYDanKM5z                  │ │
│                  │                     │ │  port             6432                                      │ │
│                  │                     │ │  standbys         host=10.180.162.203 dbname=cli_standby po │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  state            master                                    │ │
│                  │                     │ │  user             pgbouncer_user_4_test_db_admin_3una       │ │
│                  │                     │ │  version          12.12                                     │ │
│                  │                     │ ╰─────────────────────────────────────────────────────────────╯ │
│ unit data        │ ╭─ psql/0* ───────╮ │ ╭─ pgbouncer/0* ──────────────────────────────────────────────╮ │
│                  │ │                 │ │ │                                                             │ │
│                  │ │  database  cli  │ │ │  allowed-subnets  10.180.162.56/32                          │ │
│                  │ ╰─────────────────╯ │ │  allowed-units    psql/0                                    │ │
│                  │                     │ │  database         cli                                       │ │
│                  │                     │ │  host             10.180.162.4                              │ │
│                  │                     │ │  master           host=10.180.162.4 dbname=cli port=6432    │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  password         T6NX0iz1ZRHZF5kfYDanKM5z                  │ │
│                  │                     │ │  port             6432                                      │ │
│                  │                     │ │  standbys         host=10.180.162.203 dbname=cli_standby po │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  state            master                                    │ │
│                  │                     │ │  user             pgbouncer_user_4_test_db_admin_3una       │ │
│                  │                     │ │  version          12.12                                     │ │
│                  │                     │ ╰─────────────────────────────────────────────────────────────╯ │
│                  │                     │ ╭─ pgbouncer/1 ───────────────────────────────────────────────╮ │
│                  │                     │ │                                                             │ │
│                  │                     │ │  allowed-subnets  10.180.162.56/32                          │ │
│                  │                     │ │  allowed-units    psql/0                                    │ │
│                  │                     │ │  database         cli                                       │ │
│                  │                     │ │  host             10.180.162.203                            │ │
│                  │                     │ │  master           host=10.180.162.4 dbname=cli port=6432    │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  password         T6NX0iz1ZRHZF5kfYDanKM5z                  │ │
│                  │                     │ │  port             6432                                      │ │
│                  │                     │ │  standbys         host=10.180.162.203 dbname=cli_standby po │ │
│                  │                     │ │                   user=pgbouncer_user_4_test_db_admin_3una  │ │
│                  │                     │ │                   password=T6NX0iz1ZRHZF5kfYDanKM5z         │ │
│                  │                     │ │                   fallback_application_name=psql            │ │
│                  │                     │ │  state            standby                                   │ │
│                  │                     │ │  user             pgbouncer_user_4_test_db_admin_3una       │ │
│                  │                     │ │  version          12.12                                     │ │
│                  │                     │ ╰─────────────────────────────────────────────────────────────╯ │
└──────────────────┴─────────────────────┴─────────────────────────────────────────────────────────────────┘
"""  # noqa: W505

import logging
from typing import Dict, Iterable

from charms.pgbouncer_k8s.v0 import pgb
from charms.postgresql_k8s.v0.postgresql import (
    PostgreSQLCreateDatabaseError,
    PostgreSQLCreateUserError,
    PostgreSQLDeleteUserError,
)
from ops.charm import (
    CharmBase,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationDepartedEvent,
    RelationJoinedEvent,
)
from ops.framework import Object
from ops.model import (
    ActiveStatus,
    Application,
    BlockedStatus,
    MaintenanceStatus,
    Relation,
    Unit,
    WaitingStatus,
)

from constants import PG

logger = logging.getLogger(__name__)


class RelationNotInitialisedError(Exception):
    """An error to be raised if the relation is not initialised."""


class DbProvides(Object):
    """Defines functionality for the 'provides' side of the 'db' relation.

    This relation connects to client applications, providing database services in an identical way
    to the same relation in the PostgreSQL charm, to the point where they should be
    indistinguishable to the client app.

    Hook events observed:
        - relation-joined
        - relation-changed
        - relation-departed
        - relation-broken
    """

    def __init__(self, charm: CharmBase, admin: bool = False):
        """Constructor for DbProvides object.

        Args:
            charm: the charm for which this relation is provided
            admin: a boolean defining whether or not this relation has admin permissions, switching
                between "db" and "db-admin" relations.
        """
        if admin:
            self.relation_name = "db-admin"
        else:
            self.relation_name = "db"

        super().__init__(charm, self.relation_name)

        self.framework.observe(
            charm.on[self.relation_name].relation_joined, self._on_relation_joined
        )
        self.framework.observe(
            charm.on[self.relation_name].relation_changed, self._on_relation_changed
        )
        self.framework.observe(
            charm.on[self.relation_name].relation_departed, self._on_relation_departed
        )
        self.framework.observe(
            charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )

        self.charm = charm
        self.admin = admin

    def _on_relation_joined(self, join_event: RelationJoinedEvent):
        """Handle db-relation-joined event.

        If the backend relation is fully initialised and available, we generate the proposed
        database and create a user on the postgres charm, and add preliminary data to the databag.
        """
        self.charm.unit.status = self.charm.check_status()
        if not isinstance(self.charm.unit.status, ActiveStatus):
            join_event.defer()
            return

        logger.info(f"Setting up {self.relation_name} relation")
        logger.warning(
            f"DEPRECATION WARNING - {self.relation_name} is a legacy relation, and will be deprecated in a future release. "
        )

        remote_app_databag = join_event.relation.data[join_event.app]
        remote_unit_databag = join_event.relation.data[join_event.unit]
        if not (database := remote_app_databag.get("database")) and not (
            database := remote_unit_databag.get("database")
        ):
            # If there's nothing in either databag, return early.
            no_db = "No database name provided in app or unit databag"
            logger.warning(no_db)
            self.charm.unit.status = WaitingStatus(no_db)
            join_event.defer()
            return

        # Do not allow apps requesting extensions to be installed. Extensions should be installed
        # through db charm config
        if (
            remote_app_databag.get("extensions") is not None
            or remote_unit_databag.get("extensions") is not None
        ):
            logger.error(
                "ERROR - `extensions` cannot be requested through relations"
                " - they should be installed through a database charm config in the future"
            )
            self.charm.unit.status = BlockedStatus(
                "bad relation request - remote app requested extensions, which are unsupported. Please remove this relation."
            )
            join_event.fail()
            return

        user = self._generate_username(join_event)
        if self.charm.unit.is_leader():
            password = pgb.generate_password()
        else:
            if not (password := self.charm.peers.app_databag.get(user, None)):
                join_event.defer()

        self.update_databags(
            join_event.relation,
            {
                "user": user,
                "password": password,
                "database": database,
            },
        )

        if not self.charm.unit.is_leader():
            return

        # Create user and database in backend postgresql database
        try:
            init_msg = f"initialising database and user for {self.relation_name} relation"
            self.charm.unit.status = MaintenanceStatus(init_msg)
            logger.info(init_msg)

            self.charm.backend.postgres.create_user(user, password, admin=self.admin)
            self.charm.backend.postgres.create_database(database, user)

            created_msg = f"database and user for {self.relation_name} relation created"
            self.charm.unit.status = ActiveStatus(created_msg)
            logger.info(created_msg)
        except (PostgreSQLCreateDatabaseError, PostgreSQLCreateUserError):
            err_msg = f"failed to create database or user for {self.relation_name}"
            logger.error(err_msg)
            join_event.fail()
            self.charm.unit.status = BlockedStatus(err_msg)
            return

        # set up auth function
        self.charm.backend.initialise_auth_function([database])
        self.charm.peers.add_user(user, password)

        # Create user in pgbouncer config
        cfg = self.charm.read_pgb_config()
        cfg.add_user(user, admin=self.admin)
        self.charm.render_pgb_config(cfg, reload_pgbouncer=True)

    def _on_relation_changed(self, change_event: RelationChangedEvent):
        """Handle db-relation-changed event.

        Takes information from the pgbouncer db app relation databag and copies it into the
        pgbouncer.ini config.

        This relation will defer if the backend relation isn't fully available, and if the
        relation_joined hook isn't completed.
        """
        self.charm.unit.status = self.charm.check_status()
        if not isinstance(self.charm.unit.status, ActiveStatus):
            change_event.defer()
            return

        logger.warning(
            f"DEPRECATION WARNING - {self.relation_name} is a legacy relation, and will be deprecated in a future release. "
        )

        # No backup values because if databag isn't populated, this relation isn't initialised.
        # This means that the database and user requested in this relation haven't been created, so
        # we defer this event until the databag is populated.
        databag = self.get_databags(change_event.relation)[0]
        database = databag.get("database")
        user = databag.get("user")
        password = databag.get("password")

        if None in [database, user, password]:
            not_initialised = (
                "relation not fully initialised - deferring until join_event is complete"
            )
            logger.warning(not_initialised)
            self.charm.unit.status = WaitingStatus(not_initialised)
            change_event.defer()
            return

        self.update_connection_info(change_event.relation, self.charm.config["listen_port"])
        self.update_postgres_endpoints(change_event.relation, reload_pgbouncer=True)
        self.update_databags(
            change_event.relation,
            {
                "allowed-subnets": self.get_allowed_subnets(change_event.relation),
                "allowed-units": self.get_allowed_units(change_event.relation),
                "version": self.charm.backend.postgres.get_postgresql_version(),
                "host": self.charm.unit_ip,
                "user": user,
                "password": password,
                "database": database,
                "state": self._get_state(),
            },
        )

    def update_connection_info(self, relation: Relation, port: str = None):
        """Updates databag connection info."""
        if not port:
            port = self.charm.config["listen_port"]

        databag = self.get_databags(relation)[0]
        database = databag.get("database")
        user = databag.get("user")
        password = databag.get("password")

        if None in [database, user, password]:
            logger.warning("relation not fully initialised - skipping port update")
            return

        master_dbconnstr = {
            "host": "localhost",
            "dbname": database,
            "port": port,
            "user": user,
            "password": password,
            "fallback_application_name": self.get_external_app(relation).name,
        }

        connection_updates = {
            "master": pgb.parse_dict_to_kv_string(master_dbconnstr),
            "port": str(port),
            "host": "localhost",
        }

        self.update_databags(relation, connection_updates)

    def update_postgres_endpoints(self, relation: Relation, reload_pgbouncer: bool = False):
        """Updates postgres replicas.

        Requires the backend relation to be running.
        """
        database = self.get_databags(relation)[0].get("database")
        if database is None:
            logger.warning(
                f"{self.relation_name} relation not fully initialised - skipping postgres endpoint update"
            )
            # TODO return false
            return

        # In postgres, "endpoints" will only ever have one value. Other databases using the library
        # can have more, but that's not planned for the postgres charm.
        postgres_endpoint = self.charm.backend.postgres_databag.get("endpoints")

        cfg = self.charm.read_pgb_config()
        cfg["databases"][database] = {
            "host": postgres_endpoint.split(":")[0],
            "dbname": database,
            "port": postgres_endpoint.split(":")[1],
            "auth_user": self.charm.backend.auth_user,
        }

        read_only_endpoints = self.charm.backend.get_read_only_endpoints()
        if len(read_only_endpoints) > 0:
            cfg["databases"][f"{database}_standby"] = {
                "host": ",".join([ep.split(":")[0] for ep in read_only_endpoints]),
                "dbname": database,
                "port": next(iter(read_only_endpoints)).split(":")[1],
                "auth_user": self.charm.backend.auth_user,
            }
        else:
            cfg["databases"].pop(f"{database}_standby", None)

        if self.admin:
            # Admin relations get access to postgres root db
            cfg["databases"][PG] = {
                "host": postgres_endpoint.split(":")[0],
                "dbname": PG,
                "port": postgres_endpoint.split(":")[1],
                "auth_user": self.charm.backend.auth_user,
            }

        # Write config data to charm filesystem
        self.charm.render_pgb_config(cfg, reload_pgbouncer=reload_pgbouncer)

    def _on_relation_departed(self, departed_event: RelationDepartedEvent):
        """Handle db-relation-departed event.

        Removes relevant information from pgbouncer config when db relation is removed. This
        function assumes that relation databags are destroyed when the relation itself is removed.
        """
        logger.info("db relation removed - updating config")
        logger.warning(
            f"DEPRECATION WARNING - {self.relation_name} is a legacy relation, and will be deprecated in a future release. "
        )

        self.update_databags(
            departed_event.relation,
            {"allowed-units": self.get_allowed_units(departed_event.relation)},
        )

        # If a departed event is dispatched to itself, this relation isn't being scaled down -
        # it's being removed
        if departed_event.app == self.charm.app and self.charm.unit.is_leader():
            self.charm.peers.app_databag[
                f"{self.relation_name}-{self.relation.id}-relation-breaking"
            ] = "true"

    def _on_relation_broken(self, broken_event: RelationBrokenEvent):
        """Handle db-relation-broken event.

        Removes all traces of the given application from the pgbouncer config, and removes relation
        user if its unused by any other relations.

        This doesn't delete any tables so we aren't deleting a user's entire database with one
        command.
        """
        # Only delete relation data if we're the leader, and we're the last unit to leave.
        if not self.charm.unit.is_leader():
            self.charm.update_client_connection_info()
            return
        break_flag = f"{self.relation_name}-{broken_event.relation.id}-relation-breaking"
        if not self.charm.peers.app_databag.get(break_flag, None):
            # This relation isn't being removed, so we don't need to do the relation teardown
            # steps.
            self.update_connection_info(broken_event.relation)
            return

        del self.charm.peers.app_databag[break_flag]

        databag = self.get_databags(broken_event.relation)[0]
        user = databag.get("user")
        database = databag.get("database")

        if not self.charm.backend.postgres or None in [user, database]:
            # this relation was never created, so wait for it to be initialised before removing
            # everything.
            logger.warning(
                f"backend relation not yet available - deferring {self.relation_name}-relation-broken event."
            )
            broken_event.defer()
            return

        cfg = self.charm.read_pgb_config()

        # check database can be deleted from pgb config, and if so, delete it. Database is kept on
        # postgres application because we don't want to delete all user data with one command.
        delete_db = True
        relations = self.model.relations.get("db", []) + self.model.relations.get("db-admin", [])
        for relation in relations:
            if relation.id == broken_event.relation.id:
                continue
            if relation.data[self.charm.unit].get("database") == database:
                # There's multiple applications using this database, so don't remove it until
                # we can guarantee this is the last one.
                delete_db = False
                break

        if delete_db:
            cfg["databases"].pop(database, None)
            cfg["databases"].pop(f"{database}_standby", None)
            self.charm.backend.remove_auth_function([database])

        # TODO delete postgres database from config if there's no admin relations left

        cfg.remove_user(user)
        self.charm.render_pgb_config(cfg, reload_pgbouncer=True)
        self.charm.peers.remove_user(user)

        try:
            self.charm.backend.postgres.delete_user(user)
        except PostgreSQLDeleteUserError as err:
            # We've likely lost connection at this point, and can't do anything about a
            # trailing user.
            logger.error(f"connection lost to PostgreSQL - unable to delete user {user}.")
            logger.error(err)

    def get_databags(self, relation):
        """Returns a list of writable databags for this unit."""
        databags = [relation.data[self.charm.unit]]
        if self.charm.unit.is_leader():
            databags.append(relation.data[self.charm.app])
        return databags

    def update_databags(self, relation, updates: Dict[str, str]):
        """Updates databag with the given dict."""
        databags = self.get_databags(relation)

        # Databag entries can only be strings
        for key, item in updates.items():
            updates[key] = str(item)

        for databag in databags:
            databag.update(updates)

    def _generate_username(self, event):
        """Generates a unique username for this relation."""
        app_name = self.charm.app.name
        relation_id = event.relation.id
        model_name = self.model.name
        return f"{app_name}_user_{relation_id}_{model_name}".replace("-", "_")

    def _get_state(self) -> str:
        """Gets the given state for this unit.

        Args:
            standbys: the comma-separated list of postgres standbys

        Returns:
            The described state of this unit. Can be 'master' or 'standby'.
        """
        if self.charm.unit.is_leader():
            return "master"
        else:
            return "standby"

    def get_allowed_subnets(self, relation: Relation) -> str:
        """Gets the allowed subnets from this relation."""

        def _comma_split(string) -> Iterable[str]:
            if string:
                for substring in string.split(","):
                    substring = substring.strip()
                    if substring:
                        yield substring

        subnets = set()
        for unit, reldata in relation.data.items():
            logger.warning(f"Checking subnets for {unit}")
            if isinstance(unit, Unit) and not unit.name.startswith(self.model.app.name):
                # NB. egress-subnets is not always available.
                subnets.update(set(_comma_split(reldata.get("egress-subnets", ""))))
        return ",".join(sorted(subnets))

    def get_allowed_units(self, relation: Relation) -> str:
        """Gets the external units from this relation that can be allowed into the network."""
        return ",".join(
            sorted(
                [
                    unit.name
                    for unit in relation.data
                    if isinstance(unit, Unit) and unit.app != self.charm.app
                ]
            )
        )

    def get_external_app(self, relation):
        """Gets external application, as an Application object."""
        for entry in relation.data.keys():
            if isinstance(entry, Application) and entry != self.charm.app:
                return entry
