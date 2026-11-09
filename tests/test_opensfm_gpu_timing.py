"""Startup/native deadline contracts, including real isolated subprocesses."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
spec = importlib.util.spec_from_file_location('opensfm_gpu_timing_probe', SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ScheduledProcess:
    """Synthetic process timeline, independent of the supervising deadlines."""
    def __init__(self, ready, finish, marker=None):
        self.now = 0.0
        self.ready, self.finish = ready, finish
        self.marker = marker or probe.STAGE_MARKER + 'engine_ready'
        self.killed = False
        self.returncode = None

    def output(self):
        result = probe.STAGE_MARKER + 'official_cli_imports\n'
        if self.now >= self.ready:
            result += self.marker + '\n'
        if self.now >= self.finish:
            result += probe.MARKER + '{"status":"completed"}\n'
        return result

    def communicate(self, timeout=None):
        if timeout is None:
            assert self.killed
            return self.output(), 'private/path must never be emitted'
        if self.finish <= self.now + timeout:
            self.now = self.finish
            self.returncode = 0
            return self.output(), ''
        self.now += timeout
        # Real Popen timeout output may be bytes even with text=True.
        raise subprocess.TimeoutExpired('synthetic', timeout, output=self.output().encode())

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_slow_imports_and_native_work_have_independent_budgets():
    process = ScheduledProcess(ready=3, finish=4.5)
    output, phase = probe.communicate_with_phase_limits(
        process, startup_seconds=4, native_seconds=2, clock=lambda: process.now)
    assert phase is None and not process.killed
    assert process.now == 4.5  # Beyond the original startup deadline, valid native budget.
    assert probe.read_report(output)['status'] == 'completed'


def test_slow_or_blocked_import_still_stops_at_startup_deadline():
    process = ScheduledProcess(ready=9, finish=10)
    output, phase = probe.communicate_with_phase_limits(
        process, startup_seconds=3, native_seconds=2, clock=lambda: process.now)
    assert phase == 'startup' and process.killed
    assert process.now == pytest.approx(3)
    assert probe.last_stage(output)['last_stage'] == 'official_cli_imports'


def test_repeated_readiness_output_never_resets_native_deadline():
    process = ScheduledProcess(ready=0.5, finish=100)
    output, phase = probe.communicate_with_phase_limits(
        process, startup_seconds=4, native_seconds=1, clock=lambda: process.now)
    assert phase == 'native' and process.killed
    assert 1.5 <= process.now <= 1.7
    assert probe.last_stage(output)['last_stage'] == 'engine_ready'


@pytest.mark.parametrize('marker', [
    probe.STAGE_MARKER + 'engine_ready_extra',
    'noise' + probe.STAGE_MARKER + 'engine_ready',
    probe.STAGE_MARKER + 'private/path',
])
def test_only_exact_readiness_marker_can_change_phase(marker):
    process = ScheduledProcess(ready=0, finish=100, marker=marker)
    _output, phase = probe.communicate_with_phase_limits(
        process, startup_seconds=0.5, native_seconds=2, clock=lambda: process.now)
    assert phase == 'startup' and process.killed
    assert process.now == pytest.approx(0.5)


def test_phase_timeout_reports_import_limit_and_never_runs_matching(monkeypatch):
    process = ScheduledProcess(ready=150, finish=200)
    monkeypatch.setattr(probe.subprocess, 'Popen', lambda *args, **kwargs: process)
    supervisor = probe.communicate_with_phase_limits
    monkeypatch.setattr(probe, 'communicate_with_phase_limits',
                        lambda child, **kwargs: supervisor(child, clock=lambda: child.now, **kwargs))
    calls = []
    def runner(mode, index=0):
        calls.append(mode)
        return probe.run_worker(mode, index, phase_timeouts=True)
    result = probe.probe(runner)
    assert calls == ['inventory']
    assert result['status'] == 'inventory_failed'
    assert result['inventory'] == {'status': 'timeout', 'timeout_phase': 'startup',
                                   'limit_seconds': 120, 'last_stage': 'official_cli_imports'}
    assert 'private/path' not in json.dumps(result)


def test_phase_supervision_never_accepts_json_after_process_crash(monkeypatch):
    payload = probe.MARKER + '{"status":"completed","devices":[{"is_gpu":true}]}\n'
    process = SimpleNamespace(returncode=3221225477)
    monkeypatch.setattr(probe.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(probe, 'communicate_with_phase_limits', lambda child, **kwargs: (payload, None))
    result = probe.run_worker('inventory', phase_timeouts=True)
    assert result['status'] == 'worker_failed'
    assert result['exit_code_hex'] == '0xC0000005'
    assert result['before_exit']['accepted_as_success'] is False


def test_cli_uses_phase_limits_for_inventory_and_matching_and_reports_budgets(monkeypatch, capsys):
    monkeypatch.setattr(probe, 'sys', SimpleNamespace(platform='win32',
        version_info=(3, 10), flags=SimpleNamespace(isolated=True)))
    calls = []
    def runner(mode, index, system, cli, *, phase_timeouts):
        calls.append((mode, index, system, cli, phase_timeouts))
        if mode == 'inventory':
            return {'status': 'completed', 'devices': [{'index': 0, 'is_gpu': True}]}
        return {'status': 'passed'}
    monkeypatch.setattr(probe, 'run_worker', runner)
    assert probe.main(['--system-opencl', '--cli-imports', '--phase-timeouts']) == 0
    report = json.loads(capsys.readouterr().out.split('\n', 1)[1])
    assert report['time_limits_seconds'] == {'startup': 120, 'native_including_shutdown': 30}
    assert report['dataset'] == report['dense_reconstruction'] == 'not_tested'
    assert calls == [('inventory', 0, True, True, True), ('matching', 0, True, True, True)]


@pytest.mark.parametrize('mode,expected', [('finish', None), ('native_hang', 'native'),
                                          ('startup_hang', 'startup')])
def test_actual_subprocess_pipe_retries_and_owned_timeout(mode, expected, tmp_path):
    # Runs on Windows CI and Linux with only an owned isolated Python process.
    ready = tmp_path / 'ready'
    code = ('import time\nfrom pathlib import Path\n'
            f'print({(probe.STAGE_MARKER + "official_cli_imports")!r}, flush=True)\n')
    if mode == 'startup_hang':
        code += 'time.sleep(10)\n'
    else:
        code += 'time.sleep(0.2)\n'
        code += f'Path({str(ready)!r}).write_bytes({probe.READY_TOKEN!r})\n'
        code += f'print({(probe.STAGE_MARKER + "engine_ready")!r}, flush=True)\n'
        code += 'time.sleep(0.3)\n' if mode == 'finish' else 'time.sleep(10)\n'
        payload = probe.MARKER + json.dumps({'status': 'completed'})
        code += f'print({payload!r}, flush=True)\n' 
    process = subprocess.Popen([sys.executable, '-I', '-u', '-c', code],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8')
    try:
        output, phase = probe.communicate_with_phase_limits(process,
            startup_seconds=0.5 if mode == 'startup_hang' else 10,
            native_seconds=1 if mode == 'finish' else 0.2,
            is_ready=lambda: probe.ready_file_written(ready))
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    assert phase == expected
    if expected:
        assert process.returncode != 0
    else:
        assert process.returncode == 0
        assert probe.read_report(output)['status'] == 'completed'


def test_windows_style_buffering_still_starts_native_budget():
    process = ScheduledProcess(ready=0.3, finish=10)
    # Windows communicate timeouts provide no partial stdout to the supervisor.
    communicate = process.communicate
    def buffered(timeout=None):
        try:
            return communicate(timeout)
        except subprocess.TimeoutExpired as error:
            error.output = None
            raise
    process.communicate = buffered
    _output, phase = probe.communicate_with_phase_limits(process,
        startup_seconds=2, native_seconds=0.5, clock=lambda: process.now,
        is_ready=lambda: process.now >= process.ready)
    assert phase == 'native' and process.killed
    assert 0.8 <= process.now <= 1.0


def test_ready_signal_is_exclusive_adjacent_and_precedes_device_access(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, '__file__', str(tmp_path / 'probe.py'))
    directory = tmp_path / 'gpu-start-synthetic'
    directory.mkdir()
    ready = directory / 'ready'
    def count():
        assert ready.read_bytes() == probe.READY_TOKEN
        return 0
    features = SimpleNamespace(opencl_num_devices=count)
    dense = SimpleNamespace(DepthmapClusterEstimator=SimpleNamespace(num_devices=count))
    load = lambda: (None, features, dense)
    assert probe.worker('inventory', load=load, ready_file=str(ready))['status'] == 'completed'
    assert probe.worker('inventory', load=load, ready_file=str(ready))['status'] == 'native_check_failed'
    assert ready.read_bytes() == probe.READY_TOKEN
    outside = tmp_path / 'must-not-be-written'
    assert probe.worker('inventory', load=load, ready_file=str(outside))['status'] == 'native_check_failed'
    assert not outside.exists()


def test_phase_scope_passes_ready_path_and_removes_only_own_signal(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, '__file__', str(tmp_path / 'probe.py'))
    sentinel = tmp_path / 'keep-existing-file'
    sentinel.write_bytes(b'keep')
    def launch(args, **kwargs):
        ready = Path(args[args.index('--ready-file') + 1])
        assert ready.parent.parent == tmp_path
        assert ready.parent.name.startswith('gpu-start-')
        ready.write_bytes(probe.READY_TOKEN)
        return SimpleNamespace(returncode=0)
    def supervise(child, *, is_ready):
        assert is_ready() is True
        return probe.MARKER + '{"status":"completed"}', None
    monkeypatch.setattr(probe.subprocess, 'Popen', launch)
    monkeypatch.setattr(probe, 'communicate_with_phase_limits', supervise)
    assert probe.run_worker('inventory', phase_timeouts=True)['status'] == 'completed'
    assert list(tmp_path.iterdir()) == [sentinel]
