"""Real Windows debug/unwind contracts; no OpenSfM, GPU or images in CI."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'MCM_SolarCheck_OPENSFM_STACK_PRUEFUNG.py'
spec = importlib.util.spec_from_file_location('solarcheck_native_stack', SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def capture_json(**changes):
    result = {'status': 'captured', 'target_exit_code': 0xC0000005,
              'exception_code_hex': '0xC0000005',
              'frames': [{'module': 'ntdll.dll', 'offset': '0x24785'}]}
    result.update(changes)
    return json.dumps(result).encode()


def test_capture_is_not_gpu_success_and_retains_original_exit():
    result = probe.filtered_report(capture_json(), 0)
    assert result['status'] == 'captured'
    assert result['target_exit_code_hex'] == '0xC0000005'
    assert 'passed' not in json.dumps(result)


@pytest.mark.parametrize('row', [
    {'module': r'C:\private\example.dll', 'offset': '0x1'},
    {'module': '/private/example.dll', 'offset': '0x1'},
    {'module': 'example.dll', 'offset': '0x7FFFFFFF0000'},
    {'module': 'example.dll', 'offset': 'not-an-offset'},
    {'module': 'name with space.dll', 'offset': '0x1'},
])
def test_paths_and_absolute_addresses_never_escape(row):
    result = probe.filtered_report(capture_json(frames=[row]), 0)
    assert result == {'status': 'invalid_debugger_report'}
    assert 'private' not in json.dumps(result)


@pytest.mark.parametrize('changes,code', [
    ({'target_exit_code': 0}, 0),
    ({'target_exit_code': True}, 0),
    ({'exception_code_hex': '0x00000000'}, 0),
    ({'frames': [{}]}, 0),
    ({'frames': [dict(module='n.dll')] * 33}, 0),
    ({}, 3221225477),
])
def test_invalid_or_crashed_debugger_never_accepted(changes, code):
    assert probe.filtered_report(capture_json(**changes), code)['status'] == 'invalid_debugger_report'


def test_native_command_only_starts_known_inventory_worker(tmp_path, monkeypatch):
    work = tmp_path / 'synthetic'
    seen = []
    monkeypatch.setenv('_NT_SYMBOL_PATH', 'srv*https://example.invalid')
    monkeypatch.setenv('_NT_ALT_SYMBOL_PATH', r'C:\private-symbols')

    def run(command, **kwargs):
        seen.append(command)
        assert kwargs['env']['PROJ_NETWORK'] == 'OFF'
        assert kwargs['env']['MPLCONFIGDIR'] == str(work / 'matplotlib')
        assert not any(key.upper() in ('_NT_SYMBOL_PATH', '_NT_ALT_SYMBOL_PATH') for key in kwargs['env'])
        assert kwargs['timeout'] == 40
        return subprocess.CompletedProcess(command, 0, capture_json(), b'never forwarded')

    monkeypatch.setattr(probe.subprocess, 'run', run)
    result = probe.run_capture(work, 'owned-python.exe', 'known-probe.py')
    assert seen == [[str(work / 'stack.exe'), '--inventory', 'owned-python.exe',
                     'known-probe.py', str(work / 'symbols')]]
    assert result['target_exit_code'] == 0xC0000005


@pytest.mark.skipif(sys.platform != 'win32', reason='Real MSVC/Win32 Debug API required')
def test_real_native_compile_unhandled_av_clean_exit_and_owned_timeout(tmp_path):
    sdk = probe.load_buildtools()
    work = tmp_path / 'native-stack'
    work.mkdir()
    for name in ('temp', 'symbols', 'matplotlib'):
        (work / name).mkdir()
    compiled = probe.compile_helper(work, sdk)
    if compiled['status'] != 'compiled':
        # Only new synthetic CI build files, never a user/engine log.
        logs = '\n'.join((work / name).read_text(errors='replace')[-5000:]
                         for name in ('driver.log', 'build.log') if (work / name).is_file())
        pytest.fail(json.dumps(compiled) + '\n' + logs)
    av = probe.run_capture(work, synthetic='av')
    assert av['status'] == 'captured', av
    assert av['target_exit_code'] == 0xC0000005
    assert av['exception_code_hex'] == '0xC0000005'
    assert len(av['frames']) >= 2, av
    assert any(frame['module'].lower() == 'stack.exe' for frame in av['frames']), av
    assert any(frame['module'].lower() in ('kernelbase.dll', 'kernel32.dll', 'ntdll.dll')
               for frame in av['frames']), av
    assert 'offset' in av['frames'][0]
    clean = probe.run_capture(work, synthetic='clean')
    assert clean['status'] == 'clean_exit', clean
    assert clean['target_exit_code'] == 0
    assert clean['frames'] == []
    timeout = probe.run_capture(work, synthetic='timeout')
    assert timeout['status'] == 'timeout', timeout
    assert timeout['target_exit_code'] == 258
    assert timeout['frames'] == []
    assert not list(work.rglob('*.dmp'))
    assert list((work / 'symbols').iterdir()) == []
