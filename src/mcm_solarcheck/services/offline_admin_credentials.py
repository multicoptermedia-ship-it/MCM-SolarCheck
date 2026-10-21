"""Explicit offline administrator bootstrap. No default password or implicit OS user.

The local file contains a salted scrypt verifier, never a plaintext password.
It is distinct from the inspection database and created exclusively. POSIX
owner-only permissions are checked; Windows ACL deployment still needs review.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat

_FILE_NAME = "offline-admin-credentials.json"
_KDF_N = 1 << 14
_KDF_R = 8
_KDF_P = 1


def default_admin_credential_path(database_path: str | Path) -> Path:
    return Path(database_path).absolute().parent / _FILE_NAME


def _actor(value: str) -> str:
    if not isinstance(value, str) or not (1 <= len(value.strip()) <= 120):
        raise ValueError("administrator ID must contain 1-120 characters")
    if any(ord(c) < 32 for c in value):
        raise ValueError("invalid administrator ID")
    return value.strip()


def _password(value: str) -> str:
    if not isinstance(value, str) or not (12 <= len(value) <= 1024):
        raise ValueError("administrator password must contain 12-1024 characters")
    return value


def create_offline_admin_credentials(path: str | Path, actor_id: str, password: str) -> None:
    """Opt-in bootstrap; never overwrite an existing verifier, including links."""
    path = Path(path)
    if not path.is_absolute() or not path.parent.is_dir():
        raise ValueError("absolute credentials path inside an existing directory required")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("credential symlinks are not allowed")
    actor_id = _actor(actor_id)
    password = _password(password)
    salt = secrets.token_bytes(32)
    verifier = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_KDF_N, r=_KDF_R, p=_KDF_P,
        dklen=32,
    )
    data = json.dumps({
        "version": 1, "actor_id": actor_id, "salt": salt.hex(),
        "verifier": verifier.hex(),
    }, separators=(",", ":")).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def verify_offline_admin_credentials(
    path: str | Path, actor_id: str, password: str,
) -> bool:
    """Fail closed on absent, linked, malformed or permission-unsafe verifiers."""
    path = Path(path)
    if not isinstance(actor_id, str) or not isinstance(password, str):
        return False
    try:
        if not path.is_absolute() or any(
            part.is_symlink() for part in (path, *path.parents)
        ):
            return False
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            return False
        if os.name == "posix" and (info.st_mode & 0o077):
            return False
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as file:
            record = json.loads(file.read(4097))
        if record.get("version") != 1 or record.get("actor_id") != actor_id:
            return False
        salt = bytes.fromhex(record["salt"])
        verifier = bytes.fromhex(record["verifier"])
        if len(salt) != 32 or len(verifier) != 32 or len(password) > 1024:
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=_KDF_N, r=_KDF_R, p=_KDF_P,
            dklen=32,
        )
        return hmac.compare_digest(actual, verifier)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, AttributeError):
        return False
