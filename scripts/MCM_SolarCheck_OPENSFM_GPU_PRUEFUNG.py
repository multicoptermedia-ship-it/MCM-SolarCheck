"""Bounded OpenSfM-native GPU matching check using only synthetic descriptors."""
from __future__ import annotations

import argparse
import ctypes as ct
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys


MARKER = 'SOLARCHECK_GPU_JSON='
STAGE_MARKER = 'SOLARCHECK_GPU_STAGE='
STAGES = ('system_loader', 'native_imports', 'import_numpy', 'import_pyfeatures',
          'import_pydense', 'dense_device_count', 'features_device_count',
          'device_metadata', 'native_matching', 'worker_complete')
DESCRIPTORS = 64
DIMENSIONS = 128


def stage(name):
    print(STAGE_MARKER + name, flush=True)


def preload_system_opencl(load_dll=None):
    """Select an existing Windows runtime for this child, never replace a DLL."""
    load_dll = load_dll or ct.WinDLL
    kernel = load_dll('kernel32.dll', winmode=0x800)
    for name, args, result in (
        ('GetSystemDirectoryW', [ct.c_wchar_p, ct.c_uint], ct.c_uint),
        ('GetModuleFileNameW', [ct.c_void_p, ct.c_wchar_p, ct.c_uint], ct.c_uint),
        ('GetModuleHandleW', [ct.c_wchar_p], ct.c_void_p),
    ):
        function = getattr(kernel, name)
        function.argtypes, function.restype = args, result
    buffer = ct.create_unicode_buffer(32768)
    length = kernel.GetSystemDirectoryW(buffer, len(buffer))
    if not 0 < length < len(buffer):
        raise OSError('system_directory_unavailable')
    expected = str(Path(buffer.value) / 'OpenCL.dll').casefold()

    def verify(handle):
        size = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
        if not 0 < size < len(buffer) or str(Path(buffer.value)).casefold() != expected:
            raise RuntimeError('opencl_module_outside_system32')
    existing = kernel.GetModuleHandleW('OpenCL.dll')
    if existing:
        verify(existing)
    loader = load_dll(expected, winmode=0x800)
    verify(loader._handle)
    return loader  # Keep this handle alive while native OpenSfM uses the runtime.


def load_engine():
    modules = []
    for name, checkpoint in (('numpy', 'import_numpy'), ('opensfm.pyfeatures', 'import_pyfeatures'),
                             ('opensfm.pydense', 'import_pydense')):
        stage(checkpoint)
        modules.append(importlib.import_module(name))
    prefix = Path(sys.prefix).resolve()
    for module in modules:
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            raise RuntimeError('outside_isolated_prefix')
    return modules


def worker(mode, index=0, load=load_engine, system_opencl=False):
    try:
        runtime = None
        if system_opencl:
            stage('system_loader')
            runtime = preload_system_opencl()
        stage('native_imports')
        np, features, dense = load()
        devices = dense.DepthmapClusterEstimator
        stage('dense_device_count')
        count = int(devices.num_devices())
        stage('features_device_count')
        if not 0 <= count <= 32 or int(features.opencl_num_devices()) != count:
            return {'status': 'device_inventory_mismatch'}
        if mode == 'inventory':
            stage('device_metadata')
            return {'status': 'completed', 'devices': [
                {'index': i, 'name': ''.join(c for c in devices.device_name(i)
                                           if c.isprintable())[:160],
                 'is_gpu': bool(devices.device_is_gpu(i)),
                 'memory_mib': int(devices.device_memory_bytes(i)) // 1048576}
                for i in range(count)]}
        stage('device_metadata')
        if not 0 <= index < count or not devices.device_is_gpu(index):
            return {'status': 'not_a_gpu'}
        # Existing upstream GPU matcher compiles/executes its own OpenCL kernel.
        # Identity descriptors have exactly one zero-distance counterpart each.
        # Two 32-KiB descriptor arrays, no photos and no custom matching engine.
        descriptors = np.eye(DESCRIPTORS, DIMENSIONS, dtype=np.float32)
        stage('native_matching')
        matches = features.match_brute_force_opencl(descriptors, descriptors.copy(), 0.8, index)
        expected = np.column_stack((np.arange(DESCRIPTORS), np.arange(DESCRIPTORS)))
        if matches.dtype.kind not in 'iu' or not np.array_equal(matches, expected):
            return {'status': 'unexpected_matches'}
        return {'status': 'passed', 'matched_descriptors': DESCRIPTORS,
                'descriptor_dimensions': DIMENSIONS, 'kernel': 'opensfm_native_matching'}
    except Exception as error:
        # Native build logs may contain private installation paths: report types only.
        result = {'status': 'native_check_failed', 'error_type': type(error).__name__}
        if str(error) == 'opencl_module_outside_system32':
            result['reason'] = 'opencl_module_outside_system32'
        return result


def last_stage(stdout, include_completion=True):
    names = [line[len(STAGE_MARKER):] for line in stdout.splitlines() if line.startswith(STAGE_MARKER)]
    valid = [name for name in names if name in STAGES and
             (include_completion or name != 'worker_complete')]
    return {'last_stage': valid[-1]} if valid else {}


def read_report(stdout):
    try:
        lines = [line[len(MARKER):] for line in stdout.splitlines() if line.startswith(MARKER)]
        if len(lines) != 1:
            return None
        result = json.loads(lines[0])
        return result if isinstance(result, dict) else None
    except (ValueError, TypeError):
        return None


def run_worker(mode, index=0, system_opencl=False):
    command = [sys.executable, '-I', str(Path(__file__).resolve()), '--worker', mode,
               '--device-index', str(index)]
    if system_opencl:
        command.append('--system-opencl')
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace')
    except OSError:
        return {'status': 'launch_failed'}
    try:
        stdout, _stderr = process.communicate(timeout=30)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        process.kill()
        stdout, _stderr = process.communicate()
        if isinstance(error, KeyboardInterrupt):
            raise
        return {'status': 'timeout', **last_stage(stdout)}
    report = read_report(stdout)
    if process.returncode != 0:
        # Even a completed JSON result cannot be PASS after a native shutdown crash.
        return {'status': 'worker_failed', 'exit_code': process.returncode,
                'exit_code_hex': f'0x{process.returncode & 0xffffffff:08X}',
                'structured_result_written': report is not None, **last_stage(stdout)}
    if report is None:
        return {'status': 'invalid_worker_output'}
    if report.get('status') not in ('passed', 'completed'):
        return {**report, **last_stage(stdout, include_completion=False)}
    return report


def probe(runner=run_worker, loader_mode='process_default'):
    report = {'check': 'solarcheck-opensfm-gpu-1', 'status': 'not_started',
              'dataset': 'not_tested', 'dense_reconstruction': 'not_tested',
              'loader_mode': loader_mode, 'devices': []}
    inventory = runner('inventory')
    if inventory.get('status') != 'completed':
        return {**report, 'status': 'inventory_failed', 'inventory': inventory}
    rows = inventory.get('devices', [])
    if not isinstance(rows, list) or len(rows) > 32:
        return {**report, 'status': 'invalid_inventory'}
    for row in rows:
        if not isinstance(row, dict) or type(row.get('index')) is not int or not 0 <= row['index'] < 32:
            return {**report, 'status': 'invalid_inventory', 'devices': []}
        if row.get('is_gpu') is True:
            result = runner('matching', row['index'])
            report['devices'].append({**row, 'native_matching': result})
    passed = any(row['native_matching'].get('status') == 'passed' for row in report['devices'])
    return {**report, 'status': 'passed' if passed else 'no_verified_gpu'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='OpenSfM-GPU-Funktionsprobe ohne Fotos')
    parser.add_argument('--worker', choices=('inventory', 'matching'), help=argparse.SUPPRESS)
    parser.add_argument('--device-index', type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--system-opencl', action='store_true',
                        help='Preload and verify the existing Windows System32 OpenCL runtime in each worker')
    args = parser.parse_args(argv)
    if not sys.flags.isolated:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_isolated_python_flag'}))
        return 1
    if args.worker:
        print(MARKER + json.dumps(worker(args.worker, args.device_index, system_opencl=args.system_opencl), ensure_ascii=True), flush=True)
        stage('worker_complete')
        return 0
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 10) or struct.calcsize('P') != 8:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_windows_python310_x64'}))
        return 1
    print('OpenSfM-eigener GPU-Matcher, nur synthetische Zahlen. 30 Sekunden je Teiltest.', flush=True)
    try:
        report = probe(lambda mode, index=0: run_worker(mode, index, args.system_opencl),
                       loader_mode='system32_preload' if args.system_opencl else 'process_default')
    except KeyboardInterrupt:
        return 130
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
