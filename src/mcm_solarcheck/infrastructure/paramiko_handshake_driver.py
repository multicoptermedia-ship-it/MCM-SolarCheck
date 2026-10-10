"""Paramiko transport driver: no authentication before pinned host-key verification.

This optional adapter does not connect until the injected probe is invoked.
Paramiko is imported lazily and is not installed by this module.
"""
from __future__ import annotations

import socket

from mcm_solarcheck.infrastructure.sftp_connection_errors import SFTPTimeoutError


class ParamikoHandshakeDriver:
    def __init__(self, config, *, socket_factory=None, transport_factory=None, credentials=None, timeout=15):
        self.config = config
        self.socket_factory = socket_factory or socket.create_connection
        self.transport_factory = transport_factory
        self.credentials = credentials
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 120:
            raise ValueError("timeout must be between 0 and 120 seconds")
        self.timeout = timeout
        self.transport = None
        self.socket = None

    def negotiate_without_authentication(self):
        if self.transport is not None:
            raise RuntimeError("SSH handshake already started")
        try:
            self.socket = self.socket_factory((self.config.host, self.config.port), self.timeout)
            if self.transport_factory is None:
                import paramiko
                factory = paramiko.Transport
            else:
                factory = self.transport_factory
            self.transport = factory(self.socket)
            self.transport.start_client(timeout=self.timeout)
        except BaseException as exc:
            try:
                self.close()
            except Exception:
                pass
            if isinstance(exc, (socket.timeout, TimeoutError)):
                raise SFTPTimeoutError("SSH handshake timed out") from exc
            raise

    def negotiated_host_key_blob(self):
        if self.transport is None:
            raise RuntimeError("SSH handshake not established")
        key = self.transport.get_remote_server_key()
        if key is None:
            raise RuntimeError("SSH server key missing")
        return key.asbytes()

    def authenticate(self):
        if self.transport is None:
            raise RuntimeError("SSH handshake not established")
        if self.credentials is None:
            raise PermissionError("explicit credentials provider required")
        credentials = self.credentials()
        if not isinstance(credentials, dict):
            raise TypeError("credentials provider must return a mapping")
        if set(credentials) != {"password"} or not isinstance(credentials["password"], str):
            raise ValueError("only explicit password authentication is supported")
        self.transport.auth_password(self.config.username, credentials["password"])
        if not self.transport.is_authenticated():
            raise PermissionError("SSH authentication failed")

    def open_read_only_sftp(self):
        if self.transport is None or not self.transport.is_authenticated():
            raise PermissionError("SSH authentication required")
        import paramiko
        return _ReadOnlySFTPSession(paramiko.SFTPClient.from_transport(self.transport))

    def close(self):
        transport, sock = self.transport, self.socket
        self.transport, self.socket = None, None
        try:
            if transport is not None:
                transport.close()
        finally:
            if sock is not None:
                sock.close()


class _ReadOnlySFTPSession:
    def __init__(self, client):
        self.client = client

    def directory_exists(self, path):
        import stat
        try:
            return stat.S_ISDIR(self.client.stat(path).st_mode)
        except OSError:
            return False

    def close(self):
        self.client.close()
