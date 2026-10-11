"""Explicit, local extraction of selected DJI M3T ZIP pairs."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from mcm_solarcheck.importers.m3t_pair_selection import MatchedM3TSelection, select_m3t_pairs


def stage_m3t_pairs(
    thermal_zip: str | Path,
    rgb_zip: str | Path,
    destination: str | Path,
    *,
    count: int = 29,
    max_member_bytes: int = 32_000_000,
) -> MatchedM3TSelection:
    """Stage only selected files in an existing empty directory; never overwrite."""
    selection = select_m3t_pairs(thermal_zip, rgb_zip, count=count)
    root = Path(destination)
    if not root.is_dir() or any(root.iterdir()):
        raise ValueError("destination must be an existing empty directory")
    staged: list[Path] = []
    try:
        for path, names in ((thermal_zip, selection.thermal_names), (rgb_zip, selection.rgb_names)):
            with ZipFile(path) as archive:
                for name in names:
                    info = archive.getinfo(name)
                    if info.file_size > max_member_bytes:
                        raise ValueError("image exceeds safe extraction limit")
                    target = root / name
                    with archive.open(info) as source, target.open("xb") as output:
                        staged.append(target)
                        remaining = max_member_bytes + 1
                        while remaining > 0:
                            chunk = source.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            output.write(chunk)
                            remaining -= len(chunk)
                        if remaining == 0 and source.read(1):
                            raise ValueError("image exceeds safe extraction limit")
        return selection
    except Exception:
        for target in staged:
            target.unlink(missing_ok=True)
        raise
