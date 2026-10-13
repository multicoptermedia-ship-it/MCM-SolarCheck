"""Fail-closed advice for manually controlled worker recovery."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MariaDBRecoveryAdvice:
    status: str
    may_reassign: bool
    action: str


def advise_mariadb_recovery(status):
    actions = {
        "empty": "no_action",
        "active": "leave_running",
        "expired_requires_quiescence": "stop_or_fence_external_worker_then_review",
        "manual_review": "investigate_inconsistent_lease",
    }
    if status not in actions:
        raise ValueError("unknown recovery status")
    return MariaDBRecoveryAdvice(status, False, actions[status])
