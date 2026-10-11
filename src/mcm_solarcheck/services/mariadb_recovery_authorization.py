"""Explicit recovery authorization: no expiry-only reclamation."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class QuiescenceProof:
    job_id: int
    slot_id: int
    lease_token: str
    operator_id: str
    evidence_reference: str

    def __post_init__(self):
        if type(self.job_id) is not int or self.job_id <= 0:
            raise ValueError("invalid job")
        if type(self.slot_id) is not int or self.slot_id not in (1, 2):
            raise ValueError("invalid slot")
        if not isinstance(self.lease_token, str) or len(self.lease_token) != 32 or any(c not in "0123456789abcdef" for c in self.lease_token):
            raise ValueError("invalid token")
        for value in (self.operator_id, self.evidence_reference):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValueError("operator and evidence required")
