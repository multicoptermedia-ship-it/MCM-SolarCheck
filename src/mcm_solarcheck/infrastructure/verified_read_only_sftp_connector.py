"""Injected SSH client connector for verified read-only SFTP sessions.

The client factory is provided by a trusted integration layer. This module
does not import a network library, resolve DNS or open sockets on its own.
"""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sftp_host_key_pin import verify_ssh_host_key


class VerifiedReadOnlySFTPConnector:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def open_verified_read_only(self, config):
        client = self.client_factory(config)
        try:
            # The injected client must complete SSH negotiation without
            # automatically trusting unknown host keys.
            key_blob = client.negotiated_host_key_blob()
            verify_ssh_host_key(key_blob, config.host_key_sha256)
            session = client.open_read_only_sftp()
            return _VerifiedSession(client, session)
        except BaseException:
            client.close()
            raise


class _VerifiedSession:
    def __init__(self, client, session):
        self.client = client
        self.session = session

    def __enter__(self):
        return self

    def directory_exists(self, path):
        return self.session.directory_exists(path)

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.session.close()
        finally:
            self.client.close()
        return False
