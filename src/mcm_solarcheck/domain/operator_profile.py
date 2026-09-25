"""Operator identity and branding used for customer-facing reports."""
from __future__ import annotations
from dataclasses import dataclass


def _required(name,value):
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"{name} must not be empty")
    return value.strip()


@dataclass(frozen=True)
class OperatorProfile:
    company_name: str
    street: str
    postal_code: str
    city: str
    email: str
    phone: str | None = None
    website: str | None = None
    tax_id: str | None = None
    vat_id: str | None = None
    logo_path: str | None = None

    def __post_init__(self):
        for name in ("company_name","street","postal_code","city","email"):
            _required(name,getattr(self,name))
        for name in ("phone","website","tax_id","vat_id","logo_path"):
            value=getattr(self,name)
            if value is not None: _required(name,value)

    @property
    def address(self) -> str:
        return f"{self.street}, {self.postal_code} {self.city}"
