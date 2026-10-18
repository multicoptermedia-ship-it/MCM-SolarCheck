"""Prepare a read-only DJI RGB image list for an external ODM runner.

This adapter never invokes Docker, modifies originals, or claims an orthophoto.
"""
from pathlib import Path
from mcm_solarcheck.services.flight_inventory import scan_flight


def prepare_odm_rgb_inputs(folder, *, max_captures=1000):
    if type(max_captures) is not int or max_captures < 1:
        raise ValueError("invalid capture limit")
    captures, ignored = scan_flight(folder)
    if len(captures) > max_captures:
        raise ValueError("flight exceeds configured capture limit")
    rgb = tuple(path for _, path, _ in captures if path is not None)
    missing = tuple(key for key, path, _ in captures if path is None)
    if not rgb:
        raise ValueError("flight contains no RGB images")
    return {"rgb": rgb, "missing_rgb": missing,
            "capture_count": len(captures), "ignored": ignored}


def stage_odm_rgb_project(folder, project_directory, *, max_captures=1000):
    """Create ODM images/ with source-preserving copies, never resample."""
    import shutil

    manifest = prepare_odm_rgb_inputs(folder, max_captures=max_captures)
    target = Path(project_directory)
    if target.exists() or not target.parent.is_dir() or target.is_symlink():
        raise ValueError("ODM project destination must be new")
    # Validate all source paths before creating the project.
    for source in manifest["rgb"]:
        if source.is_symlink() or not source.is_file():
            raise ValueError("ODM source image must be a regular local file")
    images = target / "images"
    images.mkdir(parents=True, exist_ok=False)
    try:
        for source in manifest["rgb"]:
            with source.open("rb") as input_stream, (images / source.name).open("xb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
    except Exception:
        shutil.rmtree(target)
        raise
    return {"project": target, "images": tuple(images / p.name for p in manifest["rgb"]),
            "missing_rgb": manifest["missing_rgb"], "ignored": manifest["ignored"]}


def odm_command(project_directory, *, split=400, split_overlap=100):
    """Return an argument vector for installed ODM, without executing it.

    ODM split-overlap is measured in meters, not image count.
    """
    if (type(split) is not int or split < 1 or
            type(split_overlap) is not int or split_overlap < 0):
        raise ValueError("invalid ODM split configuration")
    project = Path(project_directory)
    if not project.is_dir() or not (project / "images").is_dir():
        raise ValueError("staged ODM project required")
    return ("docker", "run", "--rm", "-v",
            f"{project.parent.resolve().as_posix()}:/datasets",
            "opendronemap/odm", "--project-path", "/datasets",
            project.name, "--split", str(split),
            "--split-overlap", str(split_overlap))
