"""Read-only manifest preflight for safe RGB working-array resumption."""
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions
from mcm_solarcheck.services.flight_rgb_tile_source import RGBArrayTileSource


def inspect_rgb_batch_resume(sources, output_dir, *, max_pixels=12_000_000):
    """Classify existing outputs without deleting, replacing or trusting corrupt arrays."""
    folder = Path(output_dir)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("regular output directory required")
    if type(max_pixels) is not int or max_pixels < 1:
        raise ValueError("invalid pixel budget")
    paths = [Path(source) for source in sources]
    if len({str(p.resolve()) for p in paths}) != len(paths):
        raise ValueError("duplicate source paths")
    if len({p.stem.casefold() for p in paths}) != len(paths):
        raise ValueError("colliding output names")
    records = []
    for source in paths:
        if source.is_symlink() or not source.is_file() or source.suffix.lower() not in (".jpg", ".jpeg"):
            raise ValueError("regular JPEG source required")
        width, height = jpeg_dimensions(source)
        if width * height > max_pixels:
            raise ValueError("JPEG exceeds pixel budget")
        destination = folder / (source.stem + ".npy")
        status = "missing"
        if destination.is_symlink():
            status = "unsafe"
        elif destination.exists():
            try:
                reader = RGBArrayTileSource(destination)
                status = "existing_shape_valid" if (reader.width, reader.height) == (width, height) else "invalid"
            except (ValueError, OSError, TypeError):
                status = "invalid"
        records.append({"source_name": source.name, "output_name": destination.name,
                        "status": status})
    return {"entries": records, "read_only": True,
            "safe_to_resume_automatically": all(r["status"] == "missing" for r in records),
            "existing_outputs_unverified_provenance": any(
                r["status"] == "existing_shape_valid" for r in records)}
