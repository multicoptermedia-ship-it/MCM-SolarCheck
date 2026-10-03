"""Server-side session boundary for SolarCheck Online."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

DEFAULT_SESSION_DURATION = timedelta(hours=8)


@dataclass(frozen=True)
class OnlineSession:
    token: str
    user_id: str
    expires_at: datetime


class SessionStore(Protocol):
    def save(self, session: OnlineSession) -> None:
        ...

    def get(self, token: str) -> OnlineSession:
        ...

    def delete(self, token: str) -> None:
        ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, OnlineSession] = {}

    def save(self, session: OnlineSession) -> None:
        self._sessions[session.token] = session

    def get(self, token: str) -> OnlineSession:
        try:
            return self._sessions[token]
        except KeyError as exc:
            raise KeyError(token) from exc

    def delete(self, token: str) -> None:
        self._sessions.pop(token, None)


class OnlineSessionService:
    """Issue and resolve opaque server-side sessions after authentication."""

    def __init__(
        self,
        store: SessionStore,
        *,
        duration: timedelta = DEFAULT_SESSION_DURATION,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if duration <= timedelta(0):
            raise ValueError("session duration must be positive")
        self._store = store
        self._duration = duration
        self._now = now or (lambda: datetime.now(timezone.utc))

    def create(self, user_id: str) -> OnlineSession:
        user_id = self._require_value(user_id, "user identity")
        now = self._utc_now()
        session = OnlineSession(
            token=secrets.token_urlsafe(32),
            user_id=user_id,
            expires_at=now + self._duration,
        )
        self._store.save(session)
        return session

    def require_user(self, token: str) -> str:
        token = self._require_value(token, "session token")
        try:
            session = self._store.get(token)
        except KeyError as exc:
            raise PermissionError("online session is invalid") from exc
        if session.expires_at <= self._utc_now():
            self._store.delete(token)
            raise PermissionError("online session is invalid")
        return session.user_id

    def revoke(self, token: str) -> None:
        token = self._require_value(token, "session token")
        self._store.delete(token)

    def _utc_now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session clock must return timezone-aware UTC")
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("session clock must return UTC")
        return value

    @staticmethod
    def _require_value(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be non-empty")
        return value.strip()
