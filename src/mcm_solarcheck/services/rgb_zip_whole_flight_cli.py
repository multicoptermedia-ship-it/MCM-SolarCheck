"""Local read-only six-archive RGB flight run; never export private coordinates.

Example (user-local paths):
python -m mcm_solarcheck.services.rgb_zip_whole_flight_cli \\
  --rgb-archive RGB7.zip --rgb-archive RGB6.zip ... \\
  --calibration-json independent-camera.json --report absolute-local-report.json

The JPEG originals are opened from ZIP members in memory, never extracted.
Only aggregated diagnostic numbers go to JSON/stdout. Explicit opt-in can
write a PRIVATE, unverified RGBA preview PNG to a new local path outside
the checkout and all source archive directories. Never writes ENU/GPS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.rgb_private_multi_plane_preview import (
    PrivateRGBMultiPlaneOrthopreview,
)
from mcm_solarcheck.services.rgb_zip_whole_flight_reconstruction import (
    PrivateRGBFlightStageError, reconstruct_private_complete_rgb_zip_flight,
    render_private_multiplane_preview_from_original_rgb_archives,
)


def _require_private_preview_destination(path: Path, archives: tuple[Path, ...]) -> None:
    """Refuse public-checkout, source-folder, existing, or redirected PNG targets."""
    parent = path.parent
    resolved = parent.resolve()
    checkout = Path(__file__).resolve().parents[3]
    original_dirs = {archive.resolve().parent for archive in archives}
    if (not path.is_absolute() or path.suffix.lower() != ".png"
            or path.is_symlink() or path.exists()
            or not parent.is_dir() or parent.is_symlink()
            or resolved == checkout or checkout in resolved.parents
            or any(resolved == root or root in resolved.parents
                   for root in original_dirs)):
        raise ValueError("new private PNG outside checkout and original archives required")


def _write_private_multiplane_png(
    path: Path, preview: PrivateRGBMultiPlaneOrthopreview,
) -> None:
    """Lossless RGB+alpha; invalid/ambiguous geometry stays transparent black."""
    if (not isinstance(preview, PrivateRGBMultiPlaneOrthopreview)
            or not isinstance(preview.rgb_private, np.ndarray)
            or not isinstance(preview.valid_mask_private, np.ndarray)
            or preview.rgb_private.dtype != np.uint8
            or preview.rgb_private.ndim != 3
            or preview.rgb_private.shape[2] != 3
            or preview.valid_mask_private.dtype != bool
            or preview.valid_mask_private.shape != preview.rgb_private.shape[:2]
            or preview.valid_pixel_count < 1
            or not np.any(preview.valid_mask_private)
            or preview.valid_pixel_count != int(np.count_nonzero(
                preview.valid_mask_private
            ))):
        raise ValueError("private multi-plane preview contains no usable RGB")
    bgra = cv2.cvtColor(preview.rgb_private, cv2.COLOR_RGB2BGRA)
    invalid = ~preview.valid_mask_private
    bgra[invalid, :3] = 0
    bgra[:, :, 3] = np.where(preview.valid_mask_private, 255, 0).astype(np.uint8)
    encoded, buffer = cv2.imencode(".png", bgra)
    if not encoded:
        raise ValueError("private RGB preview PNG could not be encoded")
    try:
        with path.open("xb") as destination:
            destination.write(buffer.tobytes())
    except OSError:
        raise ValueError("private RGB preview PNG could not be written") from None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PRIVATE whole-flight RGB SfM + RTK windowed BA (not an orthophoto)",
    )
    parser.add_argument("--rgb-archive", action="append", required=True,
                        help="local RGB ZIP/.tip path; repeat for all flight archives")
    parser.add_argument("--calibration-json", type=Path, required=True,
                        help="independently verified RGB lens calibration JSON")
    parser.add_argument("--report", type=Path,
                        help="optional NEW absolute local JSON (no GPS/images)")
    parser.add_argument("--max-side", type=int, default=1200)
    parser.add_argument("--max-features", type=int, default=1600)
    parser.add_argument("--expected-frames", type=int, default=160,
                        help="required complete RGB frame count; Hummintech default 160")
    parser.add_argument("--expected-archives", type=int, default=6,
                        help="required private RGB ZIP/.tip count; Hummintech default 6")
    parser.add_argument("--first-counter", type=int, default=1,
                        help="first exact DJI V-JPEG four-digit counter; default 0001")
    parser.add_argument("--private-preview-png", type=Path,
                        help="OPT-IN: NEW local private unverified RGB+alpha PNG; requires --report")
    parser.add_argument("--preview-meters-per-pixel", type=float, default=.05,
                        help="private multi-plane preview grid spacing (0.01..0.50 m)")
    parser.add_argument("--preview-max-side", type=int, default=1024,
                        help="private preview side limit (64..2048 px)")
    args = parser.parse_args(argv)
    archives = tuple(Path(value) for value in args.rgb_archive)
    calibration_file = args.calibration_json
    if (not calibration_file.is_file() or calibration_file.is_symlink()
            or calibration_file.stat().st_size > 1_000_000):
        raise ValueError("existing bounded external calibration file required")
    report_file = args.report
    if report_file is not None:
        if (not report_file.is_absolute() or report_file.is_symlink()
                or report_file.exists() or not report_file.parent.is_dir()
                or report_file.parent.is_symlink()
                or report_file.parent.resolve() in {
                    path.resolve().parent for path in archives
                }):
            raise ValueError("new local report outside every RGB archive folder required")
    preview_file = args.private_preview_png
    if preview_file is not None:
        if report_file is None:
            raise ValueError("--report required with private RGB preview")
        _require_private_preview_destination(preview_file, archives)
    try:
        calibration = json.loads(calibration_file.read_text(encoding="utf-8"))
        outcome = reconstruct_private_complete_rgb_zip_flight(
            archives, calibration,
            max_side=args.max_side, max_features=args.max_features,
            expected_frame_count=args.expected_frames,
            expected_archive_count=args.expected_archives,
            first_counter=args.first_counter,
        )
        result = outcome.privacy_safe_summary()
        status = 0
        if preview_file is not None:
            try:
                preview = render_private_multiplane_preview_from_original_rgb_archives(
                    archives, calibration, outcome.rtk_windowed_ba,
                    meters_per_pixel=args.preview_meters_per_pixel,
                    max_side=args.preview_max_side,
                )
                _write_private_multiplane_png(preview_file, preview)
                result["private_multiplane_preview"] = preview.privacy_safe_summary()
                result["private_preview_png_written"] = True
            except (ValueError, TypeError, RuntimeError, cv2.error):
                # Failure must not be silently reported as a completed RGB preview.
                # Never print exception text: it may contain private paths/positions.
                result["status"] = "whole_flight_rgb_multiplane_preview_failed"
                result["failed_stage"] = "multiplane_preview"
                result["private_preview_png_written"] = False
                status = 2
    except PrivateRGBFlightStageError as failed:
        result = {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_flight_rgb_quality_gate_failed",
            "failed_stage": failed.stage,
            "all_input_rgb_frames_processed": False,
            "roof_geometry_verified": False,
            "rgb_orthophoto_verified": False,
            "module_analysis_verified": False,
            "thermal_registration_verified": False,
        }
        if failed.camera_reprojection_audit is not None:
            # The only permitted failure details are aggregate counts/pixel
            # percentiles produced by the strict post-BA quality audit.
            result["per_camera_reprojection"] = (
                failed.camera_reprojection_audit.privacy_safe_summary()
            )
        if failed.multiview_parallax_audit is not None:
            # Aggregate angular separation, never landmark coordinates/IDs.
            result["multiview_parallax"] = (
                failed.multiview_parallax_audit.privacy_safe_summary()
            )
        status = 2
    except (ValueError, TypeError, json.JSONDecodeError):
        result = {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_flight_rgb_calibration_gate_failed",
            "failed_stage": "calibration",
            "all_input_rgb_frames_processed": False,
            "roof_geometry_verified": False,
            "rgb_orthophoto_verified": False,
            "module_analysis_verified": False,
            "thermal_registration_verified": False,
        }
        status = 2
    if report_file is not None:
        with report_file.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
