"""Explicit offline administrator bootstrap. No default password or implicit OS user.

The local file contains a salted scrypt verifier, never a plaintext password.
It is distinct from the inspection database and created exclusively. POSIX
owner-only permissions are checked; Windows ACL deployment still needs review.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile

from mcm_solarcheck.services import windows_dpapi
from mcm_solarcheck.services.offline_admin_lock import credential_mutation_lock

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



def _windows_user_protection() -> bool:
    return sys.platform == "win32"


def _encode_credential_record(actor_id: str, salt: bytes, verifier: bytes) -> bytes:
    payload = {
        "version": 1, "actor_id": actor_id,
        "salt": salt.hex(), "verifier": verifier.hex(),
    }
    if _windows_user_protection():
        # Protect the entire verifier plus identity against other Windows users.
        inner = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        protected = windows_dpapi.protect_for_current_user(inner)
        if not 0 < len(protected) <= 3000:
            raise PermissionError("Windows credential protection unavailable")
        payload = {
            "version": 2, "scheme": "dpapi-current-user-scrypt",
            "sealed": base64.b64encode(protected).decode("ascii"),
        }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _decode_credential_record(
    raw: bytes, *, legacy_windows_migration: bool = False,
) -> dict:
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("invalid credential record")
    if _windows_user_protection() and not legacy_windows_migration:
        if set(record) != {"version", "scheme", "sealed"}:
            raise PermissionError("Windows admin credentials require explicit migration")
        if record["version"] != 2 or record["scheme"] != "dpapi-current-user-scrypt":
            raise PermissionError("unsupported protected credential record")
        sealed = base64.b64decode(record["sealed"], validate=True)
        if not 0 < len(sealed) <= 3000:
            raise ValueError("invalid sealed credential")
        record = json.loads(windows_dpapi.unprotect_for_current_user(sealed))
    if (
        not isinstance(record, dict)
        or set(record) != {"version", "actor_id", "salt", "verifier"}
        or record["version"] != 1 or not isinstance(record["actor_id"], str)
        or not isinstance(record["salt"], str) or not isinstance(record["verifier"], str)
        or len(bytes.fromhex(record["salt"])) != 32
        or len(bytes.fromhex(record["verifier"])) != 32
    ):
        raise ValueError("invalid administrator credential record")
    return record


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
    data = _encode_credential_record(actor_id, salt, verifier)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    with credential_mutation_lock(path):
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
        record = _decode_credential_record(_read_trusted_credentials(path))
        if record["actor_id"] != actor_id:
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
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, AttributeError, PermissionError):
        return False


def _read_trusted_credentials(path: Path) -> bytes:
    """Read a small, owner-restricted regular file through one checked descriptor."""
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise PermissionError("administrator credentials unavailable")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as file:
        info = os.fstat(file.fileno())
        if (
            not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 4096
            or (os.name == "posix" and info.st_mode & 0o077)
        ):
            raise PermissionError("administrator credentials unavailable")
        data = file.read(4097)
    if len(data) > 4096:
        raise PermissionError("administrator credentials unavailable")
    return data


def credential_revision(path: str | Path) -> str | None:
    """Internal fingerprint used to revoke sessions after external file changes."""
    try:
        raw = _read_trusted_credentials(Path(path))
        _decode_credential_record(raw)
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, PermissionError, AttributeError):
        return None


def _rotate_unlocked(
    path: str | Path, actor_id: str, current_password: str, new_password: str,
) -> None:
    """Replace credentials atomically only after proving the previous password.

    The old file remains in place on write/validation failures. No backup with
    plaintext, no implicit reset, no change of admin identity or permissions.
    """
    path = Path(path)
    if not isinstance(actor_id, str) or not isinstance(current_password, str):
        raise PermissionError("administrator reauthentication required")
    new_password = _password(new_password)
    if new_password == current_password:
        raise ValueError("new administrator password must differ")
    try:
        original = _read_trusted_credentials(path)
        record = _decode_credential_record(original)
        if record["actor_id"] != actor_id:
            raise PermissionError("administrator reauthentication required")
        salt = bytes.fromhex(record["salt"])
        old = bytes.fromhex(record["verifier"])
        if len(salt) != 32 or len(old) != 32:
            raise PermissionError("administrator reauthentication required")
        calculated = hashlib.scrypt(
            current_password.encode("utf-8"), salt=salt, n=_KDF_N,
            r=_KDF_R, p=_KDF_P, dklen=32,
        )
        if not hmac.compare_digest(calculated, old):
            raise PermissionError("administrator reauthentication required")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, AttributeError) as exc:
        raise PermissionError("administrator reauthentication required") from exc

    salt_new = secrets.token_bytes(32)
    verifier_new = hashlib.scrypt(
        new_password.encode("utf-8"), salt=salt_new, n=_KDF_N,
        r=_KDF_R, p=_KDF_P, dklen=32,
    )
    encoded = _encode_credential_record(actor_id, salt_new, verifier_new)
    _atomic_replace_credentials(path, original, encoded)

def _atomic_replace_credentials(path: Path, original: bytes, encoded: bytes) -> None:
    """Called with stable per-credential mutation lock already held."""
    fd, temporary = tempfile.mkstemp(prefix=".offline-admin-rotate-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if _read_trusted_credentials(path) != original:
            raise PermissionError("administrator credentials changed concurrently")
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass  # Directory fsync not supported on all Windows filesystems.
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def rotate_offline_admin_password(
    path: str | Path, actor_id: str, current_password: str, new_password: str,
) -> None:
    """Serialize password changes across cooperating local processes."""
    with credential_mutation_lock(Path(path)):
        _rotate_unlocked(path, actor_id, current_password, new_password)


def migrate_legacy_windows_admin_credentials(
    path: str | Path, actor_id: str, current_password: str,
) -> None:
    """Explicit one-way migration of the v1 Windows verifier to DPAPI v2.

    Never migrates silently, never overwrites existing DPAPI records. The old
    password is required and remains unchanged. No plaintext password is stored.
    """
    if not _windows_user_protection():
        raise OSError("legacy Windows credential migration requires Windows")
    if not isinstance(actor_id, str) or not isinstance(current_password, str):
        raise PermissionError("administrator reauthentication required")
    path = Path(path)
    with credential_mutation_lock(path):
        try:
            original = _read_trusted_credentials(path)
            record = _decode_credential_record(
                original, legacy_windows_migration=True,
            )
            if record["actor_id"] != actor_id:
                raise PermissionError("administrator reauthentication required")
            salt = bytes.fromhex(record["salt"])
            verifier = bytes.fromhex(record["verifier"])
            actual = hashlib.scrypt(
                current_password.encode("utf-8"), salt=salt,
                n=_KDF_N, r=_KDF_R, p=_KDF_P, dklen=32,
            )
            if not hmac.compare_digest(actual, verifier):
                raise PermissionError("administrator reauthentication required")
        except (OSError, TypeError, KeyError, ValueError, UnicodeError) as exc:
            raise PermissionError("administrator reauthentication required") from exc
        protected = _encode_credential_record(actor_id, salt, verifier)
        _atomic_replace_credentials(path, original, protected)
