"""Sequential, bounded exports for every registered RGB segment of one DJI flight."""
import json
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_folder_preview import export_flight_rgb_segment


def export_all_flight_rgb_segments(folder, registration, output_dir, *,
                                   max_side=800, max_frames=8,
                                   max_image_bytes=80_000_000,
                                   max_pixels=12_000_000,
                                   on_progress=None, should_cancel=None):
    """Export each segment independently, recording failures without modifying inputs.

    The output directory must exist and be empty. Each segment is decoded and
    rendered independently, so full-flight RGB arrays are never retained.
    """
    target = Path(output_dir)
    if not target.is_dir() or target.is_symlink() or any(target.iterdir()):
        raise ValueError("an empty regular RGB output directory is required")
    segments = registration["nonmetric_geometry"]["segments"]
    if not isinstance(segments, (list, tuple)):
        raise ValueError("invalid RGB segments")
    records = []
    total = len(segments)
    for index in range(total):
        if should_cancel is not None and should_cancel():
            break
        stem = f"segment_{index:04d}"
        png = target / f"{stem}.png"
        quality = target / f"{stem}.json"
        try:
            metadata = export_flight_rgb_segment(
                folder, registration, index, png, quality,
                max_side=max_side, max_frames=max_frames,
                max_image_bytes=max_image_bytes, max_pixels=max_pixels,
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            record = {"index": index, "status": "failed",
                      "reason": str(exc)}
        else:
            record = {"index": index, "status": "exported",
                      "image": png.name, "quality": quality.name,
                      "nonmetric": metadata["nonmetric"]}
        records.append(record)
        if on_progress is not None:
            on_progress(len(records), total, record)
    return {
        "schema_version": 1,
        "processing_kind": "nonmetric_rgb_flight_segment_previews",
        "segment_count": total,
        "processed": len(records),
        "exported": sum(item["status"] == "exported" for item in records),
        "failed": sum(item["status"] == "failed" for item in records),
        "cancelled": len(records) < total,
        "metric_orthophoto_verified": False,
        "full_resolution_sources_modified": False,
        "temperature_calibrated": False,
        "segments": records,
    }


def save_all_flight_rgb_segments(folder, registration, output_dir, **options):
    """Write a summary after completing or cancelling the sequential export."""
    output_dir = Path(output_dir)
    result = export_all_flight_rgb_segments(folder, registration, output_dir, **options)
    summary = output_dir / "segments_summary.json"
    with summary.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result
