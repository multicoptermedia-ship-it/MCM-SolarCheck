"""Sequential, fail-closed JPEG working-array batch preparation.

No concurrent decodes, no overwrite, no implicit cleanup or rollback.
"""
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_jpeg_conversion import convert_jpeg_to_rgb_array
from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions
from mcm_solarcheck.services.flight_rgb_resource_plan import estimate_rgb_conversion_resources


def convert_jpeg_batch(sources, output_dir, *, max_total_disk_bytes,
                       max_pixels=12_000_000, max_source_bytes=80_000_000,
                       max_output_bytes=40_000_000):
    """Convert one JPEG at a time after validating the entire manifest and quota."""
    folder = Path(output_dir)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("regular output directory required")
    if type(max_total_disk_bytes) is not int or max_total_disk_bytes < 1:
        raise ValueError("invalid batch disk budget")
    paths = [Path(source) for source in sources]
    if len({str(p.resolve()) for p in paths}) != len(paths):
        raise ValueError("duplicate JPEG sources")
    if len({p.stem.casefold() for p in paths}) != len(paths):
        raise ValueError("colliding JPEG output names")
    destinations = [folder / (p.stem + ".npy") for p in paths]
    if any(target.exists() or target.is_symlink() for target in destinations):
        raise ValueError("batch destination already exists")
    dimensions = []
    for path in paths:
        if (path.is_symlink() or not path.is_file()
                or path.suffix.lower() not in (".jpg", ".jpeg")
                or path.stat().st_size > max_source_bytes):
            raise ValueError("invalid JPEG source")
        size = jpeg_dimensions(path)
        if size[0] * size[1] > max_pixels:
            raise ValueError("JPEG exceeds pixel budget")
        if size[0] * size[1] * 3 + 4096 > max_output_bytes:
            raise ValueError("JPEG exceeds output byte budget")
        dimensions.append(size)
    plan = estimate_rgb_conversion_resources(dimensions)
    if plan["estimated_working_disk_bytes"] > max_total_disk_bytes:
        raise ValueError("batch disk quota exceeded")
    completed = []
    for source, destination in zip(paths, destinations):
        convert_jpeg_to_rgb_array(source, destination, max_pixels=max_pixels,
                                  max_source_bytes=max_source_bytes,
                                  max_output_bytes=max_output_bytes)
        completed.append(destination.name)
    return {"completed_outputs": completed, "resource_plan": plan,
            "sequential": True, "atomic_batch": False}
