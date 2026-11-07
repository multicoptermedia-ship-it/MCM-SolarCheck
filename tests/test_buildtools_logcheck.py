import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "MCM_SolarCheck_BUILDTOOLS_LOGCHECK.py"
spec = importlib.util.spec_from_file_location("buildtools_logcheck", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_only_error_and_exit_codes_are_exposed():
    text = """Info download https://example.invalid/private-token 0xDEADBEEF
Error 0x80070070 at C:\\Users\\PRIVATE\\Customer\\secret.jpg
Final Result: 0x80131500
ExitCode = 5005
Return code: -1073741510
Failure without a code: customer-secret GPS=51.123,7.456
"""
    result = check.extract_codes(text)
    assert result == {
        "error_hex_codes": ["0x80070070"], "result_hex_codes": ["0x80131500"],
        "exit_codes": [5005, -1073741510], "error_lines_without_code": 1,
    }
    serialized = json.dumps(result)
    for private in ("PRIVATE", "Customer", "secret", "51.123", "example.invalid"):
        assert private not in serialized


def test_hex_result_does_not_become_decimal_zero():
    result = check.extract_codes("ExitCode: 0x80131500\nExit code: 0\nExit code: 3010")
    assert result["exit_codes"] == [0, 3010]
    assert result["result_hex_codes"] == ["0x80131500"]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-16-be"])
def test_bounded_tail_handles_encodings(tmp_path, encoding):
    path = tmp_path / "dd_setup_20261107.log"
    data = ("Info private old message\n" * 30000 + "Error 0x80070057 private-path\nExit code: 5005\n").encode(encoding)
    if encoding == "utf-16-be":
        data = b"\xfe\xff" + data
    path.write_bytes(data)
    result = check.read_codes(path)
    assert result["tail_only"]
    assert result["error_hex_codes"] == ["0x80070057"]
    assert result["exit_codes"] == [5005]
    assert "private" not in json.dumps(result)


def test_scan_ignores_old_unrelated_and_nested_files(tmp_path):
    now = 1000000
    for name, age in (("dd_setup_recent.log", 60), ("dd_setup_old.log", 90000),
                      ("customer.log", 0), ("photo.jpg", 0)):
        path = tmp_path / name
        path.write_text("Error 0x80070070")
        os.utime(path, (now - age, now - age))
    nested = tmp_path / "customer-folder"
    nested.mkdir()
    (nested / "dd_setup_nested.log").write_text("Error 0xDEADBEEF")
    result = check.scan([tmp_path], now)
    assert len(result["logs"]) == 1
    assert result["logs"][0]["age_minutes"] == 1
    assert result["logs"][0]["error_hex_codes"] == ["0x80070070"]
    assert not result["installer_started_by_this_check"]
    assert "customer" not in json.dumps(result)


def test_at_most_two_newest_logs_per_kind_and_no_paths(tmp_path):
    now = 1000000
    for index in range(5):
        path = tmp_path / f"dd_bootstrapper_private-{index}.log"
        path.write_text(f"ExitCode: {5000 + index}")
        os.utime(path, (now - index * 60, now - index * 60))
    result = check.scan([tmp_path, tmp_path], now)
    assert [row["exit_codes"] for row in result["logs"]] == [[5000], [5001]]
    assert "private" not in json.dumps(result) and str(tmp_path) not in json.dumps(result)


def test_symlink_is_not_read(tmp_path):
    original = tmp_path / "customer.txt"
    original.write_text("Error 0xDEADBEEF")
    link = tmp_path / "dd_setup_link.log"
    try:
        link.symlink_to(original)
    except OSError:
        pytest.skip("Symlink creation unavailable for current Windows account")
    assert check.scan([tmp_path])["status"] == "no_recent_setup_logs"


def test_read_failure_does_not_disclose_exception_path(tmp_path, monkeypatch):
    (tmp_path / "dd_installer_recent.log").write_text("private")

    def fail(path):
        raise PermissionError("C:\\private-user\\private-customer")

    monkeypatch.setattr(check, "read_codes", fail)
    result = check.scan([tmp_path])
    assert result["logs"][0]["read_status"] == "unreadable"
    assert "private" not in json.dumps(result)


def test_empty_scan_is_explicit_and_does_not_infer_installation(tmp_path):
    result = check.scan([tmp_path])
    assert result["status"] == "no_recent_setup_logs"
    assert result["logs"] == []
    assert "success" not in result


def test_main_always_prints_even_when_no_log_is_found(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(check.sys, "platform", "win32")
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.delenv("SystemRoot", raising=False)
    assert check.main() == 0
    output = capsys.readouterr().out
    assert "kein Installerstart" in output and '"status": "no_recent_setup_logs"' in output


@pytest.mark.skipif(sys.platform == "win32", reason="Linux standalone check must not read native host logs")
def test_standalone_has_no_solarcheck_package_dependency():
    result = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, timeout=10)
    assert result.returncode == 0
    assert b'"status": "windows_required"' in result.stdout
