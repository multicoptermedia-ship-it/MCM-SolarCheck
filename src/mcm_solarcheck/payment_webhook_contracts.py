"""Storage-neutral contracts for payment webhook replay protection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WebhookReplayStatus(str, Enum):
    ACQUIRED = "acquired"
    PROCESSING = "processing"
    PROCESSED = "processed"


@dataclass(frozen=True)
class WebhookReplayReservation:
    status: WebhookReplayStatus
    lease_token: str | None = None

    def __post_init__(self) -> None:
        if self.status is WebhookReplayStatus.ACQUIRED:
            if not isinstance(self.lease_token, str) or not self.lease_token.strip():
                raise ValueError("acquired webhook replay lease requires token")
        elif self.lease_token is not None:
            raise ValueError("non-acquired webhook replay state cannot carry token")
