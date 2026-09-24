"""Deterministic split assignment for reproducible model training."""
from __future__ import annotations
from hashlib import sha256


def split_for_sample(sample_id: str, *, train: int = 80, validation: int = 10, test: int = 10) -> str:
    if train <= 0 or validation <= 0 or test <= 0 or train + validation + test != 100:
        raise ValueError("training split percentages must be positive and sum to 100")
    if not sample_id.strip():
        raise ValueError("sample id must not be empty")
    bucket=int(sha256(sample_id.encode()).hexdigest()[:8],16) % 100
    if bucket < train:return "train"
    if bucket < train + validation:return "validation"
    return "test"
