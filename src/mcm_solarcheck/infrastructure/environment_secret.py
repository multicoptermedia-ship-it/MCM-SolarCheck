"""Environment-backed runtime secret resolution."""

from __future__ import annotations

import os
from collections.abc import Mapping


class EnvironmentSecretResolver:
    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = os.environ if environ is None else environ

    def resolve(self, reference: str) -> str:
        if not isinstance(reference, str) or not reference.startswith("env:"):
            raise ValueError("environment resolver requires env: reference")
        key = reference.split(":", 1)[1].strip()
        if not key:
            raise ValueError("environment secret reference must include a key")
        try:
            value = self._environ[key]
        except KeyError:
            raise KeyError(reference) from None
        if not isinstance(value, str) or not value:
            raise ValueError("resolved environment secret must be non-empty")
        return value
