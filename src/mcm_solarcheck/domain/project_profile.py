"""Project/customer data entered once at project creation and reused by reports."""
from __future__ import annotations
from dataclasses import dataclass


def _required(name: str, value: str) -> str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()


@dataclass(frozen=True)
class ProjectProfile:
    customer_name: str
    site_name: str
    site_street: str
    site_postal_code: str
    site_city: str
    inspector: str
    customer_contact: str | None = None
    customer_street: str | None = None
    customer_postal_code: str | None = None
    customer_city: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_reference: str | None = None
    order_reference: str | None = None

    def __post_init__(self) -> None:
        for name in ("customer_name","site_name","site_street","site_postal_code","site_city","inspector"):
            _required(name,getattr(self,name))
        for name in ("customer_contact","customer_street","customer_postal_code","customer_city","customer_email","customer_phone","customer_reference","order_reference"):
            value=getattr(self,name)
            if value is not None and (not isinstance(value,str) or not value.strip()):
                raise ValueError(f"{name} must be non-empty when provided")
