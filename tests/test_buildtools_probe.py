"""Synthetic failure boundaries and an actual Windows compiler/SDK/x64 run."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py"
spec = importlib.util.spec_from_file_location("solarcheck_buildtools_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def installed_fixture(tmp_path, monkeypatch):
    # Spaces, parentheses and ampersands must not break the batch CALL/cwd.
    installation = tmp_path / "synthetic VS (2022) & SDK"
    vcvars = installation / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    vcvars.parent.mkdir(parents=True)
    vcvars.write_text("@echo off\n", encoding="ascii")
    monkeypatch.setattr(probe.sys, "platform", "win32")
    monkeypatch.setattr(probe, "find_vs2022", lambda: {
        "installationPath": str(installation), "installationVersion": "17.14.44.0",
    })
    return vcvars


def test_missing_cpp_tools_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.sys, "platform", "win32")
    monkeypatch.setattr(probe, "find_vs2022", lambda: None)
    output = tmp_path / "must-not-be-created"
    assert probe.check(output)["status"] == "vs2022_cpp_not_found"
    assert not output.exists()


@pytest.mark.parametrize("character", ['%', '!', '^', '"', '\r', '\n', '\u00e4'])
def test_command_expansion_and_non_ascii_setup_paths_are_not_executed(tmp_path, monkeypatch, character):
    if character in '<>"\r\n' and sys.platform == "win32":
        # Windows does not permit these characters in an actual path.
        with pytest.raises(ValueError):
            probe.compiler_batch("invalid" + character + "path")
        return
    vcvars = installed_fixture(tmp_path, monkeypatch)
    original_batch = probe.compiler_batch
    monkeypatch.setattr(probe, "compiler_batch", lambda path: original_batch(str(path) + character))
    output = tmp_path / "not-created"
    assert probe.check(output)["status"] == "setup_path_unsupported"
    assert not output.exists()


@pytest.mark.parametrize("exit_code, stage", [(11, "compiler_environment"), (12, "compile_link"), (13, "execute")])
def test_failures_keep_raw_logs_local_and_do_not_change_existing_files(tmp_path, monkeypatch, exit_code, stage):
    installed_fixture(tmp_path, monkeypatch)
    original = tmp_path / "existing-project.txt"
    original.write_bytes(b"unchanged-project-fixture")
    output = tmp_path / "owned probes"

    def failed(work, env):
        assert Path(env["TEMP"]).parent == work
        assert env["TMP"] == env["TEMP"]
        assert not any(key in env for key in ("CL", "_CL_", "LINK", "_LINK_"))
        (work / "build.log").write_bytes(
            b'C:\\synthetic-private\\customer\\source.cpp: error C1083: missing SDK\n'
            b'error LNK1104: C:\\synthetic-private\\customer\\data.lib\n'
        )
        return exit_code

    monkeypatch.setenv("CL", "/Fo:C:\\unexpected\\object.obj")
    monkeypatch.setattr(probe, "run_batch", failed)
    report = probe.check(output)
    assert report["status"] == "failed"
    assert report["stage"] == stage
    assert report["compiler_codes"] == ["C1083", "LNK1104"]
    assert "synthetic-private" not in json.dumps(report)
    assert original.read_bytes() == b"unchanged-project-fixture"
    assert len(list(output.iterdir())) == 1


@pytest.mark.parametrize("bad_executable", [True, False])
def test_success_exit_without_valid_executable_and_output_is_rejected(tmp_path, monkeypatch, bad_executable):
    installed_fixture(tmp_path, monkeypatch)

    def invalid(work, env):
        pe = b"MZ" + bytes(58) + struct.pack("<I", 64) + b"PE\0\0\x64\x86"
        (work / "probe.exe").write_bytes(b"not-an-executable" if bad_executable else pe)
        (work / "run.log").write_bytes(probe.TOKEN if bad_executable else b"unexpected output")
        return 0

    monkeypatch.setattr(probe, "run_batch", invalid)
    assert probe.check(tmp_path / "output")["status"] == "result_invalid"


@pytest.mark.parametrize("root_key", ["SystemRoot", "SYSTEMROOT", "systemroot"])
def test_timeout_stops_only_the_owned_process_tree(tmp_path, monkeypatch, root_key):
    class Process:
        pid = 12345
        calls = 0

        def wait(self, timeout):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("owned-check", timeout)
            return 1

    process = Process()
    calls = []
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(probe.subprocess, "run", lambda args, **kw: calls.append(args))
    assert probe.run_batch(tmp_path, {root_key: str(tmp_path / "synthetic Windows")}) is None
    assert calls == [[str(tmp_path / "synthetic Windows" / "System32" / "taskkill.exe"),
                      "/PID", "12345", "/T", "/F"]]
    assert process.calls == 2


def test_x86_executable_cannot_pass_as_x64(tmp_path):
    path = tmp_path / "synthetic.exe"
    path.write_bytes(b"MZ" + bytes(58) + struct.pack("<I", 64) + b"PE\0\0\x4c\x01")
    assert not probe.is_x64_executable(path)


@pytest.mark.skipif(sys.platform != "win32", reason="Requires actual MSVC and Windows SDK")
@pytest.mark.parametrize("folder", ["probe-files", "probe files (spaces) & tools"])
def test_native_windows_cpp17_sdk_compile_link_and_execution(tmp_path, folder):
    # Required on the pinned windows-2022 CI image, not silently skipped if
    # the SDK/toolchain is absent. Only the explicit disposable CI directory.
    output = tmp_path / folder
    report = probe.check(output)
    if report["status"] != "passed":
        # Diagnostics from this test's newly generated, synthetic CI build only.
        # The standalone user command still never prints its raw local logs.
        details = [json.dumps(report, indent=2)]
        for work in output.glob("probe-*"):
            for name in ("driver.log", "activate.log", "build.log", "run.log"):
                log = work / name
                if log.is_file():
                    details.append(name + ": " + log.read_bytes()[-3000:].decode("utf-8", "replace"))
        pytest.fail("\n".join(details))
    assert report["cpp17_windows_sdk_x64"] == "passed"
    assert report["opensfm"] == "not_tested"
    assert report["installer_started"] is False
