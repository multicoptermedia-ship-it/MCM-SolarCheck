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

    def __post_init__(self) -> None:
        database = _resolved(self.state_database)
        reports = _resolved(self.reports_root)
        invoices = _resolved(self.invoices_root)
        web = _resolved(self.web_root) if self.web_root is not None else None

        if reports == invoices or _is_within(reports, invoices) or _is_within(invoices, reports):
            raise ValueError("report and invoice storage must be separate directories")
        if database == reports or database == invoices:
            raise ValueError("state database must not be a document directory")
        if web is not None:
            for private_path in (database, reports, invoices):
                if private_path == web or _is_within(private_path, web):
                    raise ValueError("private SolarCheck storage must be outside web root")

        object.__setattr__(self, "state_database", database)
        object.__setattr__(self, "reports_root", reports)
        object.__setattr__(self, "invoices_root", invoices)
        object.__setattr__(self, "web_root", web)
