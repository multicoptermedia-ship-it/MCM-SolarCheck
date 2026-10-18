"""Read-only inspection of interrupted nonmetric RGB preview exports.

Never delete, repair or overwrite customer files automatically.
"""
import json

import cv2
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
        if "png" in parts:
            try:
                image = cv2.imread(str(parts["png"]), cv2.IMREAD_UNCHANGED)
                if image is None or image.size == 0:
                    state = "invalid_png"
            except (OSError, ValueError, cv2.error):
                state = "invalid_png"
        if not missing:
            try:
                data = json.loads(parts["json"].read_text(encoding="utf-8"))
                if (data.get("processing_kind") != "nonmetric_rgb_segment_preview"
                        or data.get("metric_orthophoto_verified") is not False):
                    if state == "paired":
                        state = "invalid_quality"
            except (OSError, UnicodeError, ValueError, AttributeError):
                if state == "paired":
                    state = "invalid_quality"
        segments.append({"index": index, "status": state,
                         "missing": missing,
                         "files": sorted(path.name for path in parts.values())})
    summary = directory / "segments_summary.json"
    summary_state = "absent"
    summary_mismatches = []
    if summary.is_symlink():
        raise ValueError("symlink summary is not allowed")
    if summary.exists():
        if not summary.is_file():
            raise ValueError("non-file summary")
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            summary_state = ("present" if isinstance(data, dict) and
                             data.get("processing_kind") == "nonmetric_rgb_flight_segment_previews"
                             else "invalid")
            if summary_state == "present":
                records = data.get("segments")
                if not isinstance(records, list):
                    summary_mismatches.append("invalid_segment_records")
                else:
                    by_index = {item["index"]: item for item in segments}
                    for record in records:
                        if not isinstance(record, dict) or not isinstance(record.get("index"), int):
                            summary_mismatches.append("invalid_record")
                            continue
                        index = record["index"]
                        if record.get("status") == "exported":
                            found = by_index.get(index)
                            if (found is None or found["status"] != "paired"
                                    or record.get("image") != f"segment_{index:04d}.png"
                                    or record.get("quality") != f"segment_{index:04d}.json"):
                                summary_mismatches.append(f"exported_segment_{index:04d}")
                    recorded = {r.get("index") for r in records
                                if isinstance(r, dict) and isinstance(r.get("index"), int)}
                    for index in by_index.keys() - recorded:
                        summary_mismatches.append(f"unlisted_segment_{index:04d}")
        except (OSError, UnicodeError, ValueError, AttributeError):
            summary_state = "invalid"
    issues = sum(item["status"] != "paired" for item in segments)
    issues += len(staging) + (summary_state == "invalid") + len(summary_mismatches)
    return {"segments": segments, "staging_files": sorted(staging),
            "summary": summary_state, "summary_mismatches": sorted(summary_mismatches),
            "issues": issues,
            "requires_manual_review": bool(issues),
            "read_only": True}
