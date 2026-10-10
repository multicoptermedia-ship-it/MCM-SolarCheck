"""Read-only SFTP probe with explicit host-key verification delegated to connector.

No credentials or network client are constructed by this service.
"""
from __future__ import annotations


class SFTPReadOnlyProbe:
    def __init__(self, connector):
        self.connector = connector

    def inspect(self, config):
        # The connector must verify the pinned host key before exposing any session.
        with self.connector.open_verified_read_only(config) as session:
            return {
                "root_exists": session.directory_exists(config.root),
                "host_key_verified": True,
            }
