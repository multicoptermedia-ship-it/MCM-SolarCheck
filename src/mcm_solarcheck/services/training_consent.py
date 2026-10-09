"""Explicit, optional training permission; no training data is copied here."""
from __future__ import annotations

NOTICE_VERSION = "training-images-v1"


class TrainingConsentService:
    def __init__(self, store, projects):
        self._store = store
        self._projects = projects

    def grant(self, *, customer_id: str, project_id: str) -> None:
        self._require_owner(customer_id, project_id)
        self._store.record(customer_id=customer_id, project_id=project_id, event="granted", notice_version=NOTICE_VERSION)

    def withdraw(self, *, customer_id: str, project_id: str) -> None:
        self._require_owner(customer_id, project_id)
        self._store.record(customer_id=customer_id, project_id=project_id, event="withdrawn", notice_version=NOTICE_VERSION)

    def _require_owner(self, customer_id: str, project_id: str) -> None:
        if not self._projects(customer_id, project_id):
            raise PermissionError("project is not available to customer")
