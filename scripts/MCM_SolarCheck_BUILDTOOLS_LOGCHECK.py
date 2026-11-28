"""Read a bounded tail of recent VS setup logs; emit codes, never raw log text.

Standard library only. Does not launch installers, search photo folders, modify
the registry, remove caches, or create output files.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time


MAX_BYTES = 256 * 1024
MAX_AGE_SECONDS = 24 * 60 * 60
LOG_KINDS = ("bootstrapper", "installer", "setup")
HEX = re.compile(r"\b0x[0-9a-f]{8}\b", re.IGNORECASE)
EXIT = re.compile(
    r"\b(?:exit\s*code|return\s*code|final\s*result|result\s*code)"
    r"\s*(?:[:=]|is|of|was)?\s*(-?\d+)\b", re.IGNORECASE
)
ERROR = re.compile(r"\b(?:error|failed|failure|fatal|exception)\b", re.IGNORECASE)
RESULT = re.compile(r"\b(?:hresult|exit\s*code|return\s*code|final\s*result|result\s*code)\b", re.IGNORECASE)


def distinct_tail(values):
    return list(dict.fromkeys(values))[-16:]


def extract_codes(text):
    error_codes, result_codes, exit_codes = [], [], []
    errors_without_code = 0
    for line in text.splitlines():
        codes = ["0x" + match[2:].upper() for match in HEX.findall(line)]
        is_error = bool(ERROR.search(line))
        if is_error:
            error_codes.extend(codes)
            errors_without_code += not bool(codes or EXIT.search(line))
        if RESULT.search(line):
            result_codes.extend(codes)
        exit_codes.extend(int(match) for match in EXIT.findall(line))
    return {
        "error_hex_codes": distinct_tail(error_codes),
        "result_hex_codes": distinct_tail(result_codes),
        "exit_codes": distinct_tail(exit_codes),
        "error_lines_without_code": errors_without_code,
    }


def read_codes(path):
    with path.open("rb") as stream:
        prefix = stream.read(4)
        stream.seek(0, 2)
        size = stream.tell()
        offset = max(0, size - MAX_BYTES)
        encoding = "utf-8-sig"
        if prefix.startswith(b"\xff\xfe"):
            encoding = "utf-16-le"
            offset -= offset % 2
        elif prefix.startswith(b"\xfe\xff"):
            encoding = "utf-16-be"
            offset -= offset % 2
        stream.seek(offset)
        text = stream.read(MAX_BYTES + 2).decode(encoding, "replace")
    if offset:
        # A tail can begin inside a line: do not interpret a partial field.
        text = text.partition("\n")[2]
    return {"read_status": "read", "tail_only": bool(offset), **extract_codes(text)}


def scan(roots, now=None):
    now = time.time() if now is None else now
    results = []
    for kind in LOG_KINDS:
        candidates = {}
        for root in roots:
            try:
                for path in root.glob(f"dd_{kind}_*.log"):
                    try:
                        if path.is_symlink() or not path.is_file():
                            continue
                        modified = path.stat().st_mtime
                        if -300 <= now - modified <= MAX_AGE_SECONDS:
                            candidates[path] = modified
                    except OSError:
                        continue
            except OSError:
                continue
        for path, modified in sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:2]:
            row = {"kind": kind, "age_minutes": round(max(0, now - modified) / 60, 1)}
            try:
                row.update(read_codes(path))
            except OSError:
                row["read_status"] = "unreadable"
            results.append(row)
    return {
        "check": "solarcheck-buildtools-logcodes-1",
        "status": "logs_found" if results else "no_recent_setup_logs",
        "installer_started_by_this_check": False,
        "logs": results,
        "note": "Codes are log evidence; no installation success or root cause inferred.",
    }


def main():
    print("Buildtools-Pruefung: nur vorhandene Setup-Protokolle, kein Installerstart.", flush=True)
    if sys.platform != "win32":
        report = {"status": "windows_required"}
    else:
        # Do not use tempfile.gettempdir(): it probes writability by creating a
        # temporary file. This check reads only existing configured locations.
        temp = os.environ.get("TEMP") or os.environ.get("TMP")
        roots = [Path(os.path.expandvars(temp))] if temp else []
        windows = os.environ.get("SystemRoot")
        if windows:
            system_temp = Path(windows) / "Temp"
            if system_temp not in roots:
                roots.append(system_temp)
        try:
            report = scan(roots)
        except OSError:
            report = {"status": "setup_logs_unavailable"}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
