"""Filesystem layout for a server-side SolarCheck Online deployment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class OnlinePrivatePaths:
    """Private server paths; report and invoice files must never be web-served."""

    state_database: Path
    reports_root: Path
    invoices_root: Path
    web_root: Path | None = None
    uploads_root: Path | None = None

    def __post_init__(self) -> None:
        database = _resolved(self.state_database)
        reports = _resolved(self.reports_root)
        invoices = _resolved(self.invoices_root)
        web = _resolved(self.web_root) if self.web_root is not None else None
        uploads = (
            _resolved(self.uploads_root)
            if self.uploads_root is not None
            else reports.parent / "uploads"
        )

        private_roots = (reports, invoices, uploads)
        for index, root in enumerate(private_roots):
            for other in private_roots[index + 1 :]:
                if root == other or _is_within(root, other) or _is_within(other, root):
                    raise ValueError("private storage roots must be separate directories")
        if any(database == root or _is_within(database, root) for root in private_roots):
            raise ValueError("state database must not be inside a private document directory")
        if web is not None:
            for private_path in (database, *private_roots):
                if (
                    private_path == web
                    or _is_within(private_path, web)
                    or _is_within(web, private_path)
                ):
                    raise ValueError("private SolarCheck storage must be outside web root and web root must be separate")

        object.__setattr__(self, "state_database", database)
        object.__setattr__(self, "reports_root", reports)
        object.__setattr__(self, "invoices_root", invoices)
        object.__setattr__(self, "web_root", web)
        object.__setattr__(self, "uploads_root", uploads)
