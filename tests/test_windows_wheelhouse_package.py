"""Offline wheel inventory + pip no-index integration (no real PV data)."""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from mcm_solarcheck.offline.wheelhouse import create_manifest, verify_manifest


def _make_wheel(destination: Path) -> None:
    name = "mcm_wheelprobe-0.1.0-py3-none-any.whl"
    wheel = destination / name
    files = {
        "mcm_wheelprobe/__init__.py": b"VALUE = 'offline-only'\n",
        "mcm_wheelprobe-0.1.0.dist-info/METADATA": (
            b"Metadata-Version: 2.1\nName: mcm-wheelprobe\nVersion: 0.1.0\n"
        ),
        "mcm_wheelprobe-0.1.0.dist-info/WHEEL": (
            b"Wheel-Version: 1.0\nGenerator: mcm-solarcheck-tests\n"
            b"Root-Is-Purelib: true\nTag: py3-none-any\n"
        ),
    }
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for item, content in files.items():
        writer.writerow([item, "", ""])
    writer.writerow(["mcm_wheelprobe-0.1.0.dist-info/RECORD", "", ""])
    files["mcm_wheelprobe-0.1.0.dist-info/RECORD"] = output.getvalue().encode()
    with zipfile.ZipFile(wheel, "w") as archive:
        for item, content in files.items():
            archive.writestr(item, content)


def test_preverified_wheel_installs_with_no_index_and_no_network(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("mcm-wheelprobe==0.1.0\n", encoding="utf-8")
    _make_wheel(wheelhouse)
    create_manifest(wheelhouse, requirements)
    assert verify_manifest(wheelhouse, requirements) == 1

    destination = tmp_path / "installed"
    env = dict(os.environ)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["PIP_INDEX_URL"] = "http://127.0.0.1:9/must-not-contact"
    result = subprocess.run(
        [
            sys.executable, "-m", "pip", "--isolated", "install",
            "--disable-pip-version-check", "--no-index", "--no-deps",
            "--only-binary=:all:", "--no-cache-dir",
            "--find-links", str(wheelhouse), "--target", str(destination),
            "--requirement", str(requirements),
        ],
        env=env, text=True, capture_output=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (destination / "mcm_wheelprobe" / "__init__.py").read_text().strip() == (
        "VALUE = 'offline-only'"
    )
    assert not (tmp_path / "solarcheck.sqlite3").exists()


def test_corrupted_wheel_is_stopped_before_pip_install(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("mcm-wheelprobe==0.1.0\n", encoding="utf-8")
    _make_wheel(wheelhouse)
    create_manifest(wheelhouse, requirements)
    wheel = next(wheelhouse.glob("*.whl"))
    with wheel.open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        verify_manifest(wheelhouse, requirements)


def test_windows_offline_powershell_scripts_parse_without_execution():
    if sys.platform != "win32":
        pytest.skip("Windows PowerShell parser available only on native Windows")
    root = Path(__file__).resolve().parents[1]
    scripts = [
        "prepare_windows10_wheelhouse.ps1", "install_windows10_offline_venv.ps1",
        "start_windows10_offline.ps1", "validate_windows10_offline.ps1",
    ]
    for script in scripts:
        absolute = root / "scripts" / script
        assert absolute.is_file()
        # PowerShell AST parse only: never execute downloads or modify .venv.
        code = (
            "$errors = $null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'" + str(absolute).replace("'", "''") + "', [ref]$null, [ref]$errors"
            ") | Out-Null; if ($errors.Count -gt 0) "
            "{ $errors | Out-String | Write-Error; exit 8 }"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code],
            capture_output=True, text=True, check=False, timeout=30,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"


def test_target_install_script_does_not_offer_pip_index_fallback():
    root = Path(__file__).resolve().parents[1]
    install = (root / "scripts/install_windows10_offline_venv.ps1").read_text(
        encoding="utf-8"
    )
    prepare = (root / "scripts/prepare_windows10_wheelhouse.ps1").read_text(
        encoding="utf-8"
    )
    assert "--no-index" in install
    assert "PIP_NO_INDEX" in install
    assert "wheelhouse verify" not in install  # uses the exact Python module CLI
    assert "offline.wheelhouse verify" in install
    assert "--only-binary=:all:" in install
    assert "offline.wheelhouse create" in prepare
    assert "pip --disable-pip-version-check download" in prepare
