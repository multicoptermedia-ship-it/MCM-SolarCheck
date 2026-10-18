"""Read-only, local benchmark reporting without customer file names."""
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions
from mcm_solarcheck.services.flight_rgb_resource_plan import estimate_rgb_conversion_resources


def prepare_rgb_benchmark_report(sources):
    """Return anonymous dimension/size planning report; does not decode JPEGs."""
    frames = []
    for source in sources:
        path = Path(source)
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg"):
            raise ValueError("regular JPEG required")
        width, height = jpeg_dimensions(path)
        frames.append((width, height))
    plan = estimate_rgb_conversion_resources(frames)
    return {"frame_count": len(frames),
            "estimated_working_disk_bytes": plan["estimated_working_disk_bytes"],
            "estimated_peak_ram_bytes": plan["estimated_peak_ram_bytes"],
            "measured_peak_rss_bytes": None,
            "contains_source_paths": False,
            "estimate_only": True}
