"""Explicit offline composition of the verified SFTP read-only probe."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.sftp_read_only_probe import SFTPReadOnlyProbe
from mcm_solarcheck.infrastructure.verified_read_only_sftp_connector import VerifiedReadOnlySFTPConnector


def build_verified_sftp_probe(client_factory):
    return SFTPReadOnlyProbe(VerifiedReadOnlySFTPConnector(client_factory))
