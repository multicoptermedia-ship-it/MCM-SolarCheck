"""Explicit bounded PUBLIC PVIS research training in the existing Torch CPU pilot."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path[:0] = [str(Path(__file__).resolve().parent),
                 str(Path(__file__).resolve().parents[1]/'src')]
from MCM_SolarCheck_CVUT_PAKETPRUEFUNG import atomic_json, digest, local, package_lock
import MCM_SolarCheck_PVIS_BILDADAPTER as audited
from mcm_solarcheck.services import pvis_public_training_data as data

MARKER = 'solarcheck-pvis-public-training-root-1'


def _root(prefix):
    root = local(prefix)
    marker = local(root/'public-training.json')
    if root.exists() and any(root.iterdir()):
        if not marker.is_file() or audited._json(marker) != {'check': MARKER}:
            raise ValueError('Own empty public training folder required')
    root.mkdir(parents=True, exist_ok=True)
    if not marker.exists(): atomic_json(marker, {'check': MARKER})
    return root


def _package(root, package_id):
    if not isinstance(package_id, str) or len(package_id) != 64 or any(c not in '0123456789abcdef' for c in package_id):
        raise ValueError('Invalid public package ID')
    folder = local(root/'packages'/package_id)
    manifest = data.validate_manifest(audited._json(folder/'package.json'))
    if manifest['preparation_id'] != package_id or digest(local(folder/'data.npz')) != manifest['data_sha256']:
        raise ValueError('Public numeric package changed')
    return folder, manifest


def prepare_package(source_prefix, prefix, *, should_cancel=lambda: False):
    """App-Python creates immutable primitive arrays, bridging both NumPy runtimes."""
    import numpy as np
    from mcm_solarcheck.services import pvis_image_adapter as pixels
    source = local(source_prefix)
    state = audited.audit(source, show=True, should_cancel=should_cancel)
    root = _root(prefix)
    with package_lock(source, 'pvis-package.lock'), package_lock(root, 'pvis-training.lock'):
        if audited._json(source/audited.REPORT) != state:
            raise ValueError('Source audit changed while preparing pixels')
        config = dict(adapter_id=state['adapter_id'], adapter_manifest_sha256=state['manifest_sha256'],
            partition_sha256=state['partition_sha256'], profile=data.PROFILE, size=data.SIZE,
            samples_per_split=data.SAMPLES, seed=data.SEED,
            producer_source_sha256=dict(data=digest(Path(data.__file__)), runner=digest(Path(__file__))))
        package_id = data.fingerprint(config)
        folder = local(root/'packages'/package_id)
        if (folder/'package.json').exists(): return root, package_id, _package(root, package_id)[1]
        if shutil.disk_usage(root).free < 400_000_000: raise OSError(28, 'Public training pilot needs 400MB free')
        journal = local(source/audited.FOLDER/state['adapter_id'])
        completed = audited._json(journal/'completed.json')
        candidates = dict(train=[], validation=[])
        records = {}
        for name, expected in completed['records'].items():
            if digest(local(journal/name)) != expected: raise ValueError('Source image journal changed')
            record = audited._json(journal/name)
            if record['eligible']:
                role = record['split']
                rank = sha256(f'{data.SEED}:{record["station"]}:{record["image_id"]}'.encode()).hexdigest()
                candidates[role].append((rank, name, record))
        for role in candidates:
            candidates[role].sort()
            if len(candidates[role]) < data.SAMPLES: raise ValueError('Not enough verified public crops')
            for _, name, record in candidates[role][:data.SAMPLES]:
                records[(record['station'], record['image_id'])] = (name, record)
        arrays, selections = {}, {}
        for spec, role, archive, image, annotations in audited._sources(source):
            audited.reference._cancel(should_cancel)
            key = (spec.station, image['id'])
            if key not in records: continue
            name, expected = records[key]
            filename = image['file_name']
            filename = filename if filename.startswith('images/') else 'images/'+filename
            image_info = archive.getinfo(spec.prefix+filename)
            if image_info.file_size > pixels.MAX_JPEG: raise ValueError('Public JPEG exceeds size bound')
            sample = pixels.load_sample(archive.read(image_info), image, annotations,
                station=spec.station, split=role, should_cancel=should_cancel)
            if sample.record != expected: raise ValueError('App-runtime crop differs from visually reviewed audit')
            arrays[name] = data.training_arrays(sample.rgb, sample.instances)
            selections[name] = dict(sample_id=name, station=spec.station, split=role,
                source_record_sha256=expected['record_sha256'])
        ordered = [name for role in ('train', 'validation') for _, name, _ in candidates[role][:data.SAMPLES]]
        if set(arrays) != set(ordered): raise ValueError('Selected public input missing')
        folder.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, suffix='.next', delete=False) as stream:
                temporary = Path(stream.name)
                np.savez(stream, rgb=np.stack([arrays[n][0] for n in ordered]),
                         instances=np.stack([arrays[n][1] for n in ordered]))
            audited.reference._cancel(should_cancel)
            temporary.replace(local(folder/'data.npz'))
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
        manifest = data.seal_manifest(dict(check=data.CHECK, preparation_id=package_id, config=config,
            scope='explicit_public_pvis_research_only', source_url=data.SOURCE, dataset_version='1.0.0',
            label_policy='pvis-projected-whole-module-1', profile=data.PROFILE, size=data.SIZE,
            license_declared='CC-BY-4.0', license_decision='unreviewed', commercial_training_approved=False,
            synthetic_only=False, test_images=0, customer_images=0,
            split_counts=dict(train=data.SAMPLES, validation=data.SAMPLES),
            samples=[selections[n] for n in ordered], data_sha256=digest(folder/'data.npz')))
        data.read_arrays(folder/'data.npz', manifest)
        audited.reference._cancel(should_cancel)
        atomic_json(local(folder/'package.json'), manifest)
        return root, package_id, manifest


def show(prefix):
    from mcm_solarcheck.services.pvis_instance_training import read_report
    root = local(prefix)
    with package_lock(root, 'pvis-training.lock'):
        latest = audited._json(local(root/'latest.json'))
        _, manifest = _package(root, latest['package_id'])
        run_id = latest['run_id']
        if not isinstance(run_id, str) or len(run_id) != 64 or any(c not in '0123456789abcdef' for c in run_id):
            raise ValueError('Invalid public run ID')
        report = read_report(local(root/'runs'/run_id), run_id)
        if (report['dataset_id'] != manifest['dataset_id'] or report['synthetic_only'] is not False
                or report['weights_sha256'] != latest['weights_sha256']):
            raise ValueError('Published public run differs from data package')
        return report


def worker(prefix, package_id, reference_prefix):
    from mcm_solarcheck.services.pvis_instance_training import run_training
    root, reference_root = _root(prefix), local(reference_prefix)
    with package_lock(root, 'pvis-training.lock'):
        folder, manifest = _package(root, package_id)
        result = run_training(folder/'data.npz', manifest, reference_root, local(root/'runs'))
        atomic_json(local(root/'latest.json'), dict(package_id=package_id, run_id=result['run_id'],
                                                  weights_sha256=result['weights_sha256']))
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-prefix', default=r'E:\SolarCheck-PVIS-Referenz')
    parser.add_argument('--torch-prefix', default=r'E:\SolarCheck-CVUT-KI-Pilot')
    parser.add_argument('--prefix', default=r'E:\SolarCheck-PVIS-Training')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--run-public-pilot', action='store_true')
    modes.add_argument('--show', action='store_true')
    modes.add_argument('--worker', metavar='PACKAGE_ID', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.show: result = show(args.prefix)
        elif args.worker: result = worker(args.prefix, args.worker, args.torch_prefix)
        else:
            ref = local(args.torch_prefix)
            executable = ref/('env/Scripts/python.exe' if os.name == 'nt' else 'env/bin/python')
            if not executable.is_file() or any(p.is_symlink() for p in executable.parents):
                raise FileNotFoundError('Existing Torch CPU runtime required')
            root, package_id, _ = prepare_package(args.source_prefix, args.prefix)
            command = [str(executable), str(Path(__file__).resolve()), '--worker', package_id,
                       '--prefix', str(root), '--torch-prefix', str(ref)]
            child = subprocess.Popen(command)
            try: return child.wait()
            except KeyboardInterrupt:
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.terminate(); child.wait(timeout=10)
                raise
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        return 0
    except KeyboardInterrupt:
        code, status = 'CANCELLED_CHECKPOINT_RETAINED', 'cancelled'
    except Exception as error:
        code = ('EXISTING_RUNTIME_MISSING' if isinstance(error, (ImportError, FileNotFoundError))
                else 'PUBLIC_TRAINING_VERIFICATION_FAILED' if isinstance(error, ValueError)
                else 'LOCAL_IO' if isinstance(error, OSError) else 'PUBLIC_TRAINING_FAILED')
        status = 'failed'
    print(json.dumps(dict(check='solarcheck-pvis-public-training-failure-1', status=status,
        error_code=code, customer_training_started=False, model_updated=False, production_approved=False,
        next_step='Nur diesen Diagnoseblock mitteilen. Keine Neuinstallation. Bisherige Modelle/Läufe bleiben erhalten; '
                  'derselbe bewusste Pilotstart setzt ab der letzten vollständig gespeicherten Epoche fort.')))
    return 130 if status == 'cancelled' else 2


if __name__ == '__main__':
    raise SystemExit(main())
