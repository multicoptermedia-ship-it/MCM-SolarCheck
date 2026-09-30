"""Environment-backed SMTP secret access for deployed SolarCheck instances."""

from __future__ import annotations

import os
from collections.abc import MutableMapping


class EnvironmentSMTPSecretStore:
    """Keep the SMTP password outside SQLite and source-controlled configuration."""

    def __init__(
        self,
        variable_name: str = "SOLARCHECK_SMTP_PASSWORD",
        environment: MutableMapping[str, str] | None = None,
    ) -> None:
        if not isinstance(variable_name, str) or not variable_name.strip():
            raise ValueError("SMTP secret variable name must be non-empty")
        self._variable_name = variable_name
        self._environment = environment if environment is not None else os.environ

    def is_set(self) -> bool:
        value = self._environment.get(self._variable_name)
        return isinstance(value, str) and bool(value)

    def replace(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("SMTP password must be provided")
        self._environment[self._variable_name] = password

    def resolve_for_delivery(self) -> str:
        value = self._environment.get(self._variable_name)
        if not isinstance(value, str) or not value:
            raise RuntimeError("SMTP password is not configured")
        return value
