"""Server-owned canonical final names for local publication prototypes."""
from __future__ import annotations

from pathlib import Path
import re


_TOKEN = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")


def canonical_local_destination(root, customer_id, project_id, transfer_id):
    for label, value in (("customer", customer_id), ("project", project_id), ("transfer", transfer_id)):
        if not isinstance(value, str) or not _TOKEN.fullmatch(value):
            raise ValueError(f"invalid {label} identifier")
    base = Path(root)
    if not base.is_absolute() or base.is_symlink():
        raise ValueError("root must be an absolute non-symlink directory")
    return base / customer_id / project_id / f"{transfer_id}.bin"
