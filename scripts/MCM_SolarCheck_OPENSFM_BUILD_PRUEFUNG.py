"""Exercise installed OpenSfM extensions using constants, never a dataset."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys


def check():
    result = {"check": "solarcheck-opensfm-build-1", "status": "not_started",
              "dataset": "not_tested", "gpu_execution": "not_tested"}
    if not sys.flags.isolated:
        return {**result, "status": "requires_isolated_python_flag"}
    prefix = Path(sys.prefix).resolve()
    extensions = {}
    for name in ("pybundle", "pydense", "pyfeatures", "pygeo", "pygeometry",
                 "pymap", "pypointcloud", "pyrobust", "pysfm"):
        module = importlib.import_module("opensfm." + name)
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            return {**result, "status": "outside_isolated_prefix", "module": name}
        extensions[name] = module
    # Fixed public mathematical constants, no GPS from an image/project.
    ecef = extensions["pygeo"].ecef_from_lla(0.0, 0.0, 0.0)
    if max(abs(float(a) - b) for a, b in zip(ecef, (6378137.0, 0.0, 0.0))) > 1e-6:
        return {**result, "status": "native_constant_check_failed"}
    # Import the actual command registry used by upstream's CLI. This also
    # covers Python/native linking beyond an empty top-level package import.
    commands = importlib.import_module("opensfm.commands")
    names = {item.Command.name for item in commands.opensfm_commands}
    required = {"extract_metadata", "detect_features", "match_features",
                "reconstruct", "undistort", "dense_clustering",
                "compute_depthmaps", "fuse_depthmaps", "dense_merging"}
    if not required.issubset(names):
        return {**result, "status": "command_registry_incomplete"}
    return {**result, "status": "passed", "native_modules": len(extensions),
            "native_constant_check": "passed", "command_registry": "available"}


if __name__ == "__main__":
    try:
        report = check()
    except Exception as error:
        report = {"check": "solarcheck-opensfm-build-1", "status": "check_failed",
                  "error_type": type(error).__name__, "dataset": "not_tested",
                  "gpu_execution": "not_tested"}
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)
