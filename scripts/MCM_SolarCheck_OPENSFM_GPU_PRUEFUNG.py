"""Bounded OpenSfM-native GPU matching check using only synthetic descriptors."""
from __future__ import annotations

import argparse
import ctypes as ct
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time


MARKER = 'SOLARCHECK_GPU_JSON='
STAGE_MARKER = 'SOLARCHECK_GPU_STAGE='
STAGES = ('system_loader', 'native_imports', 'official_cli_imports', 'import_numpy', 'import_pyfeatures',
          'import_pydense', 'engine_ready', 'dense_device_count', 'features_device_count',
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


def load_engine(cli_imports=False):
    prefix = Path(sys.prefix).resolve()
    if cli_imports:
        # Same first import as upstream bin/opensfm_main.py; no DataSet or job.
        stage('official_cli_imports')
        commands = importlib.import_module('opensfm.commands')
        if not Path(commands.__file__).resolve().is_relative_to(prefix):
            raise RuntimeError('outside_isolated_prefix')
    modules = []
    for name, checkpoint in (('numpy', 'import_numpy'), ('opensfm.pyfeatures', 'import_pyfeatures'),
                             ('opensfm.pydense', 'import_pydense')):
        stage(checkpoint)
        modules.append(importlib.import_module(name))
    for module in modules:
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            raise RuntimeError('outside_isolated_prefix')
    return modules


def worker(mode, index=0, load=load_engine, system_opencl=False, cli_imports=False):
    try:
        if cli_imports and not Path(os.environ.get('MPLCONFIGDIR', '')).is_absolute():
            return {'status': 'cache_not_configured'}
        runtime = None
        if system_opencl:
            stage('system_loader')
            runtime = preload_system_opencl()
        stage('native_imports')
        np, features, dense = load(cli_imports=True) if cli_imports else load()
        stage('engine_ready')
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


def before_exit_summary(report):
    """Preserve diagnostic facts, never turn a failed process into success."""
    if not isinstance(report, dict) or report.get('status') not in (
            'completed', 'passed', 'native_check_failed', 'device_inventory_mismatch',
            'not_a_gpu', 'unexpected_matches', 'cache_not_configured'):
        return {}
    summary = {'reported_status': report['status'], 'accepted_as_success': False}
    rows = report.get('devices')
    if isinstance(rows, list) and len(rows) <= 32 and all(
            isinstance(row, dict) and type(row.get('is_gpu')) is bool for row in rows):
        summary['device_count'] = len(rows)
        summary['gpu_count'] = sum(row['is_gpu'] for row in rows)
    if report.get('error_type') in ('ImportError', 'ModuleNotFoundError', 'OSError',
            'FileNotFoundError', 'RuntimeError', 'AttributeError', 'TypeError', 'ValueError'):
        summary['error_type'] = report['error_type']
    if report.get('reason') == 'opencl_module_outside_system32':
        summary['reason'] = report['reason']
    return summary


def communicate_with_phase_limits(process, startup_seconds=120, native_seconds=30, clock=None):
    """Give imports their own budget; never extend a native operation's budget.

    Retrying Popen.communicate after TimeoutExpired is supported and preserves
    accumulated output. Only our exact flushed readiness marker starts the
    native budget, once. No engine import, warmup job or second worker here.
    """
    clock = clock or time.monotonic
    deadline = clock() + startup_seconds
    phase = 'startup'
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            process.kill()
            stdout, _stderr = process.communicate()
            return stdout, phase
        try:
            stdout, _stderr = process.communicate(timeout=min(0.1, remaining))
            return stdout, None
        except subprocess.TimeoutExpired as error:
            output = error.output or ''
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            if phase == 'startup' and STAGE_MARKER + 'engine_ready' in output.splitlines():
                phase = 'native'
                deadline = clock() + native_seconds


def run_worker(mode, index=0, system_opencl=False, cli_imports=False, phase_timeouts=False):
    command = [sys.executable, '-I', str(Path(__file__).resolve()), '--worker', mode,
               '--device-index', str(index)]
    if system_opencl:
        command.append('--system-opencl')
    if cli_imports:
        command.append('--cli-imports')
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace')
    except OSError:
        return {'status': 'launch_failed'}
    try:
        if phase_timeouts:
            stdout, timeout_phase = communicate_with_phase_limits(process)
            if timeout_phase:
                return {'status': 'timeout', 'timeout_phase': timeout_phase,
                        'limit_seconds': 120 if timeout_phase == 'startup' else 30,
                        **last_stage(stdout)}
        else:
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
        result = {'status': 'worker_failed', 'exit_code': process.returncode,
                'exit_code_hex': f'0x{process.returncode & 0xffffffff:08X}',
                'structured_result_written': report is not None, **last_stage(stdout)}
        summary = before_exit_summary(report)
        if summary:
            result['before_exit'] = summary
        return result
    if report is None:
        return {'status': 'invalid_worker_output'}
    if report.get('status') not in ('passed', 'completed'):
        return {**report, **last_stage(stdout, include_completion=False)}
    return report


def probe(runner=run_worker, loader_mode='process_default', startup_mode='minimal_modules'):
    report = {'check': 'solarcheck-opensfm-gpu-1', 'status': 'not_started',
              'dataset': 'not_tested', 'dense_reconstruction': 'not_tested',
              'loader_mode': loader_mode, 'startup_mode': startup_mode, 'devices': []}
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
    parser.add_argument('--cli-imports', action='store_true',
                        help='Import the official OpenSfM command registry before native modules')
    parser.add_argument('--phase-timeouts', action='store_true',
                        help='Allow 120 s for imports, then a separate 30 s for native work and shutdown')
    args = parser.parse_args(argv)
    if not sys.flags.isolated:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_isolated_python_flag'}))
        return 1
    if args.worker:
        print(MARKER + json.dumps(worker(args.worker, args.device_index,
            system_opencl=args.system_opencl, cli_imports=args.cli_imports), ensure_ascii=True), flush=True)
        stage('worker_complete')
        return 0
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 10) or struct.calcsize('P') != 8:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_windows_python310_x64'}))
        return 1
    limits = '120 Sekunden fuer Importe, danach 30 Sekunden fuer native Arbeit/Prozessende.' if args.phase_timeouts else '30 Sekunden je Teiltest.'
    print('OpenSfM-eigener GPU-Matcher, nur synthetische Zahlen. ' + limits, flush=True)
    try:
        report = probe(lambda mode, index=0: run_worker(mode, index, args.system_opencl,
                       args.cli_imports, phase_timeouts=args.phase_timeouts),
                       loader_mode='system32_preload' if args.system_opencl else 'process_default',
                       startup_mode='official_cli' if args.cli_imports else 'minimal_modules')
    except KeyboardInterrupt:
        return 130
    if args.phase_timeouts:
        report['time_limits_seconds'] = {'startup': 120, 'native_including_shutdown': 30}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
