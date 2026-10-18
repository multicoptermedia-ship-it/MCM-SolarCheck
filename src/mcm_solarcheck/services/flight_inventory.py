"""Read-only DJI flight inventory."""
from pathlib import Path
import re

PATTERN = re.compile(r"DJI_([0-9]{14})_([0-9]{4})_([VT])[.](JPG|JPEG|PNG)", re.I)

def scan_flight(folder):
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("local image folder required")
    found = {}
    ignored = []
    for path in root.iterdir():
        match = PATTERN.fullmatch(path.name)
        if path.is_symlink() or not path.is_file() or match is None:
            ignored.append(path.name)
            continue
        stamp, number, kind, _ = match.groups()
        key = stamp + "_" + number
        entry = found.setdefault(key, {})
        kind = kind.upper()
        if kind in entry:
            raise ValueError("duplicate DJI capture modality: " + key)
        entry[kind] = path
    if not found:
        raise ValueError("no DJI captures found")
    return tuple((key, entry.get("V"), entry.get("T"))
                 for key, entry in sorted(found.items())), tuple(sorted(ignored))
