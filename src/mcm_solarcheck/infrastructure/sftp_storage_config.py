"""Validate remote SFTP storage configuration without opening a connection."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SFTPStorageConfig:
    host: str
    port: int
    username: str
    root: str
    host_key_sha256: str

    def __post_init__(self):
        if not isinstance(self.host, str) or not self.host or any(c.isspace() for c in self.host):
            raise ValueError("invalid SFTP host")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("invalid SFTP port")
        if not isinstance(self.username, str) or not self.username or any(c.isspace() for c in self.username):
            raise ValueError("invalid SFTP username")
        if not isinstance(self.root, str) or not self.root.startswith("/") or self.root == "/" or chr(92) in self.root or chr(0) in self.root:
            raise ValueError("private absolute SFTP root required")
        if any(part in (".", "..") for part in self.root.split("/") if part):
            raise ValueError("unsafe SFTP root")
        if not isinstance(self.host_key_sha256, str) or not self.host_key_sha256.startswith("SHA256:") or len(self.host_key_sha256) < 20:
            raise ValueError("pinned host key fingerprint required")
