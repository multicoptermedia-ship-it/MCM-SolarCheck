"""Prevent losing automatic Windows native validation on the integration branch.

This is a static regression guard for the checked-in GitHub Actions config.
"""
from pathlib import Path


def test_main_and_prior_development_branch_trigger_windows_validation():
    project_root = Path(__file__).resolve().parents[1]
    config = (project_root / ".github/workflows/windows-offline.yml").read_text(
        encoding="utf-8"
    )
    assert "name: windows-offline-validation" in config
    # Scope to push-trigger block to avoid passing from incidental comments.
    push = config.split("  push:\n", 1)[1].split("  pull_request:", 1)[0]
    assert "    branches:\n" in push
    branches = {
        line.strip()[2:].strip()
        for line in push.splitlines()
        if line.strip().startswith("- ")
    }
    assert {"main", "feature/offline-human-report-approval"} <= branches
    assert "  workflow_dispatch:" in config
    assert "runs-on: windows-2022" in config
