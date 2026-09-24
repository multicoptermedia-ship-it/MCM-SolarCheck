"""Usage gates for external model candidates."""
from __future__ import annotations

from dataclasses import dataclass

from .model_manifest import ModelManifest
from .model_validation import ModelValidationDecision


@dataclass(frozen=True)
class ModelUseAuthorization:
    commercial_rights_verified: bool
    validation: ModelValidationDecision

    @property
    def customer_project_allowed(self) -> bool:
        return self.commercial_rights_verified and self.validation.accepted


def require_customer_project_authorization(
    manifest: ModelManifest,
    authorization: ModelUseAuthorization,
) -> None:
    """Fail closed before an external model can be used on a customer project."""
    if not authorization.commercial_rights_verified:
        raise PermissionError(
            f"commercial rights are not verified for external model {manifest.provider}"
        )
    if not authorization.validation.accepted:
        reasons="; ".join(authorization.validation.reasons) or "validation not accepted"
        raise ValueError(f"external model failed M3T validation: {reasons}")
