# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pgbouncer backend-database relation hooks & helpers.

This relation expects that usernames and passwords are generated and provided by the PostgreSQL
charm.

Some example relation data is below. The only parts of this we actually need are the "endpoints"
and "read-only-endpoints" fields. All values are examples taken from a test deployment, and are
not definite.

Example:
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ relation (id: 3) ┃ postgresql                               ┃ pgbouncer                                       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ relation name    │ database                                 │ backend-database                                │
│ interface        │ postgresql_client                        │ postgresql_client                               │
│ leader unit      │ 0                                        │ 2                                               │
├──────────────────┼──────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ application data │ ╭──────────────────────────────────────╮ │ ╭─────────────────────────────────────────────╮ │
│                  │ │                                      │ │ │                                             │ │
│                  │ │  data       {"database": "pgbouncer",│ │ │  database          pgbouncer                │ │
│                  │ │             "extra-user-roles":      │ │ │  extra-user-roles  SUPERUSER                │ │
│                  │ │             "SUPERUSER"}             │ │ ╰─────────────────────────────────────────────╯ │
│                  │ │  endpoints  10.180.162.236:5432      │ │                                                 │
│                  │ │  password   yPEgUWCYX0SBxpvC         │ │                                                 │
│                  │ │  username   relation-3               │ │                                                 │
│                  │ │  version    12.12                    │ │                                                 │
│                  │ ╰──────────────────────────────────────╯ │                                                 │
│ unit data        │ ╭─ postgresql/0* ─╮                      │ ╭─ pgbouncer/1 ───────────────────────────────╮ │
│                  │ │ <empty>         │                      │ │                                             │ │
│                  │ ╰─────────────────╯                      │ │  data  {"endpoints": "10.180.162.236:5432", │ │
│                  │                                          │ │         "password": "yPEgUWCYX0SBxpvC",     │ │
│                  │                                          │ │         "username": "relation-3",           │ │
│                  │                                          │ │         "version": "12.12"}                 │ │
│                  │                                          │ ╰─────────────────────────────────────────────╯ │
│                  │                                          │ ╭─ pgbouncer/2* ──────────────────────────────╮ │
│                  │                                          │ │                                             │ │
│                  │                                          │ │  data  {"endpoints": "10.180.162.236:5432", │ │
│                  │                                          │ │         "password": "yPEgUWCYX0SBxpvC",     │ │
│                  │                                          │ │        "username": "relation-3",            │ │
│                  │                                          │ │         "version": "12.12"}                 │ │
│                  │                                          │ ╰─────────────────────────────────────────────╯ │
└──────────────────┴──────────────────────────────────────────┴─────────────────────────────────────────────────┘

"""  # noqa: W505

import logging
from typing import Dict, List

import psycopg2
from charms.data_platform_libs.v0.database_requires import (
    DatabaseCreatedEvent,
    DatabaseRequires,
)
from charms.pgbouncer_k8s.v0 import pgb
from charms.postgresql_k8s.v0.postgresql import PostgreSQL
from ops.charm import CharmBase, RelationBrokenEvent, RelationDepartedEvent
from ops.framework import Object
from ops.model import (
    ActiveStatus,
    Application,
    BlockedStatus,
    MaintenanceStatus,
    Relation,
)

from constants import AUTH_FILE_PATH, BACKEND_RELATION_NAME, PG, PGB, PGB_DIR

logger = logging.getLogger(__name__)


class BackendDatabaseRequires(Object):
    """Defines functionality for the 'requires' side of the 'backend-database' relation.

    The data created in this relation allows the pgbouncer charm to connect to the postgres charm.

    Hook events observed:
        - database-created
        - database-endpoints-changed
        - database-read-only-endpoints-changed
        - relation-departed
        - relation-broken
    """

    def __init__(self, charm: CharmBase):
        super().__init__(charm, BACKEND_RELATION_NAME)

        self.charm = charm
        self.database = DatabaseRequires(
            self.charm,
            relation_name=BACKEND_RELATION_NAME,
            database_name=PGB,
            extra_user_roles="SUPERUSER",
        )

        self.framework.observe(self.database.on.database_created, self._on_database_created)
        self.framework.observe(self.database.on.endpoints_changed, self._on_endpoints_changed)
        self.framework.observe(
            self.database.on.read_only_endpoints_changed, self._on_endpoints_changed
        )
        self.framework.observe(
            charm.on[BACKEND_RELATION_NAME].relation_broken, self._on_relation_broken
        )

    def _on_database_created(self, event: DatabaseCreatedEvent) -> None:
        """Handle backend-database-database-created event.

        Accesses user and password generated by the postgres charm and adds a user.
        """
        logger.info("initialising postgres and pgbouncer relations")
        self.charm.unit.status = MaintenanceStatus("Initialising backend-database relation")
        if not self.charm.unit.is_leader():
            return
        if self.postgres is None:
            event.defer()
            logger.error("deferring database-created hook - postgres database not ready")
            return

        plaintext_password = pgb.generate_password()
        # create authentication user on postgres database, so we can authenticate other users
        # later on
        self.postgres.create_user(self.auth_user, plaintext_password, admin=True)
        self.initialise_auth_function([self.database.database, PG])

        hashed_password = pgb.get_hashed_password(self.auth_user, plaintext_password)
        self.charm.render_auth_file(f'"{self.auth_user}" "{hashed_password}"')

        cfg = self.charm.read_pgb_config()
        # adds user to pgb config
        cfg.add_user(user=event.username, admin=True)
        cfg["pgbouncer"][
            "auth_query"
        ] = f"SELECT username, password FROM {self.auth_user}.get_auth($1)"
        cfg["pgbouncer"]["auth_file"] = AUTH_FILE_PATH
        self.charm.render_pgb_config(cfg)

        self.charm.update_postgres_endpoints(reload_pgbouncer=True)

        self.charm.unit.status = ActiveStatus("backend-database relation initialised.")

    def _on_endpoints_changed(self, _):
        self.charm.update_postgres_endpoints(reload_pgbouncer=True)

    def _on_relation_departed(self, event: RelationDepartedEvent):
        """Runs pgbouncer-uninstall.sql and removes auth user.

        pgbouncer-uninstall doesn't actually uninstall anything - it actually removes permissions
        for the auth user.
        """
        if event.departing_unit != self.charm.unit or not self.charm.unit.is_leader():
            return

        logger.info("removing auth user")

        # TODO remove all databases that were created for client applications

        try:
            # TODO de-authorise all databases
            self.remove_auth_function([PGB, PG])
        except psycopg2.Error:
            self.charm.unit.status = BlockedStatus(
                "failed to remove auth user when disconnecting from postgres application."
            )
            event.fail()
            return

        self.postgres.delete_user(self.auth_user)
        logger.info("auth user removed")

    def _on_relation_broken(self, event: RelationBrokenEvent):
        """Handle backend-database-relation-broken event.

        Removes all traces of this relation from pgbouncer config.
        """
        try:
            cfg = self.charm.read_pgb_config()
        except FileNotFoundError:
            event.defer()
            return
        cfg.remove_user(self.postgres.user)
        cfg["pgbouncer"].pop("auth_user", None)
        cfg["pgbouncer"].pop("auth_query", None)
        self.charm.render_pgb_config(cfg)

        self.charm.delete_file(f"{PGB_DIR}/userlist.txt")

    def initialise_auth_function(self, dbs: List[str]):
        """Runs an SQL script to initialise the auth function.

        This function must run in every database for authentication to work correctly, and assumes
        self.postgres is set up correctly.

        Args:
            dbs: a list of database names to connect to.

        Raises:
            psycopg2.Error if self.postgres isn't usable.
        """
        logger.info("initialising auth function")
        install_script = open("src/relations/sql/pgbouncer-install.sql", "r").read()

        for dbname in dbs:
            with self.postgres.connect_to_database(dbname) as conn, conn.cursor() as cursor:
                cursor.execute(install_script.replace("auth_user", self.auth_user))
            conn.close()
        logger.info("auth function initialised")

    def remove_auth_function(self, dbs: List[str]):
        """Runs an SQL script to remove auth function.

        Args:
            dbs: a list of database names to connect to.

        Raises:
            psycopg2.Error if self.postgres isn't usable.
        """
        logger.info("removing auth function from backend relation")
        uninstall_script = open("src/relations/sql/pgbouncer-uninstall.sql", "r").read()
        for dbname in dbs:
            with self.postgres.connect_to_database(dbname) as conn, conn.cursor() as cursor:
                cursor.execute(uninstall_script.replace("auth_user", self.auth_user))
            conn.close()
        logger.info("auth function remove")

    @property
    def relation(self) -> Relation:
        """Relation object for postgres backend-database relation."""
        backend_relation = self.model.get_relation(BACKEND_RELATION_NAME)

        if not backend_relation:
            return None
        else:
            return backend_relation

    @property
    def postgres(self) -> PostgreSQL:
        """Returns PostgreSQL representation of backend database, as defined in relation.

        Returns None if backend relation is not fully initialised.
        """
        if not self.relation:
            return None

        databag = self.postgres_databag
        endpoint = databag.get("endpoints")
        user = databag.get("username")
        password = databag.get("password")
        database = self.database.database

        if None in [endpoint, user, password]:
            return None

        return PostgreSQL(
            host=endpoint.split(":")[0], user=user, password=password, database=database
        )

    @property
    def auth_user(self):
        """Username for auth_user."""
        username = self.postgres_databag.get("username")
        if username is None:
            return None

        return f"pgbouncer_auth_{username}".replace("-", "_")

    @property
    def postgres_databag(self) -> Dict:
        """Wrapper around accessing the remote application databag for the backend relation.

        Returns None if relation is none.

        Since we can trigger db-relation-changed on backend-changed, we need to be able to easily
        access the backend app relation databag.
        """
        if self.relation:
            for key, databag in self.relation.data.items():
                if isinstance(key, Application) and key != self.charm.app:
                    return databag
        return None