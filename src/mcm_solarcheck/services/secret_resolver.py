"""Resolve provider credential references without exposing secrets to domain state."""

from __future__ import annotations

from typing import Protocol


class SecretResolver(Protocol):
    def resolve(self, reference: str) -> str:
        """Resolve a validated secret reference to runtime credential material."""
        ...
