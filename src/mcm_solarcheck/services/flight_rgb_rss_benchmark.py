"""Optional isolated JPEG conversion peak-RSS benchmark.

Run manually on a representative machine:
python -m mcm_solarcheck.services.flight_rgb_rss_benchmark input.jpg output.npy

Uses resource.ru_maxrss on Linux/macOS, or psutil when installed on Windows.
The measured maximum is for this fresh subprocess, not a strict memory cap.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def _peak_rss_bytes():
    if sys.platform == "win32":
        try:
            import psutil
        except ImportError as exc:
            raise RuntimeError("Windows RSS measurement requires psutil") from exc
        return psutil.Process().memory_info().peak_wset
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def benchmark_jpeg_conversion(source, destination):
    """Run the converter in a fresh process to isolate the peak RSS."""
    command = [sys.executable, "-m",
               "mcm_solarcheck.services.flight_rgb_rss_benchmark",
               "--worker", str(Path(source)), str(Path(destination))]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def _worker(source, destination):
    from mcm_solarcheck.services.flight_rgb_jpeg_conversion import convert_jpeg_to_rgb_array
    convert_jpeg_to_rgb_array(source, destination)
    return {"peak_rss_bytes": _peak_rss_bytes(), "measured": True,
            "platform": sys.platform, "isolated_subprocess": True}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: python -m mcm_solarcheck.services.flight_rgb_rss_benchmark [--worker] source.jpg output.npy")
    if sys.argv[1] == "--worker":
        print(json.dumps(_worker(sys.argv[2], sys.argv[3])))
    else:
        print(json.dumps(benchmark_jpeg_conversion(sys.argv[1], sys.argv[2])))
