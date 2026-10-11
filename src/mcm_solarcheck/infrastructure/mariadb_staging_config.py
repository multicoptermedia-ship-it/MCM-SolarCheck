"""Validated MariaDB staging settings; no network connection is made."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MariaDBStagingConfig:
    host: str
    port: int
    database: str
    username: str
    tls_ca_file: str

    def __post_init__(self):
        for name in ("host", "database", "username", "tls_ca_file"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 255:
                raise ValueError(f"invalid {name}")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("invalid port")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.host):
            raise ValueError("invalid host")
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.database):
            raise ValueError("invalid database name")
        if not re.fullmatch(r"[A-Za-z0-9_@.%-]+", self.username):
            raise ValueError("invalid username")
