"""Actual isolated CLI dispatch against an inert fake installed engine API."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import venv

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def isolated_engine(tmp_path_factory):
    folder = tmp_path_factory.mktemp('opensfm-cli-contract')
    prefix = folder / 'environment'
    venv.EnvBuilder(with_pip=False).create(prefix)
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    result = subprocess.run([str(python), '-I', '-c',
        'import sysconfig; print(sysconfig.get_path("purelib"))'],
        capture_output=True, text=True, check=True, timeout=30)
    package = Path(result.stdout.strip()) / 'opensfm'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'commands.py').write_text('''import json, os, sys
from pathlib import Path
opensfm_commands = ['synthetic']
def command_runner(commands, factory, dataset_choices):
    assert commands == ['synthetic'] and dataset_choices == ['opensfm']
    with factory(sys.argv[2], 'opensfm') as data:
        result = {'argv': sys.argv[1:], 'isolated': sys.flags.isolated,
                  'proj_network': os.environ['PROJ_NETWORK'],
                  'temp_owned': Path(os.environ['TEMP']).parent == data.path,
                  'cache_owned': Path(os.environ['MPLCONFIGDIR']).parent == data.path}
        (data.path / 'dispatch.json').write_text(json.dumps(result))
        if os.environ.get('SOLARCHECK_SYNTHETIC_FAIL') == '1':
            raise RuntimeError('synthetic failure')
''')
    (package / 'dataset.py').write_text('''from pathlib import Path
class DataSet:
    def __init__(self, path): self.path = Path(path)
    def clean_up(self): (self.path / 'cleanup.txt').write_text('done')
''')
    scripts = folder / 'adapter scripts'
    scripts.mkdir()
    runner = scripts / 'MCM_SolarCheck_OPENSFM_STAGE.py'
    shutil.copyfile(ROOT / 'scripts' / runner.name, runner)
    # This test replaces only the external loader boundary, not CLI dispatch.
    (scripts / 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py').write_text('''import os
from types import SimpleNamespace
def preload_system_opencl(): return object()
def load_engine(cli_imports=False):
    assert cli_imports
    return None, SimpleNamespace(opencl_matching_available=lambda:
        os.environ.get('SOLARCHECK_SYNTHETIC_GPU_UNAVAILABLE') != '1'), None
''')
    return python, runner


def owned_dataset(tmp_path):
    folder = tmp_path / 'opensfm-rgb-synthetic'
    folder.mkdir()
    (folder / 'job.json').write_text('{}')
    (folder / 'config.yaml').write_text('{"proj_cdn_enabled":false}')
    return folder


@pytest.mark.parametrize('stage,extra', [('extract_metadata', []), ('dense_merging', ['--georeferenced'])])
def test_actual_isolated_cli_delegates_and_cleans_up(isolated_engine, tmp_path, stage, extra):
    python, runner = isolated_engine
    folder = owned_dataset(tmp_path)
    result = subprocess.run([str(python), '-I', str(runner), stage, str(folder), *extra],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads((folder / 'dispatch.json').read_text())
    assert report['argv'] == [stage, str(folder), *extra]
    assert report['isolated'] and report['proj_network'] == 'OFF'
    assert report['temp_owned'] and report['cache_owned']
    assert (folder / 'cleanup.txt').read_text() == 'done'


def test_actual_dispatch_error_still_runs_upstream_dataset_cleanup(isolated_engine, tmp_path):
    python, runner = isolated_engine
    folder = owned_dataset(tmp_path)
    env = {**os.environ, 'SOLARCHECK_SYNTHETIC_FAIL': '1'}
    result = subprocess.run([str(python), '-I', str(runner), 'reconstruct', str(folder)],
                            env=env, capture_output=True, timeout=30)
    assert result.returncode != 0
    assert (folder / 'cleanup.txt').read_text() == 'done'


def test_time_first_project_folder_is_accepted_by_isolated_stage_adapter(isolated_engine, tmp_path):
    python, runner = isolated_engine
    folder = owned_dataset(tmp_path)
    renamed = folder.with_name('20261110_204300_OpenSfM_RGB_Demo-Projekt_abc12345')
    folder.rename(renamed)
    result = subprocess.run([str(python), '-I', str(runner), 'extract_metadata', str(renamed)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert (renamed / 'dispatch.json').exists()


def test_missing_gpu_cannot_silently_switch_pilot_to_cpu_matching(isolated_engine, tmp_path):
    python, runner = isolated_engine
    folder = owned_dataset(tmp_path)
    env = {**os.environ, 'SOLARCHECK_SYNTHETIC_GPU_UNAVAILABLE': '1'}
    result = subprocess.run([str(python), '-I', str(runner), 'match_features', str(folder)],
                            env=env, capture_output=True, timeout=30)
    assert result.returncode != 0 and not (folder / 'dispatch.json').exists()


@pytest.mark.parametrize('arguments', [[], ['run_all', 'unused'], ['dense_merging', 'unused'],
                                      ['extract_metadata', 'unused', '--georeferenced']])
def test_only_explicit_standard_stages_and_owned_data_are_dispatched(isolated_engine, arguments):
    python, runner = isolated_engine
    result = subprocess.run([str(python), '-I', str(runner), *arguments],
                            capture_output=True, timeout=30)
    assert result.returncode != 0
