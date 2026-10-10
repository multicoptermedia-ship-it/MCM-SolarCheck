"""Compose the ordered SSH factory into the existing read-only SFTP probe."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.ordered_ssh_client_factory import OrderedSSHClientFactory
from mcm_solarcheck.infrastructure.verified_sftp_probe_composition import build_verified_sftp_probe


def build_ordered_verified_sftp_probe(driver_factory):
    return build_verified_sftp_probe(OrderedSSHClientFactory(driver_factory))
