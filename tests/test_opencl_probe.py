"""Exercise native-call contracts, failures and child-process containment without a GPU."""
import ctypes as ct
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "MCM_SolarCheck_OPENCL_PRUEFUNG.py"
spec = importlib.util.spec_from_file_location("solarcheck_opencl_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def put(pointer, kind, value):
    ct.cast(pointer, ct.POINTER(kind))[0] = value


class Function:
    def __init__(self, name, implementation):
        self.name, self.implementation = name, implementation

    def __call__(self, *args):
        assert len(args) == len(self.argtypes), self.name
        return self.implementation(self.name, *args)


class Library:
    """Synthetic OpenCL implementation; no driver, photo or persistent file access."""
    def __init__(self, fail=None, wrong_result=False, no_platform=False):
        self.fail, self.wrong_result, self.no_platform = fail, wrong_result, no_platform
        self.calls, self.released = [], []
        self.next_handle = 100
        for name in (
            "clGetPlatformIDs", "clGetPlatformInfo", "clGetDeviceIDs", "clGetDeviceInfo",
            "clCreateContext", "clCreateCommandQueue", "clCreateProgramWithSource",
            "clBuildProgram", "clCreateKernel", "clCreateBuffer", "clSetKernelArg",
            "clEnqueueNDRangeKernel", "clEnqueueReadBuffer", "clReleaseMemObject",
            "clReleaseKernel", "clReleaseProgram", "clReleaseCommandQueue", "clReleaseContext",
        ):
            setattr(self, name, Function(name, self.call))

    def call(self, name, *args):
        self.calls.append(name)
        if name == self.fail:
            if name.startswith("clCreate"):
                put(args[-1], ct.c_int32, -6)
                return None
            return -11
        if name == "clGetPlatformIDs":
            if self.no_platform:
                return -1001
            count, output, size = args
            if output is None:
                put(size, ct.c_uint32, 1)
            else:
                assert count == 1
                output[0] = 10
        elif name == "clGetDeviceIDs":
            platform, device_type, count, output, size = args
            assert platform == 10 and device_type == 4  # GPU only
            if output is None:
                put(size, ct.c_uint32, 1)
            else:
                output[0] = 20
        elif name == "clGetDeviceInfo":
            _device, parameter, _length, output, size = args
            strings = {0x102B: b"NVIDIA GeForce MX250", 0x102C: b"NVIDIA Corporation",
                       0x102F: b"OpenCL 3.0", 0x103D: b"OpenCL C 1.2", 0x102D: b"test-driver"}
            if parameter in strings:
                data = strings[parameter] + b"\0"
                if output is None:
                    put(size, ct.c_size_t, len(data))
                else:
                    ct.memmove(output, data, len(data))
            else:
                kinds = {0x101F: (ct.c_uint64, 2 * 1024**3),
                         0x1010: (ct.c_uint64, 512 * 1024**2),
                         0x1027: (ct.c_uint32, 1), 0x1028: (ct.c_uint32, 1)}
                kind, value = kinds[parameter]
                put(output, kind, value)
        elif name.startswith("clCreate"):
            if name == "clCreateContext":
                assert list(args[0]) == [0x1084, 10, 0]
            if name == "clCreateBuffer":
                assert args[1:4] == (1, 16, None)
            if name == "clCreateKernel":
                assert args[1] == b"solarcheck_probe"
            self.next_handle += 1
            put(args[-1], ct.c_int32, 0)
            return self.next_handle
        elif name == "clBuildProgram":
            assert args[3] == b"-cl-std=CL1.2"
        elif name == "clSetKernelArg":
            assert args[1] == 0 and args[2] == ct.sizeof(ct.c_void_p)
        elif name == "clEnqueueNDRangeKernel":
            assert args[2] == 1 and ct.cast(args[4], ct.POINTER(ct.c_size_t))[0] == 4
        elif name == "clEnqueueReadBuffer":
            assert args[2:5] == (1, 0, 16)  # blocking read, byte extent
            values = [7, 10, 13, 16] if not self.wrong_result else [0, 0, 0, 0]
            for i, value in enumerate(values):
                args[5][i] = value
        elif name.startswith("clRelease"):
            self.released.append((name, args[0]))
        return 0


def test_inventory_selects_gpu_and_reports_memory_without_paths():
    rows = probe.OpenCL(Library()).inventory()
    assert len(rows) == 1
    assert rows[0]["name"] == "NVIDIA GeForce MX250"
    assert rows[0]["memory_mib"] == 2048
    assert rows[0]["max_allocation_mib"] == 512
    assert rows[0]["compiler_available"]
    assert set(rows[0]) == {"platform_index", "device_index", "name", "vendor", "opencl_version",
                            "opencl_c_version", "driver_version", "memory_mib", "max_allocation_mib",
                            "available", "compiler_available"}


def test_no_opencl_platform_is_a_normal_empty_inventory():
    assert probe.OpenCL(Library(no_platform=True)).inventory() == []


def test_kernel_compiles_runs_reads_and_releases_in_reverse_order():
    lib = Library()
    assert probe.OpenCL(lib).kernel_test(0, 0) == {"status": "passed", "kernel": "OpenCL-C-1.2"}
    assert [handle for _, handle in lib.released] == [105, 104, 103, 102, 101]
    assert "clEnqueueNDRangeKernel" in lib.calls and "clEnqueueReadBuffer" in lib.calls


@pytest.mark.parametrize("failure,created", [
    ("clCreateContext", 0), ("clCreateCommandQueue", 1),
    ("clBuildProgram", 3), ("clCreateKernel", 3),
    ("clCreateBuffer", 4), ("clSetKernelArg", 5),
    ("clEnqueueNDRangeKernel", 5), ("clEnqueueReadBuffer", 5),
])
def test_native_errors_remain_failures_and_release_existing_resources(failure, created):
    lib = Library(fail=failure)
    with pytest.raises(probe.ProbeError) as error:
        probe.OpenCL(lib).kernel_test(0, 0)
    assert error.value.operation == failure
    assert len(lib.released) == created


def test_wrong_gpu_result_is_rejected():
    lib = Library(wrong_result=True)
    with pytest.raises(probe.ProbeError, match="kernel_result_mismatch"):
        probe.OpenCL(lib).kernel_test(0, 0)
    assert len(lib.released) == 5


def test_cleanup_error_does_not_pass():
    with pytest.raises(probe.ProbeError, match="opencl_cleanup_failed"):
        probe.OpenCL(Library(fail="clReleaseMemObject")).kernel_test(0, 0)


def test_missing_device_does_not_select_another_device():
    with pytest.raises(probe.ProbeError, match="device_disappeared"):
        probe.OpenCL(Library()).kernel_test(0, 1)


def test_windows_loader_uses_system32_only_and_hides_local_error(monkeypatch):
    seen = []

    def load(name, **kwargs):
        seen.append((name, kwargs))
        raise OSError("private-user-path")

    monkeypatch.setattr(probe.sys, "platform", "win32")
    monkeypatch.setattr(probe.ct, "WinDLL", load, raising=False)
    result = probe.worker("inventory")
    assert seen == [("OpenCL.dll", {"winmode": 0x800})]
    assert result == {"status": "failed", "operation": "opencl_loader_unavailable", "code": 0}
    assert "private" not in json.dumps(result)


def test_failed_inventory_does_not_launch_kernel():
    calls = []

    def runner(*args):
        calls.append(args)
        return {"status": "failed", "operation": "opencl_loader_unavailable"}

    report = probe.probe(runner)
    assert calls == [("inventory",)] and report["devices"] == []
    assert report["opensfm"] == "not_tested"


def test_device_success_and_failure_kept_separate():
    rows = [{"platform_index": 0, "device_index": i, "name": str(i)} for i in range(2)]

    def runner(mode, pi=0, di=0):
        if mode == "inventory":
            return {"status": "completed", "devices": rows}
        return {"status": "passed" if di == 1 else "failed"}

    report = probe.probe(runner)
    assert [d["kernel_test"]["status"] for d in report["devices"]] == ["failed", "passed"]
    assert report["opensfm"] == "not_tested"


def test_invalid_inventory_indices_are_rejected():
    def runner(mode):
        return {"status": "completed", "devices": [{"platform_index": -1, "device_index": 0}]}

    assert probe.probe(runner)["inventory"]["operation"] == "invalid_device_indices"


@pytest.mark.parametrize("failure", ["timeout", "exit", "invalid", "interrupt"])
def test_worker_crash_timeout_and_invalid_output_are_contained(monkeypatch, failure):
    class Process:
        returncode = -17 if failure == "exit" else 0
        killed = False

        def communicate(self, timeout=None):
            if timeout is not None and failure in ("timeout", "interrupt"):
                if failure == "interrupt":
                    raise KeyboardInterrupt
                raise subprocess.TimeoutExpired("worker", timeout)
            return b"private-driver-noise" if failure == "invalid" else b"{}", b"private-path"

        def kill(self):
            self.killed = True

    process = Process()
    monkeypatch.setattr(probe.subprocess, "Popen", lambda *a, **kw: process)
    if failure == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            probe.run_worker("inventory")
        assert process.killed
    else:
        result = probe.run_worker("inventory")
        assert result["status"] == "failed"
        assert "private" not in json.dumps(result)
        assert process.killed == (failure == "timeout")


def test_real_standalone_child_can_start_without_package_imports():
    # On Windows this probes the installed loader/platforms; absence is expected
    # on hosted runners. Success here is NOT a real GPU/OpenSfM qualification.
    result = probe.run_worker("inventory")
    assert result["status"] in ("completed", "failed")
    assert result.get("operation") not in ("worker_start_failed", "invalid_worker_result", "worker_exit")


def test_real_timed_out_child_is_reaped(monkeypatch, tmp_path):
    stalled = tmp_path / "stalled_driver.py"
    stalled.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    monkeypatch.setattr(probe, "__file__", str(stalled))
    monkeypatch.setattr(probe, "TIMEOUT_SECONDS", 0.1)
    real_popen = subprocess.Popen
    processes = []

    def start(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(probe.subprocess, "Popen", start)
    assert probe.run_worker("inventory")["operation"] == "worker_timeout"
    assert len(processes) == 1 and processes[0].poll() is not None


def test_empty_inventory_is_not_reported_as_gpu_success(monkeypatch, capsys):
    monkeypatch.setattr(probe.sys, "platform", "win32")
    monkeypatch.setattr(probe, "probe", lambda: {
        "opensfm": "not_tested", "inventory": {"status": "completed", "gpu_count": 0}, "devices": []})
    assert probe.main([]) == 1
    output = capsys.readouterr().out
    assert "GPU-Kerntest: NICHT BESTANDEN" in output
    assert '"opensfm": "not_tested"' in output
