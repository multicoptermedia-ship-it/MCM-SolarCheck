"""Opt-in composition of Paramiko driver with host-key-first read-only probe."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.ordered_sftp_probe_composition import build_ordered_verified_sftp_probe
from mcm_solarcheck.infrastructure.paramiko_handshake_driver import ParamikoHandshakeDriver


def build_paramiko_read_only_probe(*, credentials_provider, socket_factory=None, transport_factory=None, timeout=15):
    if not callable(credentials_provider):
        raise TypeError("credentials_provider must be callable")

    def driver_factory(config):
        return ParamikoHandshakeDriver(
            config,
            socket_factory=socket_factory,
            transport_factory=transport_factory,
            credentials=credentials_provider,
            timeout=timeout,
        )

    return build_ordered_verified_sftp_probe(driver_factory)
