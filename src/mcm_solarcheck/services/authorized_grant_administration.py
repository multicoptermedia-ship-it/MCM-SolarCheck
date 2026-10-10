"""Administrative grant mutation requires a separately authenticated admin."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GrantAdministrator:
    actor_id: str
    authenticated: bool
    permissions: frozenset[str]


class AuthorizedGrantAdministration:
    REQUIRED = "publication:manage_grants"

    def __init__(self, grants):
        self.grants = grants

    def set_grant(self, identity, operator_id, customer_id, project_id, enabled):
        if not isinstance(identity, GrantAdministrator):
            return "permission_denied"
        if identity.authenticated is not True:
            return "permission_denied"
        if not isinstance(identity.actor_id, str) or not 0 < len(identity.actor_id) <= 256:
            return "permission_denied"
        if not isinstance(identity.permissions, frozenset) or self.REQUIRED not in identity.permissions:
            return "permission_denied"
        self.grants.set_grant(identity.actor_id, operator_id, customer_id, project_id, enabled)
        return "grant_updated"
