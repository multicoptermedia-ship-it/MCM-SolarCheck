"""Check only the isolated OpenSfM dependency environment, not an engine/dataset."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import platform
import struct
import sys


MODULES = (
    "numpy", "scipy", "cv2", "osgeo.gdal", "pyproj", "igraph", "leidenalg",
    "rerun", "cloudpickle", "exifread", "flask", "fpdf", "joblib", "lz4",
    "matplotlib", "networkx", "PIL", "dateutil", "yaml", "xmltodict",
    "scikit_build_core", "pybind11",
)


def check():
    result = {"check": "solarcheck-opensfm-env-1", "status": "not_started",
              "opensfm": "not_built", "python": platform.python_version()}
    if sys.platform != "win32" or sys.version_info[:2] != (3, 10) or struct.calcsize("P") != 8:
        return {**result, "status": "requires_windows_python310_x64"}
    if not sys.flags.isolated:
        return {**result, "status": "requires_isolated_python_flag"}
    # Keep this check's matplotlib cache under the explicitly configured E:
    # work area (or the CI job's own disposable area), never a profile fallback.
    cache = os.environ.get("MPLCONFIGDIR")
    if not cache or not Path(cache).is_absolute():
        return {**result, "status": "matplotlib_cache_not_configured"}
    os.environ["PROJ_NETWORK"] = "OFF"
    modules = {}
    failures = {}
    prefix = Path(sys.prefix).resolve()
    for name in MODULES:
        try:
            module = importlib.import_module(name)
            location = getattr(module, "__file__", None)
            if not location or not Path(location).resolve().is_relative_to(prefix):
                failures[name] = "outside_isolated_prefix"
            else:
                modules[name] = module
        except Exception as error:
            # No raw DLL errors or paths from the local computer in the report.
            failures[name] = type(error).__name__
    if failures:
        return {**result, "status": "import_failed", "failures": failures}
    gdal = modules["osgeo.gdal"]
    proj = modules["pyproj"]
    proj.network.set_network_enabled(False)
    if gdal.GetDriverByName("GTiff") is None:
        return {**result, "status": "geotiff_driver_missing"}
    return {
        **result, "status": "passed", "modules_from_isolated_prefix": len(modules),
        "opencv": modules["cv2"].__version__, "numpy": modules["numpy"].__version__,
        "gdal": gdal.VersionInfo("RELEASE_NAME"), "pyproj": proj.__version__,
        "igraph": modules["igraph"].__version__, "geotiff_driver": "available",
        "proj_network": "disabled",
    }


if __name__ == "__main__":
    print("OpenSfM-Abhaengigkeiten: isolierte Umgebung, keine Fotos oder Engine-Rekonstruktion.", flush=True)
    try:
        report = check()
    except Exception as error:
        report = {"check": "solarcheck-opensfm-env-1", "status": "check_failed",
                  "error_type": type(error).__name__, "opensfm": "not_built"}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    raise SystemExit(0 if report["status"] == "passed" else 1)
