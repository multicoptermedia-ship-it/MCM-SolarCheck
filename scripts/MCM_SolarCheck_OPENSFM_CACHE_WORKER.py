"""Bounded local read of saved depthmaps via the installed OpenSfM loaders.

No matching, reconstruction, cleaning, repair or cache deletion is performed.
The parent owns the time limit and the fresh inspection output directory.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import sys

ENGINE_SOURCE = '8b6b77efddebf4429044d3206c7dc21c4e767e08'


def regular(path):
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('regular_local_file_required')
    return path


def snapshot(directory):
    result = {}
    for kind in ('raw', 'clean'):
        for path in directory.glob('*.' + kind + '.npz'):
            stat = regular(path).stat()
            result[path.name] = (stat.st_size, stat.st_mtime_ns)
    return result


def array_format(depth, normal, score, confidence):
    shape = getattr(depth, 'shape', ())
    if (len(shape) != 2 or any(not 0 < n <= 4000 for n in shape)
            or depth.dtype.kind != 'f' or getattr(normal, 'shape', ()) != (*shape, 3)
            or normal.dtype.kind != 'f'):
        raise ValueError('cache_array_format')
    for value in (score, confidence):
        if value is not None and (getattr(value, 'shape', ()) != shape or value.dtype.kind != 'f'):
            raise ValueError('cache_array_format')


def inspect_cache(workspace, data):
    """Only aggregate structural/readability facts, never names or coordinates."""
    workspace = Path(workspace)
    directory = workspace / 'undistorted' / 'depthmaps'
    for path in (directory, *directory.parents):
        if path.is_symlink():
            raise ValueError('linked_dataset_refused')
    working = set(data.images())  # Existing working filenames, no image decode.
    if not 3 <= len(working) <= 300 or any(not re.fullmatch(r'[0-9]{6}[.]JPG', s) for s in working):
        raise ValueError('unexpected_working_names')
    undistorted = data.undistorted_dataset()
    # Upstream may append its output format, e.g. 000001.JPG -> 000001.JPG.jpg.
    # Its saved mapping is authoritative; never guess by changing extensions.
    mapping = undistorted.load_undistorted_shot_ids()
    if (not isinstance(mapping, dict) or set(mapping) != working
            or any(not isinstance(ids, list) or len(ids) != 1
                   or not isinstance(ids[0], str) or ids[0] in ('.', '..')
                   or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', ids[0]) for ids in mapping.values())):
        raise ValueError('invalid_saved_undistorted_mapping')
    expected = {ids[0] for ids in mapping.values()}
    if len(expected) != len(working):
        raise ValueError('duplicate_saved_undistorted_ids')
    clusters = undistorted.load_clusters()
    if (not isinstance(clusters, list) or not clusters or len(clusters) > 300
            or any(not isinstance(c, list) or not c or len(c) > 300
                   or any(not isinstance(s, str) or s not in expected for s in c) for c in clusters)):
        raise ValueError('invalid_saved_clusters')
    before = snapshot(directory)
    good = {'raw': set(), 'clean': set()}
    report = {'check': 'solarcheck-opensfm-cache-1', 'status': 'completed',
              'working_images': len(working), 'clusters': len(clusters),
              'raw_readable': 0, 'raw_unreadable': 0, 'clean_readable': 0, 'clean_unreadable': 0,
              'foreign_cache_files': 0, 'changed_during_check': False,
              'geometric_quality_verified': False, 'resume_implemented': False}
    for kind in ('raw', 'clean'):
        suffix = '.' + kind + '.npz'
        for name in sorted(before):
            if not name.endswith(suffix):
                continue
            shot = name[:-len(suffix)]
            if shot not in expected:
                report['foreign_cache_files'] += 1
                continue
            try:
                if kind == 'raw':
                    depth, normal, _score, _neighbors, _names, confidence = undistorted.load_raw_depthmap(shot)
                    array_format(depth, normal, None, confidence)
                else:
                    depth, normal, score, confidence = undistorted.load_clean_depthmap(shot)
                    array_format(depth, normal, score, confidence)
                good[kind].add(shot)
                report[kind + '_readable'] += 1
                del depth, normal, confidence
            except Exception:
                # A killed parallel writer may leave an incomplete file. Preserve it.
                report[kind + '_unreadable'] += 1
    report['changed_during_check'] = before != snapshot(directory)
    available = good['raw'] | good['clean']
    report['clusters_fully_cached'] = sum(set(c) <= available for c in clusters)
    report['clusters_partly_cached'] = sum(bool(set(c) & available) and not set(c) <= available for c in clusters)
    report['clusters_without_cache'] = len(clusters) - report['clusters_fully_cached'] - report['clusters_partly_cached']
    report['clustered_images'] = len(set().union(*map(set, clusters)))
    if (report['raw_unreadable'] or report['clean_unreadable'] or report['foreign_cache_files']
            or report['changed_during_check']):
        report['status'] = 'attention_required'
    return report


def main():
    if not sys.flags.isolated or struct.calcsize('P') != 8 or len(sys.argv) != 3:
        raise ValueError('isolated_owned_check_required')
    workspace, output = map(Path, sys.argv[1:])
    if (not workspace.is_absolute() or output.parent != workspace
            or not re.fullmatch(r'cache-check-[a-z0-9_]{8}', output.name)
            or not output.is_dir() or (output / 'worker-result.json').exists()
            or any(p.is_symlink() for p in (output, *output.parents))):
        raise ValueError('fresh_owned_check_directory_required')
    manifest = json.loads(regular(workspace / 'job.json').read_text(encoding='utf-8'))
    if manifest.get('expected_engine_source') != ENGINE_SOURCE or manifest.get('status') == 'running':
        raise ValueError('stopped_opensfm_job_required')
    regular(workspace / 'config.yaml')
    before = {name: regular(workspace / name).read_bytes() for name in ('job.json', 'config.yaml')}
    os.environ.update(TEMP=str(output), TMP=str(output), MPLCONFIGDIR=str(output), PROJ_NETWORK='OFF')
    helper = Path(__file__).with_name('MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py')
    spec = importlib.util.spec_from_file_location('solarcheck_cache_loader', helper)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    runtime = loader.preload_system_opencl() if sys.platform == 'win32' else None
    loader.load_engine(cli_imports=True)
    from opensfm.dataset import DataSet
    data = DataSet(str(workspace))
    try:
        report = inspect_cache(workspace, data)
    finally:
        data.clean_up()
    if any(regular(workspace / name).read_bytes() != value for name, value in before.items()):
        report.update(status='attention_required', changed_during_check=True)
    # Presence of this file alone is never success; the parent also requires exit 0.
    with (output / 'worker-result.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)


if __name__ == '__main__':
    main()
