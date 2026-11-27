"""Controlled public learning, <=20minutes per session, no new installations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1]/'src')]
import MCM_SolarCheck_PVIS_TRAINING as pilot
from MCM_SolarCheck_PVIS_INSTANZPRUEFUNG import _input
from mcm_solarcheck.services import pvis_learning_corpus as corpus
from mcm_solarcheck.services import pvis_controlled_learning as learning

MARKER = 'solarcheck-pvis-controlled-learning-root-1'


def root_folder(prefix):
    root = pilot.local(prefix); marker = pilot.local(root/'controlled-learning.json')
    if root.exists() and any(root.iterdir()):
        if not marker.is_file() or pilot.audited._json(marker) != dict(check=MARKER):
            raise ValueError('Own empty learning folder required; preserve old training root')
    root.mkdir(parents=True, exist_ok=True)
    if not marker.exists(): pilot.atomic_json(marker, dict(check=MARKER))
    return root


def prepare(source_prefix, prefix):
    root = root_folder(prefix)
    with pilot.package_lock(root, 'learning.lock'):
        return corpus.prepare(pilot.local(source_prefix), pilot.local(root/'corpora'), pilot.audited)


def worker(prefix, parent_prefix, reference_prefix, corpus_id, minutes):
    root = root_folder(prefix); parent_root = pilot.local(parent_prefix)
    with pilot.package_lock(root, 'learning.lock'), pilot.package_lock(parent_root, 'pvis-training.lock'):
        _, _, parent_job = _input(parent_root)
        if not isinstance(corpus_id, str) or len(corpus_id) != 64 or any(c not in '0123456789abcdef' for c in corpus_id):
            raise ValueError('Invalid corpus ID')
        folder = pilot.local(root/'corpora'/corpus_id); manifest = pilot.audited._json(folder/'corpus.json')
        # This identity matches the Torch runtime, never the App-Python NumPy version.
        runtime = dict(torch=learning.factory.specification()['torch_version'], numpy=learning.np.__version__, opencv=learning.cv2.__version__)
        parent = learning._parent(parent_job, False); run = learning.identity(manifest, parent, runtime)
        if (root/'active.json').exists():
            active = pilot.audited._json(root/'active.json')
            if active != dict(corpus_id=corpus_id, run_id=run.run_id, parent_run_id=parent_job.name):
                raise ValueError('Different learning lineage requires a separate new learning folder')
        pilot.atomic_json(pilot.local(root/'active.json'), dict(corpus_id=corpus_id, run_id=run.run_id,
            parent_run_id=parent_job.name))
        return learning.run(folder, manifest, parent_job, pilot.local(reference_prefix), pilot.local(root/'runs'), seconds=minutes*60)


def show(prefix, parent_prefix):
    root, parent_root = pilot.local(prefix), pilot.local(parent_prefix)
    with pilot.package_lock(root, 'learning.lock'), pilot.package_lock(parent_root, 'pvis-training.lock'):
        _, _, parent_job = _input(parent_root)
        active = pilot.audited._json(pilot.local(root/'active.json'))
        if (active.get('parent_run_id') != parent_job.name or any(not isinstance(active.get(k), str)
                or len(active[k]) != 64 or any(c not in '0123456789abcdef' for c in active[k]) for k in ('corpus_id', 'run_id'))):
            raise ValueError('Learning publication changed')
        folder = pilot.local(root/'corpora'/active['corpus_id']); manifest = pilot.audited._json(folder/'corpus.json')
        return learning.read_status(folder, manifest, parent_job, pilot.local(root/'runs'/active['run_id']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-PVIS-Lernen')
    parser.add_argument('--parent-prefix', default=r'E:\SolarCheck-PVIS-Training')
    parser.add_argument('--source-prefix', default=r'E:\SolarCheck-PVIS-Referenz')
    parser.add_argument('--torch-prefix', default=r'E:\SolarCheck-CVUT-KI-Pilot')
    parser.add_argument('--session-minutes', type=int, choices=range(1, 21), default=20)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--learn-public', action='store_true')
    mode.add_argument('--show', action='store_true')
    mode.add_argument('--worker', metavar='CORPUS_ID', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.show: result = show(args.prefix, args.parent_prefix)
        elif args.worker: result = worker(args.prefix, args.parent_prefix, args.torch_prefix, args.worker, args.session_minutes)
        else:
            reference = pilot.local(args.torch_prefix)
            executable = reference/('env/Scripts/python.exe' if os.name == 'nt' else 'env/bin/python')
            if not executable.is_file() or any(p.is_symlink() for p in executable.parents):
                raise FileNotFoundError('Existing Torch runtime required')
            parent_root = pilot.local(args.parent_prefix)
            with pilot.package_lock(parent_root, 'pvis-training.lock'):
                _, _, parent_job = _input(parent_root); learning._parent(parent_job, False)
            folder, manifest = prepare(args.source_prefix, args.prefix)
            child = subprocess.Popen([str(executable), str(Path(__file__).resolve()), '--worker', manifest['corpus_id'],
                '--prefix', args.prefix, '--parent-prefix', args.parent_prefix, '--torch-prefix', args.torch_prefix,
                '--session-minutes', str(args.session_minutes)])
            try: return child.wait()
            except KeyboardInterrupt:
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.terminate(); child.wait(timeout=10)
                raise
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True); return 0
    except KeyboardInterrupt: code, status = 'CANCELLED_LAST_CHECKPOINT_RETAINED', 'cancelled'
    except Exception as error:
        code = ('EXISTING_INPUT_OR_RUNTIME_MISSING' if isinstance(error, (ImportError, FileNotFoundError))
                else 'LEARNING_LINEAGE_OR_DATA_INVALID' if isinstance(error, ValueError)
                else 'LOCAL_IO_OR_SPACE' if isinstance(error, OSError) else 'CONTROLLED_LEARNING_FAILED')
        status = 'failed'
    print(json.dumps(dict(check='solarcheck-pvis-controlled-learning-failure-1', status=status, error_code=code,
        customer_training_started=False, model_updated=False, production_approved=False,
        next_step='Nur diesen Diagnoseblock mitteilen. Keine Neuinstallation/kein alter Pilotlauf. '
                  'Vorhandene Quellen und alte Modelle bleiben erhalten; gleicher Lernstart setzt gespeicherte Schritte fort.')))
    return 130 if status == 'cancelled' else 2


if __name__ == '__main__': raise SystemExit(main())
