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


def split_for_group(group_id: str, *, train: int = 80, validation: int = 10, test: int = 10) -> str:
    """Keep correlated observations (for example one physical module) together."""
    return split_for_sample(f"group:{group_id}",train=train,validation=validation,test=test)


def assert_no_group_leakage(assignments) -> None:
    """Reject a dataset where the same physical group appears in multiple splits."""
    seen={}
    for group_id, split in assignments:
        if split not in {"train","validation","test"}:
            raise ValueError(f"unknown dataset split: {split}")
        previous=seen.setdefault(group_id,split)
        if previous != split:
            raise ValueError(f"dataset leakage for group {group_id}: {previous} vs {split}")
