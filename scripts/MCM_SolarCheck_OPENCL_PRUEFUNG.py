"""Read-only OpenCL discovery and a tiny GPU kernel test; standard library only.

No OpenSfM, photos, project files, downloads or driver changes are involved.
Native driver calls run in disposable child processes with a time limit.
"""
from __future__ import annotations

import argparse
import ctypes as ct
import json
from pathlib import Path
import subprocess
import sys


TIMEOUT_SECONDS = 20
CL_DEVICE_NOT_FOUND = -1
CL_PLATFORM_NOT_FOUND_KHR = -1001
KERNEL = b"""__kernel void solarcheck_probe(__global int *out) {
    size_t i = get_global_id(0); out[i] = (int)i * 3 + 7;
}"""


class ProbeError(Exception):
    def __init__(self, operation: str, code: int):
        self.operation, self.code = operation, int(code)
        super().__init__(operation)


class OpenCL:
    def __init__(self, library=None):
        if library is None:
            if sys.platform != "win32":
                raise ProbeError("windows_required", 0)
            try:
                # Search System32 only, never a DLL beside the downloaded script.
                library = ct.WinDLL("OpenCL.dll", winmode=0x00000800)
            except OSError:
                raise ProbeError("opencl_loader_unavailable", 0) from None
        self.lib = library
        p = ct.c_void_p
        u = ct.c_uint32
        z = ct.c_size_t
        i = ct.c_int32
        pp, pu, pz, pi = ct.POINTER(p), ct.POINTER(u), ct.POINTER(z), ct.POINTER(i)
        declarations = {
            "clGetPlatformIDs": (i, [u, pp, pu]),
            "clGetPlatformInfo": (i, [p, u, z, p, pz]),
            "clGetDeviceIDs": (i, [p, ct.c_uint64, u, pp, pu]),
            "clGetDeviceInfo": (i, [p, u, z, p, pz]),
            "clCreateContext": (p, [p, u, pp, p, p, pi]),
            "clCreateCommandQueue": (p, [p, p, ct.c_uint64, pi]),
            "clCreateProgramWithSource": (p, [p, u, ct.POINTER(ct.c_char_p), pz, pi]),
            "clBuildProgram": (i, [p, u, pp, ct.c_char_p, p, p]),
            "clCreateKernel": (p, [p, ct.c_char_p, pi]),
            "clCreateBuffer": (p, [p, ct.c_uint64, z, p, pi]),
            "clSetKernelArg": (i, [p, u, z, p]),
            "clEnqueueNDRangeKernel": (i, [p, p, u, pz, pz, pz, u, pp, pp]),
            "clEnqueueReadBuffer": (i, [p, p, u, z, z, p, u, pp, pp]),
            "clReleaseMemObject": (i, [p]),
            "clReleaseKernel": (i, [p]),
            "clReleaseProgram": (i, [p]),
            "clReleaseCommandQueue": (i, [p]),
            "clReleaseContext": (i, [p]),
        }
        try:
            for name, (result, args) in declarations.items():
                function = getattr(library, name)
                function.restype, function.argtypes = result, args
        except AttributeError:
            raise ProbeError("opencl_functions_unavailable", 0) from None

    @staticmethod
    def check(code, operation):
        if code != 0:
            raise ProbeError(operation, code)

    def ids(self, function, leading=(), empty_code=None):
        count = ct.c_uint32()
        code = function(*leading, 0, None, ct.byref(count))
        if code == empty_code:
            return []
        self.check(code, "enumerate_devices")
        if count.value > 256:
            raise ProbeError("device_count_out_of_range", 0)
        if not count.value:
            return []
        values = (ct.c_void_p * count.value)()
        self.check(function(*leading, count.value, values, None), "enumerate_devices")
        if any(value is None for value in values):
            raise ProbeError("invalid_device_handle", 0)
        return list(values)

    def platforms(self):
        return self.ids(self.lib.clGetPlatformIDs, empty_code=CL_PLATFORM_NOT_FOUND_KHR)

    def devices(self, platform):
        # OpenSfM's native dense pipeline selects GPU devices, not OpenCL CPUs.
        return self.ids(self.lib.clGetDeviceIDs, (platform, 4), CL_DEVICE_NOT_FOUND)

    def string(self, function, handle, parameter):
        size = ct.c_size_t()
        self.check(function(handle, parameter, 0, None, ct.byref(size)), "device_info")
        if not 0 < size.value <= 4096:
            raise ProbeError("invalid_device_info", 0)
        buffer = ct.create_string_buffer(size.value)
        self.check(function(handle, parameter, size.value, buffer, None), "device_info")
        text = buffer.value.decode("utf-8", "replace")
        return "".join(c for c in text if c.isprintable())[:160]

    def scalar(self, handle, parameter, kind):
        value = kind()
        self.check(self.lib.clGetDeviceInfo(handle, parameter, ct.sizeof(value),
                                           ct.byref(value), None), "device_info")
        return value.value

    def inventory(self):
        rows = []
        for platform_index, platform in enumerate(self.platforms()):
            for device_index, device in enumerate(self.devices(platform)):
                info = self.lib.clGetDeviceInfo
                rows.append({
                    "platform_index": platform_index,
                    "device_index": device_index,
                    "name": self.string(info, device, 0x102B),
                    "vendor": self.string(info, device, 0x102C),
                    "opencl_version": self.string(info, device, 0x102F),
                    "opencl_c_version": self.string(info, device, 0x103D),
                    "driver_version": self.string(info, device, 0x102D),
                    "memory_mib": self.scalar(device, 0x101F, ct.c_uint64) // 1048576,
                    "max_allocation_mib": self.scalar(device, 0x1010, ct.c_uint64) // 1048576,
                    "available": bool(self.scalar(device, 0x1027, ct.c_uint32)),
                    "compiler_available": bool(self.scalar(device, 0x1028, ct.c_uint32)),
                })
        return rows

    def kernel_test(self, platform_index, device_index):
        try:
            platform = self.platforms()[platform_index]
            device = ct.c_void_p(self.devices(platform)[device_index])
        except IndexError:
            raise ProbeError("device_disappeared", 0) from None
        resources = []
        error = ct.c_int32()

        def create(name, release, *args):
            error.value = 0
            handle = getattr(self.lib, name)(*args, ct.byref(error))
            if handle:
                resources.append((release, handle))
            self.check(error.value, name)
            if not handle:
                raise ProbeError(name, 0)
            return handle

        try:
            properties = (ct.c_ssize_t * 3)(0x1084, platform, 0)  # CL_CONTEXT_PLATFORM
            context = create("clCreateContext", "clReleaseContext", properties, 1,
                             ct.byref(device), None, None)
            queue = create("clCreateCommandQueue", "clReleaseCommandQueue", context, device, 0)
            source = ct.c_char_p(KERNEL)
            length = ct.c_size_t(len(KERNEL))
            program = create("clCreateProgramWithSource", "clReleaseProgram", context, 1,
                             ct.byref(source), ct.byref(length))
            self.check(self.lib.clBuildProgram(program, 1, ct.byref(device),
                                              b"-cl-std=CL1.2", None, None), "clBuildProgram")
            kernel = create("clCreateKernel", "clReleaseKernel", program, b"solarcheck_probe")
            output = (ct.c_int32 * 4)()
            buffer = create("clCreateBuffer", "clReleaseMemObject", context, 1,
                            ct.sizeof(output), None)
            buffer_arg = ct.c_void_p(buffer)
            self.check(self.lib.clSetKernelArg(kernel, 0, ct.sizeof(buffer_arg),
                                              ct.byref(buffer_arg)), "clSetKernelArg")
            size = ct.c_size_t(4)
            self.check(self.lib.clEnqueueNDRangeKernel(queue, kernel, 1, None,
                                                      ct.byref(size), None, 0, None, None),
                       "clEnqueueNDRangeKernel")
            self.check(self.lib.clEnqueueReadBuffer(queue, buffer, 1, 0, ct.sizeof(output),
                                                   output, 0, None, None), "clEnqueueReadBuffer")
            if list(output) != [7, 10, 13, 16]:
                raise ProbeError("kernel_result_mismatch", 0)
        finally:
            cleanup_failed = False
            for release, handle in reversed(resources):
                cleanup_failed |= getattr(self.lib, release)(handle) != 0
            if cleanup_failed and sys.exc_info()[0] is None:
                raise ProbeError("opencl_cleanup_failed", 0)
        return {"status": "passed", "kernel": "OpenCL-C-1.2"}


def worker(mode, platform_index=0, device_index=0):
    if not 0 <= platform_index < 256 or not 0 <= device_index < 256:
        return {"status": "failed", "operation": "invalid_device_indices"}
    try:
        api = OpenCL()
        if mode == "inventory":
            return {"status": "completed", "devices": api.inventory()}
        return api.kernel_test(platform_index, device_index)
    except ProbeError as error:
        return {"status": "failed", "operation": error.operation, "code": error.code}
    except Exception:
        # Never echo local paths or arbitrary driver exception messages.
        return {"status": "failed", "operation": "unexpected_probe_error"}


def run_worker(mode, platform_index=0, device_index=0):
    command = [sys.executable, "-I", str(Path(__file__).resolve()), "--worker", mode,
               "--platform-index", str(platform_index), "--device-index", str(device_index)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=flags)
    except OSError:
        return {"status": "failed", "operation": "worker_start_failed"}
    try:
        stdout, _stderr = process.communicate(timeout=TIMEOUT_SECONDS)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        process.kill()
        process.communicate()
        if isinstance(error, KeyboardInterrupt):
            raise
        return {"status": "failed", "operation": "worker_timeout",
                "timeout_seconds": TIMEOUT_SECONDS}
    if process.returncode != 0:
        return {"status": "failed", "operation": "worker_exit", "exit_code": process.returncode}
    try:
        result = json.loads(stdout)
        if not isinstance(result, dict) or result.get("status") not in ("completed", "passed", "failed"):
            raise ValueError
        return result
    except (ValueError, UnicodeDecodeError):
        return {"status": "failed", "operation": "invalid_worker_result"}


def probe(runner=run_worker):
    inventory = runner("inventory")
    report = {"check": "solarcheck-opencl-1", "python_bits": 8 * ct.sizeof(ct.c_void_p),
              "opensfm": "not_tested",
              "inventory": inventory, "devices": []}
    if inventory.get("status") != "completed":
        return report
    rows = inventory.get("devices", [])
    report["inventory"] = {"status": "completed", "gpu_count": len(rows)}
    for row in rows:
        pi, di = row.get("platform_index"), row.get("device_index")
        if type(pi) is not int or type(di) is not int or not 0 <= pi < 256 or not 0 <= di < 256:
            report["inventory"] = {"status": "failed", "operation": "invalid_device_indices"}
            report["devices"] = []
            return report
        result = runner("kernel", pi, di)
        report["devices"].append({**row, "kernel_test": result})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lokale OpenCL-Pruefung ohne Fotos oder Installation")
    parser.add_argument("--worker", choices=("inventory", "kernel"), help=argparse.SUPPRESS)
    parser.add_argument("--platform-index", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--device-index", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        print(json.dumps(worker(args.worker, args.platform_index, args.device_index)))
        return 0
    if sys.platform != "win32":
        print("Diese Pruefung bitte mit dem vorhandenen Python unter Windows 10 starten.")
        return 1
    print("OpenCL-Geraete und kurzer GPU-Kerntest; keine Fotos/Projektdateien erforderlich.", flush=True)
    print("Zeitlimit: 20 Sekunden je Geraeteabfrage/Kerntest.", flush=True)
    try:
        report = probe()
    except KeyboardInterrupt:
        print("Pruefung abgebrochen.")
        return 130
    print(json.dumps(report, ensure_ascii=True, indent=2))
    passed = any(d["kernel_test"].get("status") == "passed" for d in report["devices"])
    print("GPU-Kerntest: " + ("BESTANDEN (mindestens ein Geraet)" if passed else "NICHT BESTANDEN"))
    print("OpenSfM, voller GPU-Speicherbedarf und Orthofotoqualitaet sind noch nicht geprueft.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
