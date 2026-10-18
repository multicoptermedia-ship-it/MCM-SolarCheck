"""Content-addressed, no-clobber provenance for derived RGB arrays.

Hashes prove byte equality against this local manifest, not authorship or
cryptographic signature. Manifests never include customer file paths.
"""
import hashlib
import json
import os
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_jpeg_header import jpeg_dimensions
from mcm_solarcheck.services.flight_rgb_tile_source import RGBArrayTileSource


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_rgb_provenance_record(source, output):
    source, output = Path(source), Path(output)
    if (source.is_symlink() or output.is_symlink()
            or not source.is_file() or not output.is_file()):
        raise ValueError("regular source and derived array required")
    width, height = jpeg_dimensions(source)
    reader = RGBArrayTileSource(output)
    if (reader.width, reader.height) != (width, height):
        raise ValueError("RGB dimensions do not match JPEG")
    return {"schema": 1, "source_sha256": _sha256(source),
            "output_sha256": _sha256(output), "width": width, "height": height,
            "conversion": "opencv-imdecode-bgr2rgb-npy-v1"}


def write_rgb_provenance_manifest(record, destination):
    destination = Path(destination)
    if (destination.is_symlink() or destination.exists()
            or not destination.parent.is_dir()):
        raise ValueError("new manifest destination required")
    if not isinstance(record, dict) or set(record) != {
        "schema", "source_sha256", "output_sha256", "width", "height", "conversion"
    }:
        raise ValueError("invalid provenance record")
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    with destination.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def verify_rgb_provenance_manifest(source, output, manifest):
    manifest = Path(manifest)
    if manifest.is_symlink() or not manifest.is_file():
        return False
    try:
        record = json.loads(manifest.read_text(encoding="utf-8"))
        return record == build_rgb_provenance_record(source, output)
    except (ValueError, OSError, TypeError, UnicodeError):
        return False
