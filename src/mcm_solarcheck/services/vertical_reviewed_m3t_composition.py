"""Opt-in M3T importer-to-reviewed-evidence integration.

A caller must supply an actual expert review record; no automated approval.
"""
from __future__ import annotations

from typing import Callable

from mcm_solarcheck.importers.project import import_m3t_project
from mcm_solarcheck.services.vertical_m3t_composition import build_m3t_vertical_pipeline
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import analyze_imported_m3t_candidates
from mcm_solarcheck.services.vertical_expert_review import ExpertReviewRecord, review_imported_candidates
from mcm_solarcheck.services.vertical_reviewed_manifest import build_reviewed_evidence_manifest


def build_reviewed_m3t_evidence_pipeline(
    *,
    project_authorized: Callable[[str, str], bool],
    review_record_for_analysis: Callable[[object], ExpertReviewRecord],
    import_project=import_m3t_project,
):
    """Wire existing importer candidates to human decisions and an evidence manifest.

    This does not activate online processing or export a customer report.
    """
    if not callable(review_record_for_analysis):
        raise TypeError("explicit review provider required")

    def review(analysis):
        record = review_record_for_analysis(analysis)
        return review_imported_candidates(analysis, record)

    return build_m3t_vertical_pipeline(
        project_authorized=project_authorized,
        analyze_project=analyze_imported_m3t_candidates,
        review_findings=review,
        build_report=build_reviewed_evidence_manifest,
        import_project=import_project,
    )
