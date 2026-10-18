"""Read-only inspection of interrupted nonmetric RGB preview exports.

Never delete, repair or overwrite customer files automatically.
"""
import json
import re
from pathlib import Path

_SEGMENT = re.compile(r"segment_([0-9]{4})\.(png|json)\Z")


def inspect_rgb_export_directory(output_dir):
    """Report missing partners and staging artifacts without modifying anything."""
    directory = Path(output_dir)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("regular RGB output directory required")
    entries = {}
    staging = []
    for path in directory.iterdir():
        if path.is_symlink():
            raise ValueError("symlink in RGB output directory")
        match = _SEGMENT.fullmatch(path.name)
        if match:
            if not path.is_file():
                raise ValueError("non-file RGB output entry")
            entries.setdefault(int(match.group(1)), {})[match.group(2)] = path
        elif path.name.startswith((".rgb-preview-", ".rgb-summary-")) and path.name.endswith(".tmp"):
            staging.append(path.name)
    segments = []
    for index, parts in sorted(entries.items()):
        missing = [ext for ext in ("png", "json") if ext not in parts]
        state = "missing_partner" if missing else "paired"
        if not missing:
            try:
                data = json.loads(parts["json"].read_text(encoding="utf-8"))
                if (data.get("processing_kind") != "nonmetric_rgb_segment_preview"
                        or data.get("metric_orthophoto_verified") is not False):
                    state = "invalid_quality"
            except (OSError, UnicodeError, ValueError, AttributeError):
                state = "invalid_quality"
        segments.append({"index": index, "status": state,
                         "missing": missing,
                         "files": sorted(path.name for path in parts.values())})
    summary = directory / "segments_summary.json"
    summary_state = "absent"
    if summary.is_symlink():
        raise ValueError("symlink summary is not allowed")
    if summary.exists():
        if not summary.is_file():
            raise ValueError("non-file summary")
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            summary_state = ("present" if
                             data.get("processing_kind") == "nonmetric_rgb_flight_segment_previews"
                             else "invalid")
        except (OSError, UnicodeError, ValueError, AttributeError):
            summary_state = "invalid"
    issues = sum(item["status"] != "paired" for item in segments)
    issues += len(staging) + (summary_state == "invalid")
    return {"segments": segments, "staging_files": sorted(staging),
            "summary": summary_state, "issues": issues,
            "requires_manual_review": bool(issues),
            "read_only": True}
