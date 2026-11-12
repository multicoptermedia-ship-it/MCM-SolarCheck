"""Thin isolated entry adapter to the installed upstream OpenSfM command runner.

Invoked in the pilot's own fresh or explicitly continued private dataset. No algorithms,
downloads, guessed calibration or project/SQLite access live in this adapter.
"""
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import re
import struct
import sys


STAGES = ('extract_metadata', 'detect_features', 'match_features', 'create_tracks',
          'reconstruct', 'undistort', 'dense_clustering', 'compute_depthmaps',
          'fuse_depthmaps', 'dense_merging')


def main():
    if (not sys.flags.isolated or struct.calcsize('P') != 8 or len(sys.argv) not in (3, 4)
            or sys.argv[1] not in STAGES):
        raise RuntimeError('unsupported_stage_call')
    if sys.argv[3:] != (['--georeferenced'] if sys.argv[1] == 'dense_merging' else []):
        raise RuntimeError('unsupported_stage_arguments')
    dataset = Path(sys.argv[2])
    owned_name = (dataset.name.startswith('opensfm-rgb-') or re.fullmatch(
        r'[0-9]{8}_[0-9]{6}_OpenSfM_RGB_[A-Za-z0-9-]{1,32}_[a-z0-9_]{8}', dataset.name))
    if (not dataset.is_absolute() or not owned_name
            or not (dataset / 'job.json').is_file() or not (dataset / 'config.yaml').is_file()):
        raise RuntimeError('owned_dataset_required')
    for name in ('tmp', 'matplotlib'):
        (dataset / name).mkdir(exist_ok=True)
    os.environ.update(TEMP=str(dataset / 'tmp'), TMP=str(dataset / 'tmp'),
                      MPLCONFIGDIR=str(dataset / 'matplotlib'), PROJ_NETWORK='OFF')
    # Reuse the qualified loader/import path; never run the GPU setup probe.
    probe_file = Path(__file__).resolve().with_name('MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py')
    spec = importlib.util.spec_from_file_location('solarcheck_opensfm_loader', probe_file)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    runtime = loader.preload_system_opencl() if sys.platform == 'win32' else None
    _numpy, features, _dense = loader.load_engine(cli_imports=True)
    if sys.argv[1] == 'match_features' and not features.opencl_matching_available():
        raise RuntimeError('qualified_gpu_matching_unavailable')
    from opensfm import commands
    from opensfm.dataset import DataSet

    @contextmanager
    def create_dataset(path, dataset_type='opensfm'):
        data = DataSet(path)
        try:
            yield data
        finally:
            data.clean_up()

    commands.command_runner(commands.opensfm_commands, create_dataset, dataset_choices=['opensfm'])


if __name__ == '__main__':
    main()
