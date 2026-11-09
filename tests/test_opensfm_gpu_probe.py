"""Check probe boundaries with synthetic native adapters, never a driver or photo."""
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
spec = importlib.util.spec_from_file_location('opensfm_gpu_probe', SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def engine(*, wrong=False, cpu=False, fail=False):
    def match(a, b, ratio, index):
        assert a.shape == b.shape == (64, 128)
        assert a.dtype == b.dtype == np.float32 and a.nbytes == 32768
        assert np.array_equal(a, np.eye(64, 128, dtype=np.float32))
        assert np.array_equal(a, b) and not np.shares_memory(a, b)
        assert ratio == 0.8 and index == 0
        if fail:
            raise RuntimeError('private/path/not/for/report')
        result = np.column_stack((np.arange(64), np.arange(64))).astype(np.int32)
        if wrong:
            result[0, 1] = 1
        return result
    dense = SimpleNamespace(DepthmapClusterEstimator=SimpleNamespace(
        num_devices=lambda: 1, device_name=lambda i: 'synthetic GPU',
        device_is_gpu=lambda i: not cpu, device_memory_bytes=lambda i: 2 * 1024**3))
    return np, SimpleNamespace(opencl_num_devices=lambda: 1, match_brute_force_opencl=match), dense


def test_native_matcher_receives_only_tiny_synthetic_descriptors_and_selected_index():
    result = probe.worker('matching', load=engine)
    assert result['status'] == 'passed'
    assert result['matched_descriptors'] == 64


@pytest.mark.parametrize('options, expected', [
    ({'wrong': True}, 'unexpected_matches'), ({'cpu': True}, 'not_a_gpu'),
    ({'fail': True}, 'native_check_failed')])
def test_neither_wrong_results_nor_cpu_nor_native_errors_count_as_gpu_pass(options, expected):
    result = probe.worker('matching', load=lambda: engine(**options))
    assert result['status'] == expected
    assert 'private/path' not in json.dumps(result)


def test_cpu_inventory_never_triggers_gpu_work():
    calls = []
    def runner(mode, index=0):
        calls.append(mode)
        return {'status': 'completed', 'devices': [{'index': 0, 'is_gpu': False}]}
    assert probe.probe(runner)['status'] == 'no_verified_gpu'
    assert calls == ['inventory']


def test_gpu_outcome_is_used_and_dense_and_real_data_remain_unverified():
    def runner(mode, index=0):
        if mode == 'inventory':
            return probe.worker(mode, load=engine)
        return {'status': 'passed'}
    result = probe.probe(runner)
    assert result['status'] == 'passed'
    assert result['dataset'] == result['dense_reconstruction'] == 'not_tested'


def test_worker_timeout_does_not_emit_raw_native_output(monkeypatch):
    calls = []
    class Process:
        def communicate(self, timeout=None):
            calls.append(timeout)
            if timeout is not None:
                raise subprocess.TimeoutExpired('probe', timeout, output='private/path')
            return 'private/path', ''
        def kill(self):
            calls.append('kill')
    def launch(args, **kwargs):
        assert '-I' in args and kwargs['stdout'] == subprocess.PIPE
        return Process()
    monkeypatch.setattr(probe.subprocess, 'Popen', launch)
    assert probe.run_worker('matching') == {'status': 'timeout'}
    assert calls == [30, 'kill', None]


@pytest.mark.parametrize('output, code, expected', [
    ('noise\nSOLARCHECK_GPU_JSON={"status":"passed"}\n', 0, 'passed'),
    ('private/path', 1, 'worker_failed'), ('not json', 0, 'invalid_worker_output'),
    ('SOLARCHECK_GPU_JSON=[]', 0, 'invalid_worker_output')])
def test_worker_protocol_ignores_driver_noise_and_rejects_invalid_output(monkeypatch, output, code, expected):
    monkeypatch.setattr(probe.subprocess, 'Popen', lambda *a, **k: SimpleNamespace(
        communicate=lambda timeout: (output, ''), returncode=code))
    result = probe.run_worker('inventory')
    assert result['status'] == expected
    assert 'private/path' not in json.dumps(result)
