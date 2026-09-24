"""Training-corpus intake policy for M3T imagery.

Imported imagery can be indexed automatically, but it is not a trusted training
label until human review and data-rights checks have passed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256


@dataclass(frozen=True)
class TrainingSample:
    sample_id: str
    source_frame_id: str
    source_file: str
    modality: str
    content_sha256: str
    label_status: str = "unlabeled"
    rights_status: str = "unverified"

    @property
    def trainable(self) -> bool:
        return self.label_status == "human_reviewed" and self.rights_status == "approved"


def index_m3t_training_sample(frame_id: str, source_file: str | Path, modality: str) -> TrainingSample:
    """Index a new M3T image deterministically without inventing a label."""
    if modality not in {"thermal", "rgb"}:
        raise ValueError("training modality must be thermal or rgb")
    if not frame_id.strip():
        raise ValueError("source frame id must not be empty")
    path=Path(source_file)
    if not path.is_file():
        raise ValueError("training source file does not exist")
    digest=sha256(path.read_bytes()).hexdigest()
    return TrainingSample(
        sample_id=f"{modality}:{digest}",
        source_frame_id=frame_id,
        source_file=str(path),
        modality=modality,
        content_sha256=digest,
    )
