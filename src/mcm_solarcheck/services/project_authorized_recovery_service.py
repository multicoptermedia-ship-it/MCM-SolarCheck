"""Require both authenticated permission and explicit project grant."""
from __future__ import annotations

from mcm_solarcheck.services.recovery_authorization import RecoveryAuthorization


class ProjectAuthorizedRecoveryService:
    def __init__(self, coordinator, grants, authorization=None):
        self.coordinator = coordinator
        self.grants = grants
        self.authorization = authorization or RecoveryAuthorization()

    def reconcile_verified(self, transfer_id, customer_id, project_id, *, identity, request_id):
        operator_id = self.authorization.authorize(identity)
        if operator_id is None:
            return "permission_denied"
        if not self.grants.allowed(operator_id, customer_id, project_id):
            return "permission_denied"
        return self.coordinator.reconcile_verified(
            transfer_id, customer_id, project_id,
            operator_id=operator_id, request_id=request_id
        )
