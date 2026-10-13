"""Fail-closed capability policy for injected SFTP transports.

Method presence alone does not prove server-side atomicity or exclusivity.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SFTPCapabilities:
    exclusive_create_verified: bool = False
    exclusive_publish_verified: bool = False
    remote_fencing_verified: bool = False


class SFTPCapabilityPolicy:
    def __init__(self, capabilities):
        if not isinstance(capabilities, SFTPCapabilities):
            raise TypeError("explicit SFTP capability evidence required")
        self.capabilities = capabilities

    def allow_immutable_part_write(self):
        return self.capabilities.exclusive_create_verified is True

    def allow_final_publication(self):
        return (
            self.capabilities.exclusive_publish_verified is True
            and self.capabilities.remote_fencing_verified is True
        )
