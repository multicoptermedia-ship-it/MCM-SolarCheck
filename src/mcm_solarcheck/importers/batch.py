"""Batch import support for M3T thermal datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .m3t import M3TImportResult, M3TImporter


@dataclass(frozen=True)
class M3TBatchSummary:
    total_files: int
    imported: int
    failed: int
    pass_count: int
    review_count: int
    reject_count: int
    finding_count: int


@dataclass(frozen=True)
class M3TBatchFailure:
    source_file: Path
    error_type: str
    message: str


@dataclass(frozen=True)
class M3TBatchResult:
    results: tuple[M3TImportResult, ...]
    failures: tuple[M3TBatchFailure, ...]
    summary: M3TBatchSummary


def import_m3t_directory(
    directory: str | Path,
    *,
    importer: M3TImporter | None = None,
    candidate_percentile: float = 99.9,
    candidate_limit: int = 100,
) -> M3TBatchResult:
    """Import all DJI ``*_T.JPG`` files in deterministic filename order."""
    root = Path(directory)
    files = tuple(sorted(root.glob("*_T.JPG")))
    worker = importer or M3TImporter()
    results: list[M3TImportResult] = []
    failures: list[M3TBatchFailure] = []

    for path in files:
        try:
            results.append(
                worker.import_file(
                    path,
                    candidate_percentile=candidate_percentile,
                    candidate_limit=candidate_limit,
                )
            )
        except Exception as exc:  # batch boundary: preserve remaining evidence
            failures.append(M3TBatchFailure(path, type(exc).__name__, str(exc)))

    grades = [result.quality.grade.value for result in results]
    summary = M3TBatchSummary(
        total_files=len(files),
        imported=len(results),
        failed=len(failures),
        pass_count=grades.count("pass"),
        review_count=grades.count("review"),
        reject_count=grades.count("reject"),
        finding_count=sum(len(result.findings) for result in results),
    )
    return M3TBatchResult(tuple(results), tuple(failures), summary)
