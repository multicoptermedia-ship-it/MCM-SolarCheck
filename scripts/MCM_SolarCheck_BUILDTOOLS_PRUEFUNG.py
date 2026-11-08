"""Standalone MSVC/Windows-SDK smoke check; only synthetic files in a new folder.

Uses existing VS 2022, no downloads/installers, project access or configuration
changes. Raw compiler output stays in the new local probe directory.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile


OUTPUT_ROOT = r"E:\Tools\SolarCheck-BuildCheck"
TOKEN = b"SOLARCHECK_CXX17_SDK_X64_OK"
SOURCE = r"""#include <windows.h>
#include <cstdio>
#include <numeric>
#include <vector>
#ifndef _M_X64
#error x64 compiler required
#endif
static_assert(sizeof(void*) == 8, "x64 required");
static_assert(__cplusplus >= 201703L, "C++17 required");
int main() {
    const std::vector<int> values{19, 23};
    if (!GetCurrentProcessId() ||
        std::accumulate(values.begin(), values.end(), 0) != 42) return 1;
    std::puts("SOLARCHECK_CXX17_SDK_X64_OK");
    return 0;
}
"""


def find_vs2022():
    root = os.environ.get("ProgramFiles(x86)")
    if not root:
        return None
    tool = Path(root) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not tool.is_file():
        return None
    result = subprocess.run(
        [str(tool), "-latest", "-products", "*", "-version", "[17.0,18.0)",
         "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
         "-format", "json", "-utf8"],
        capture_output=True, timeout=15, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        return None
    candidates = json.loads(result.stdout.decode("utf-8-sig"))
    if not candidates or not candidates[0].get("isComplete"):
        return None
    return candidates[0]


def compiler_batch(vcvars):
    # CALL expands its argument twice. Refuse expansion characters rather than
    # attempting to repair arbitrary command syntax in an installation path.
    if any(char in str(vcvars) for char in '%!^"\r\n'):
        raise ValueError("unsupported setup path")
    return (
        '@echo off\r\nsetlocal\r\n'
        f'call "{vcvars}" > activate.log 2>&1\r\n'
        'if errorlevel 1 exit /b 11\r\n'
        'cd /d "%~dp0"\r\n'
        'cl.exe /nologo /std:c++17 /Zc:__cplusplus /EHsc /MT '
        '/Foprobe.obj /Feprobe.exe probe.cpp /link kernel32.lib > build.log 2>&1\r\n'
        'if errorlevel 1 exit /b 12\r\n'
        '.\\probe.exe > run.log 2>&1\r\n'
        'if errorlevel 1 exit /b 13\r\n'
        'exit /b 0\r\n'
    )


def run_batch(work, env):
    system = Path(env["SystemRoot"]) / "System32"
    with (work / "driver.log").open("wb") as output:
        process = subprocess.Popen(
            [str(system / "cmd.exe"), "/d", "/c", "check.cmd"],
            cwd=work, env=env, stdout=output, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            return process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            # Stop only this check's process tree, never all cl/cmd processes.
            try:
                subprocess.run(
                    [str(system / "taskkill.exe"), "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=5, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            return None


def error_codes(work):
    path = work / "build.log"
    if not path.is_file():
        return []
    # Only our own fresh log; never forward paths or raw compiler messages.
    with path.open("rb") as stream:
        stream.seek(0, 2)
        stream.seek(max(0, stream.tell() - 65536))
        data = stream.read(65536)
    return sorted({code.decode("ascii") for code in re.findall(rb"\b(?:C|D|LNK)[0-9]{4}\b", data)})[:12]


def is_x64_executable(path):
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            return False
        stream.seek(0x3C)
        offset = struct.unpack("<I", stream.read(4))[0]
        stream.seek(offset)
        return stream.read(6) == b"PE\0\0\x64\x86"


def check(output_root):
    report = {"check": "solarcheck-msvc-sdk-1", "status": "not_started",
              "installer_started": False, "opensfm": "not_tested"}
    if sys.platform != "win32":
        return {**report, "status": "windows_required"}
    candidate = find_vs2022()
    if candidate is None:
        return {**report, "status": "vs2022_cpp_not_found"}
    vcvars = Path(candidate["installationPath"]) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if not vcvars.is_file():
        return {**report, "status": "vcvars64_missing"}
    try:
        batch = compiler_batch(vcvars)
        batch_bytes = batch.encode("ascii")
    except (ValueError, UnicodeError):
        return {**report, "status": "setup_path_unsupported"}
    version = candidate.get("installationVersion", "")
    if re.fullmatch(r"17(?:\.[0-9]+){1,3}", version):
        report["vs_version"] = version
    base = Path(output_root)
    if not base.is_absolute() or not base.anchor or not Path(base.anchor).exists():
        return {**report, "status": "output_drive_unavailable"}
    # No tempfile default/C: fallback and no overwrites or removal of old runs.
    base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="probe-", dir=base))
    (work / "temp").mkdir()
    (work / "probe.cpp").write_text(SOURCE, encoding="ascii")
    (work / "check.cmd").write_bytes(batch_bytes)
    env = os.environ.copy()
    env.update(TEMP=str(work / "temp"), TMP=str(work / "temp"), VSCMD_SKIP_SENDTELEMETRY="1")
    for name in ("CL", "_CL_", "LINK", "_LINK_"):
        env.pop(name, None)
    code = run_batch(work, env)
    if code is None:
        return {**report, "status": "compiler_timed_out", "limit_seconds": 45}
    if code:
        stage = {11: "compiler_environment", 12: "compile_link", 13: "execute"}.get(code, "command")
        return {**report, "status": "failed", "stage": stage,
                "exit_code": code, "compiler_codes": error_codes(work)}
    if not is_x64_executable(work / "probe.exe") or (work / "run.log").read_bytes().strip() != TOKEN:
        return {**report, "status": "result_invalid"}
    return {**report, "status": "passed", "cpp17_windows_sdk_x64": "passed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=OUTPUT_ROOT)
    args = parser.parse_args()
    print("Compiler-/SDK-Test: nur eigene Testdateien, keine Installation oder Fotos.", flush=True)
    try:
        report = check(args.output_root)
    except subprocess.TimeoutExpired:
        report = {"status": "vswhere_timed_out"}
    except (OSError, ValueError, KeyError, TypeError, struct.error):
        report = {"status": "check_unavailable"}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
