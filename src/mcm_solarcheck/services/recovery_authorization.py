"""Fail-closed operator permission checks for explicit recovery actions.

Only trusted authentication infrastructure may construct the identity object.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryOperator:
    operator_id: str
    authenticated: bool
    permissions: frozenset[str]


class RecoveryAuthorization:
    REQUIRED = "publication:reconcile"

    def authorize(self, identity):
        if not isinstance(identity, RecoveryOperator):
            return None
        if identity.authenticated is not True:
            return None
        if not isinstance(identity.operator_id, str) or not 0 < len(identity.operator_id) <= 256:
            return None
        if not isinstance(identity.permissions, frozenset):
            return None
        if self.REQUIRED not in identity.permissions:
            return None
        return identity.operator_id
