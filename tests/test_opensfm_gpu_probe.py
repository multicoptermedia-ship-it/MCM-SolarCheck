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


def test_system_loader_is_preloaded_before_any_native_import(monkeypatch):
    order = []
    monkeypatch.setattr(probe, 'preload_system_opencl', lambda: order.append('system32'))
    def load():
        order.append('imports')
        return engine()
    assert probe.worker('inventory', load=load, system_opencl=True)['status'] == 'completed'
    assert order == ['system32', 'imports']


@pytest.mark.parametrize('existing_outside, loaded_outside', [(False, False), (True, False), (False, True)])
def test_system_loader_verifies_actual_module_path_and_never_changes_search_environment(tmp_path, existing_outside, loaded_outside):
    system = tmp_path / 'System32'
    expected = system / 'OpenCL.dll'
    outside = tmp_path / 'private' / 'OpenCL.dll'
    calls = []
    def system_directory(buffer, length):
        buffer.value = str(system)
        return len(buffer.value)
    def module_path(handle, buffer, length):
        buffer.value = str(outside if (handle == 9 or loaded_outside) else expected)
        return len(buffer.value)
    def module_handle(name):
        assert name == 'OpenCL.dll'
        return 9 if existing_outside else None
    kernel = SimpleNamespace(GetSystemDirectoryW=system_directory,
                             GetModuleFileNameW=module_path, GetModuleHandleW=module_handle)
    loader = SimpleNamespace(_handle=7)
    def load_dll(name, **kwargs):
        calls.append((name, kwargs))
        assert kwargs == {'winmode': 0x800}
        if name == 'kernel32.dll':
            return kernel
        assert name == str(expected).casefold()
        return loader
    if existing_outside or loaded_outside:
        with pytest.raises(RuntimeError, match='opencl_module_outside_system32'):
            probe.preload_system_opencl(load_dll)
    else:
        assert probe.preload_system_opencl(load_dll) is loader
    assert len(calls) == (1 if existing_outside else 2)


@pytest.mark.parametrize('checkpoint, result_written', [('dense_device_count', False), ('worker_complete', True)])
def test_native_access_violation_reports_stage_and_never_converts_partial_result_to_pass(monkeypatch, checkpoint, result_written):
    output = probe.STAGE_MARKER + checkpoint + '\n'
    if result_written:
        output = probe.MARKER + '{"status":"completed"}\n' + output
    def launch(args, **kwargs):
        assert '--system-opencl' in args and '-I' in args
        return SimpleNamespace(communicate=lambda timeout: (output, 'private/path'), returncode=3221225477)
    monkeypatch.setattr(probe.subprocess, 'Popen', launch)
    result = probe.run_worker('inventory', system_opencl=True)
    assert result['status'] == 'worker_failed'
    assert result['exit_code_hex'] == '0xC0000005'
    assert result['last_stage'] == checkpoint
    assert result['structured_result_written'] is result_written
    assert 'private/path' not in json.dumps(result)


def test_unknown_stage_never_leaks_driver_output():
    assert probe.last_stage(probe.STAGE_MARKER + 'private/path') == {}


def test_truncated_json_after_crash_is_not_reported_as_a_completed_result(monkeypatch):
    monkeypatch.setattr(probe.subprocess, 'Popen', lambda *a, **k: SimpleNamespace(
        communicate=lambda timeout: (probe.MARKER + '{"status":', ''), returncode=3221225477))
    result = probe.run_worker('inventory')
    assert result['status'] == 'worker_failed'
    assert result['structured_result_written'] is False
