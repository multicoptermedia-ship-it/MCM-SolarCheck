"""Bounded OpenSfM-native GPU matching check using only synthetic descriptors."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys


MARKER = 'SOLARCHECK_GPU_JSON='
DESCRIPTORS = 64
DIMENSIONS = 128


def load_engine():
    modules = [importlib.import_module(name) for name in
               ('numpy', 'opensfm.pyfeatures', 'opensfm.pydense')]
    prefix = Path(sys.prefix).resolve()
    for module in modules:
        if not Path(module.__file__).resolve().is_relative_to(prefix):
            raise RuntimeError('outside_isolated_prefix')
    return modules


def worker(mode, index=0, load=load_engine):
    try:
        np, features, dense = load()
        devices = dense.DepthmapClusterEstimator
        count = int(devices.num_devices())
        if not 0 <= count <= 32 or int(features.opencl_num_devices()) != count:
            return {'status': 'device_inventory_mismatch'}
        if mode == 'inventory':
            return {'status': 'completed', 'devices': [
                {'index': i, 'name': ''.join(c for c in devices.device_name(i)
                                           if c.isprintable())[:160],
                 'is_gpu': bool(devices.device_is_gpu(i)),
                 'memory_mib': int(devices.device_memory_bytes(i)) // 1048576}
                for i in range(count)]}
        if not 0 <= index < count or not devices.device_is_gpu(index):
            return {'status': 'not_a_gpu'}
        # Existing upstream GPU matcher compiles/executes its own OpenCL kernel.
        # Identity descriptors have exactly one zero-distance counterpart each.
        # Two 32-KiB descriptor arrays, no photos and no custom matching engine.
        descriptors = np.eye(DESCRIPTORS, DIMENSIONS, dtype=np.float32)
        matches = features.match_brute_force_opencl(descriptors, descriptors.copy(), 0.8, index)
        expected = np.column_stack((np.arange(DESCRIPTORS), np.arange(DESCRIPTORS)))
        if matches.dtype.kind not in 'iu' or not np.array_equal(matches, expected):
            return {'status': 'unexpected_matches'}
        return {'status': 'passed', 'matched_descriptors': DESCRIPTORS,
                'descriptor_dimensions': DIMENSIONS, 'kernel': 'opensfm_native_matching'}
    except Exception as error:
        # Native build logs may contain private installation paths: report types only.
        return {'status': 'native_check_failed', 'error_type': type(error).__name__}


def run_worker(mode, index=0):
    try:
        process = subprocess.Popen(
            [sys.executable, '-I', str(Path(__file__).resolve()), '--worker', mode,
             '--device-index', str(index)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding='utf-8', errors='replace')
    except OSError:
        return {'status': 'launch_failed'}
    try:
        stdout, _stderr = process.communicate(timeout=30)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        process.kill()
        process.communicate()
        if isinstance(error, KeyboardInterrupt):
            raise
        return {'status': 'timeout'}
    if process.returncode != 0:
        return {'status': 'worker_failed', 'exit_code': process.returncode}
    try:
        lines = [line[len(MARKER):] for line in stdout.splitlines() if line.startswith(MARKER)]
        if len(lines) != 1:
            return {'status': 'invalid_worker_output'}
        report = json.loads(lines[0])
        return report if isinstance(report, dict) else {'status': 'invalid_worker_output'}
    except (ValueError, TypeError):
        return {'status': 'invalid_worker_output'}


def probe(runner=run_worker):
    report = {'check': 'solarcheck-opensfm-gpu-1', 'status': 'not_started',
              'dataset': 'not_tested', 'dense_reconstruction': 'not_tested', 'devices': []}
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
    args = parser.parse_args(argv)
    if not sys.flags.isolated:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_isolated_python_flag'}))
        return 1
    if args.worker:
        print(MARKER + json.dumps(worker(args.worker, args.device_index), ensure_ascii=True))
        return 0
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 10) or struct.calcsize('P') != 8:
        print(json.dumps({'check': 'solarcheck-opensfm-gpu-1', 'status': 'requires_windows_python310_x64'}))
        return 1
    print('OpenSfM-eigener GPU-Matcher, nur synthetische Zahlen. 30 Sekunden je Teiltest.', flush=True)
    try:
        report = probe()
    except KeyboardInterrupt:
        return 130
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
