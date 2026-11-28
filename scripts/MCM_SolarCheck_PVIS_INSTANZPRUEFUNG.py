"""Validate existing public PVIS instance weights; no training or installation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1]/'src')]
import MCM_SolarCheck_PVIS_TRAINING as pilot
from mcm_solarcheck.services import pvis_instance_validation as validation


def _input(root):
    latest = pilot.audited._json(pilot.local(root/'latest.json'))
    folder, manifest = pilot._package(root, latest['package_id'])
    run_id = latest['run_id']
    if not isinstance(run_id, str) or len(run_id) != 64 or any(c not in '0123456789abcdef' for c in run_id):
        raise ValueError('Invalid stored training run')
    job = pilot.local(root/'runs'/run_id)
    parent = validation.trained.read_report(job, run_id)
    if parent['weights_sha256'] != latest['weights_sha256'] or parent['dataset_id'] != manifest['dataset_id']:
        raise ValueError('Stored training publication changed')
    return folder/'data.npz', manifest, job


def evaluate(prefix, reference_prefix):
    root, reference = pilot.local(prefix), pilot.local(reference_prefix)
    with pilot.package_lock(root, 'pvis-training.lock'):
        package, manifest, parent = _input(root)
        result = validation.run_validation(package, manifest, parent, reference, pilot.local(root/validation.FOLDER))
        pilot.atomic_json(pilot.local(root/validation.INDEX), result)
        return result


def show(prefix):
    root = pilot.local(prefix)
    with pilot.package_lock(root, 'pvis-training.lock'):
        package, manifest, parent = _input(root)
        return validation.read_result(package, manifest, parent, pilot.local(root/validation.FOLDER),
            validation._json(root/validation.INDEX))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-PVIS-Training')
    parser.add_argument('--torch-prefix', default=r'E:\SolarCheck-CVUT-KI-Pilot')
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--validate-instances', action='store_true')
    modes.add_argument('--show', action='store_true')
    modes.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.show: result = show(args.prefix)
        elif args.worker: result = evaluate(args.prefix, args.torch_prefix)
        else:
            root, reference = pilot.local(args.prefix), pilot.local(args.torch_prefix)
            # Preflight completed training without running or importing Torch.
            with pilot.package_lock(root, 'pvis-training.lock'): _input(root)
            executable = reference/('env/Scripts/python.exe' if os.name == 'nt' else 'env/bin/python')
            if not executable.is_file() or any(p.is_symlink() for p in executable.parents):
                raise FileNotFoundError('Existing qualified Torch CPU runtime missing')
            child = subprocess.Popen([str(executable), str(Path(__file__).resolve()), '--worker',
                '--prefix', str(root), '--torch-prefix', str(reference)])
            try: return child.wait()
            except KeyboardInterrupt:
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.terminate(); child.wait(timeout=10)
                raise
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True); return 0
    except KeyboardInterrupt:
        code, status = 'CANCELLED_SAVED_CROPS_RETAINED', 'cancelled'
    except Exception as error:
        code = ('EXISTING_INPUT_OR_RUNTIME_MISSING' if isinstance(error, (ImportError, FileNotFoundError))
                else 'INSTANCE_VALIDATION_CHANGED_OR_INVALID' if isinstance(error, ValueError)
                else 'LOCAL_IO' if isinstance(error, OSError) else 'INSTANCE_VALIDATION_FAILED')
        status = 'failed'
    print(json.dumps(dict(check='solarcheck-pvis-instance-validation-failure-1', status=status, error_code=code,
        training_started=False, model_updated=False, production_approved=False,
        next_step='Nur diesen Diagnoseblock mitteilen. Kein Training wiederholen, keine Neuinstallation. '
                  'Derselbe Instanzpruefstart verwendet vollstaendig gespeicherte Validierungscrops erneut.')))
    return 130 if status == 'cancelled' else 2


if __name__ == '__main__': raise SystemExit(main())
