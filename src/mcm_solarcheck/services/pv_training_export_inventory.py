"""Local-only inventory to track exported training crops for withdrawal review."""
from pathlib import Path
import hashlib
import sqlite3
import uuid


class TrainingExportInventory:
    def __init__(self, database: Path, root: Path):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("export root must be a directory")
        self.database = Path(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS training_export_inventory "
                "(filename TEXT PRIMARY KEY, project_key TEXT NOT NULL, "
                "sha256 TEXT NOT NULL, status TEXT NOT NULL)"
            )

    def _path(self, filename: str) -> Path:
        if not filename.endswith(".png"):
            raise ValueError("expected PNG filename")
        try:
            uuid.UUID(filename[:-4])
        except ValueError as exc:
            raise ValueError("expected UUID filename") from exc
        if "/" in filename or "\\" in filename:
            raise ValueError("invalid filename")
        path = self.root / filename
        if path.is_symlink():
            raise ValueError("symlink not permitted")
        return path

    def register(self, project_key: str, filename: str) -> None:
        if not project_key.strip():
            raise ValueError("project key required")
        digest = hashlib.sha256(self._path(filename).read_bytes()).hexdigest()
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO training_export_inventory VALUES (?, ?, ?, 'active')",
                (filename, project_key, digest),
            )

    def withdraw(self, project_key: str) -> dict[str, int]:
        deleted = changed = 0
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT filename, sha256 FROM training_export_inventory "
                "WHERE project_key=? AND status='active'", (project_key,)
            ).fetchall()
            for filename, digest in rows:
                path = self._path(filename)
                if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    connection.execute(
                        "UPDATE training_export_inventory SET status='changed' WHERE filename=?",
                        (filename,),
                    )
                    changed += 1
                    continue
                if path.exists():
                    path.unlink()
                connection.execute(
                    "UPDATE training_export_inventory SET status='deleted' WHERE filename=?",
                    (filename,),
                )
                deleted += 1
        return {"deleted_or_missing": deleted, "changed_requires_review": changed}
