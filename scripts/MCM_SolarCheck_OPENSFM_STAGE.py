"""Thin isolated entry adapter to the installed upstream OpenSfM command runner.

Invoked in the pilot's own fresh or explicitly continued private dataset. No algorithms,
downloads, guessed calibration or project/SQLite access live in this adapter.
"""
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import sys


STAGES = ('extract_metadata', 'detect_features', 'match_features', 'create_tracks',
          'reconstruct', 'undistort', 'dense_clustering', 'compute_depthmaps',
          'fuse_depthmaps', 'dense_merging')


def match_missing(data, folder):
    """Native pair selection/matching only; merge serialized records, never poses."""
    from opensfm import matching, pairs_selection
    manifest = json.loads((folder / 'job.json').read_text(encoding='utf-8'))
    targets = manifest.get('bridge_plan', {}).get('target_names', [])
    images = data.images()
    if (manifest.get('pipeline') != 'opensfm_thermal' or not isinstance(targets, list)
            or not 1 <= len(targets) <= 20 or len(set(targets)) != len(targets)
            or not set(targets) < set(images) or not 3 <= len(images) <= 300
            or any(not isinstance(n, str) or not re.fullmatch(r'[0-9]{6}[.]JPG', n) for n in images)
            or any(not data.features_exist(n) for n in images)):
        raise RuntimeError('invalid_thermal_bridge_plan')
    exifs = {name: data.load_exif(name) for name in images}
    selection = dict.fromkeys(('matching_gps_distance', 'matching_gps_neighbors',
        'matching_time_neighbors', 'matching_order_neighbors', 'matching_bow_neighbors',
        'matching_vlad_neighbors', 'matching_graph_rounds'), 0)
    pairs, _ = pairs_selection.match_candidates_from_metadata(targets, images, exifs, data, selection)
    if (len(pairs) > 6000 or len(set(pairs)) != len(pairs) or any(a not in targets or b not in images or a == b for a, b in pairs)):
        raise RuntimeError('invalid_native_bridge_pairs')
    existing = {name: data.load_matches(name) if data.matches_exists(name) else {} for name in images}
    if any(not isinstance(value, dict) or not set(value) <= set(images) for value in existing.values()):
        raise RuntimeError('invalid_saved_matches')
    fresh = [(a, b) for a, b in pairs if b not in existing[a] and a not in existing[b]]
    results = matching.match_images_with_pairs(data, {}, exifs, fresh) if fresh else {}
    if set(results) != set(fresh):
        raise RuntimeError('incomplete_native_bridge_results')
    changed = set()
    for (a, b), matches in results.items():
        existing[a][b] = matches
        changed.add(a)
    for name in changed:
        data.save_matches(name, existing[name])
    matching.clear_cache()
    result = dict(status='finished', target_images=len(targets), candidate_pairs=len(pairs),
        previous_pairs_skipped=len(pairs) - len(fresh), new_pairs=len(fresh),
        matched_pairs=sum(len(value) > 0 for value in results.values()))
    with (folder / 'matching-supplement.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)


def main():
    if (not sys.flags.isolated or struct.calcsize('P') != 8 or len(sys.argv) not in (3, 4)
            or sys.argv[1] not in (*STAGES, 'match_missing')):
        raise RuntimeError('unsupported_stage_call')
    if sys.argv[3:] != (['--georeferenced'] if sys.argv[1] == 'dense_merging' else []):
        raise RuntimeError('unsupported_stage_arguments')
    dataset = Path(sys.argv[2])
    owned_name = (dataset.name.startswith('opensfm-rgb-') or re.fullmatch(
        r'[0-9]{8}_[0-9]{6}_OpenSfM_(?:RGB|THERMAL)_[A-Za-z0-9-]{1,32}_[a-z0-9_]{8}', dataset.name))
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
    if sys.argv[1] in ('match_features', 'match_missing') and not features.opencl_matching_available():
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

    if sys.argv[1] == 'match_missing':
        with create_dataset(str(dataset)) as data:
            match_missing(data, dataset)
        return
    commands.command_runner(commands.opensfm_commands, create_dataset, dataset_choices=['opensfm'])


if __name__ == '__main__':
    main()
