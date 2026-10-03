"""Explicit image-representation contract for pretrained model inference."""
from __future__ import annotations

from dataclasses import dataclass


_ALLOWED_REPRESENTATIONS={"rendered_rgb", "grayscale_8bit"}


@dataclass(frozen=True)
class InferenceInput:
    image: object
    representation: str
    source_frame_id: str

    def __post_init__(self) -> None:
        if self.representation not in _ALLOWED_REPRESENTATIONS:
            raise ValueError(
                "model inference requires an explicitly rendered image representation"
            )
        if not self.source_frame_id.strip():
            raise ValueError("inference source frame must not be empty")


def require_preprocessing_contract(value: InferenceInput, expected: str) -> object:
    """Return image only when its representation matches the model contract."""
    if not expected.strip():
        raise ValueError("expected preprocessing representation must not be empty")
    if value.representation != expected:
        raise ValueError(
            f"model expects {expected}, received {value.representation}"
        )
    return value.image
