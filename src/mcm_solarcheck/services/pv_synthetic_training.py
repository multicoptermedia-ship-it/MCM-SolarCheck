"""Bounded CPU training qualification using generated data and random weights.

No customer inputs or published weights are accepted. The pinned external U-Net
and its license stay in the existing private reference folder. Artifacts from
this probe are deliberately not registered with either production detector.
"""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4

import numpy as np

from .thermal_partial_comparison import FLAGS
from .thermal_partial_training import AREA_MASK_POLICY, learning_target
from .orthophoto_pv_modules import _cancel
from ..review.dataset_build import DatasetBuild
from ..review.model_lineage import TrainingRun, TrainedModelArtifact
from ..review.training_runner import execute_training
from ..review.training_split import split_for_group
from ..vision.cvut_module_detector import specification, reference_model, checked_state

CHECK = 'solarcheck-pv-synthetic-training-1'
FOLDER = 'synthetic-training-probes'
WEIGHTS = 'SYNTHETIC_ONLY_NOT_A_PV_MODEL.pt'
REPORT = 'probe.json'
PROFILE = 'synthetic-rgb-unit-64x64-1'
PARAMETERS = dict(seed=6400, steps=3, learning_rate=.01,
    optimizer='SGD', ignore_index=255, synthetic_only=True)
PROBE_ID = re.compile(r'probe-[0-9]{20}-[0-9a-f]{32}')
FALSE_FLAGS = (*FLAGS, 'accuracy_verified', 'physical_module_ids_confirmed',
    'automatically_accepted', 'production_approved', 'customer_training_started',
    'customer_images_read', 'images_exported', 'model_updated',
    'published_weights_loaded', 'original_cvut_profile_verified')


def _local(path):
    # Unlike the comparison file guard, this also accepts new directories.
    path = Path(path)
    if (not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents))
            or any((p/'.git').is_file() or (p/'.git/HEAD').is_file() for p in (path, *path.parents))):
        raise ValueError('Privaten Referenzordner außerhalb Git ohne Verknüpfungen verwenden.')
    return path


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return sha256(_json(value).encode('utf-8')).hexdigest()


def _file_digest(path):
    result = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            result.update(chunk)
    return result.hexdigest()


def synthetic_dataset():
    """Four generated RGB/0-1-255 samples; disjoint deterministic site groups."""
    samples, arrays, groups = [], {}, set()
    for index, split in enumerate(('train', 'train', 'validation', 'test')):
        for number in range(10000):
            group = f'synthetic-site-{number}'
            if group not in groups and split_for_group(group) == split:
                groups.add(group)
                break
        else:
            raise RuntimeError('Synthetische Gruppenaufteilung nicht erzeugt.')
        x, y = 12+index*3, 14+index*2
        entry = {'manifest': {'mask_policy': AREA_MASK_POLICY,
            'samples': [{'source_window': [0, 0, 64, 64]}],
            'learning_area_px': [(4, 4), (60, 4), (60, 60), (4, 60)],
            'geometries': [{'polygon_px': [(x, y), (x+24, y), (x+24, y+28), (x, y+28)]}],
            'ignore_polygons_px': [[(26, 4), (29, 4), (29, 60), (26, 60)]]}}
        target = learning_target(entry)
        rng = np.random.default_rng(6400+index)
        rgb = rng.integers(20, 45, size=(64, 64, 3), dtype=np.uint8)
        rgb[y:y+28, x:x+24] = (70, 90, 130)
        rgb[y:y+28:4, x:x+24] = (120, 130, 150)
        sample_id = f'generated-{index}'
        arrays[sample_id] = (rgb, target)
        samples.append(dict(sample_id=sample_id, group_id=group, split=split,
            content_sha256=sha256(rgb.tobytes()+target.tobytes()).hexdigest()))
    manifest = dict(generator=PROFILE, samples=samples, synthetic_only=True)
    snapshot_id = _digest(manifest)
    encoded = _json(dict(snapshot_id=snapshot_id, **manifest))
    build = DatasetBuild(snapshot_id, sha256(encoded.encode('utf-8')).hexdigest(),
        len(samples), {'pv_module': len(samples)}, {'train': 2, 'validation': 1, 'test': 1}, encoded)
    return build, samples, arrays


def read_probe(reference_root, probe_id=None):
    """Read and hash-check a completed technical report without importing Torch."""
    root = _local(Path(reference_root).absolute())
    folder = _local(root/FOLDER)
    if probe_id is None:
        candidates = sorted(p.name for p in folder.iterdir() if PROBE_ID.fullmatch(p.name))
        if not candidates:
            raise ValueError('Noch keine abgeschlossene synthetische Trainingsprobe.')
        probe_id = candidates[-1]
    if not isinstance(probe_id, str) or not PROBE_ID.fullmatch(probe_id):
        raise ValueError('Ungültige synthetische Probenkennung.')
    job = _local(folder/probe_id)
    path = _local(job/REPORT)
    if path.stat().st_size > 32768:
        raise ValueError('Ungültiger Probenbericht.')
    report = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(report, dict) or report.get('check') != CHECK
            or report.get('probe_id') != probe_id or report.get('status') != 'passed'
            or report.get('synthetic_only') is not True
            or any(report.get(k) is not True for k in ('synthetic_training_started',
                'synthetic_weights_changed', 'ignore_gradient_verified', 'reload_verified'))
            or any(report.get(k) is not False for k in FALSE_FLAGS)):
        raise ValueError('Keine gültige rein synthetische Trainingsprobe.')
    try:
        run = TrainingRun(**report['training_run'])
        artifact = TrainedModelArtifact(report['run_id'], report['weights_sha256'], 'pt')
        if (run.run_id != artifact.run_id or run.dataset_id != report['dataset_sha256']
                or run.parameters != PARAMETERS or run.preprocessing != PROFILE
                or run.trainer != 'external-unet-synthetic-probe'
                or report.get('input_profile') != PROFILE
                or report.get('initialization') != 'seeded_random_not_published_weights'
                or report.get('torch_version') != specification()['torch_version']
                or run.trainer_version != specification()['source_commit']
                or report['source_commit'] != run.trainer_version
                or report['split_counts'] != {'train': 2, 'validation': 1, 'test': 1}
                or type(report['changed_parameter_tensors']) is not int or report['changed_parameter_tensors'] < 1
                or len(report['synthetic_losses']) != PARAMETERS['steps']
                or not np.isfinite([*report['synthetic_losses'], report['synthetic_validation_loss'], report['synthetic_test_loss']]).all()):
            raise ValueError('Inkonsistente synthetische Trainingsherkunft.')
    except (KeyError, TypeError) as error:
        raise ValueError('Unvollständiger synthetischer Probenbericht.') from error
    weights = _local(job/WEIGHTS)
    if (not 1 <= weights.stat().st_size <= 150_000_000
            or weights.stat().st_size != report.get('weights_bytes')
            or _file_digest(weights) != report.get('weights_sha256')):
        raise ValueError('Synthetisches Gewichtsartefakt geändert oder unvollständig.')
    return report


def run_probe(reference_root, *, should_cancel=None):
    """Fresh, three-step full-reference training; interrupted jobs never publish."""
    _cancel(should_cancel)
    root = _local(Path(reference_root).absolute())
    if not root.is_dir():
        raise ValueError('Vorhandenen getrennten Referenzordner verwenden.')
    import torch
    spec = specification()
    if torch.__version__ != spec['torch_version'] or torch.version.cuda is not None:
        raise ValueError('Vorhandene geprüfte PyTorch-CPU-Laufzeit verwenden.')
    torch.set_num_threads(2)
    build, samples, arrays = synthetic_dataset()
    run = TrainingRun(build.dataset_id, build.snapshot_id, 'external-unet-synthetic-probe',
        spec['source_commit'], PROFILE, PARAMETERS.copy())
    folder = _local(root/FOLDER)
    folder.mkdir(exist_ok=True)
    probe_id = f'probe-{time.time_ns():020d}-{uuid4().hex}'
    temporary, final = folder/(probe_id+'.next'), folder/probe_id
    temporary.mkdir(mode=0o700)
    try:
        _cancel(should_cancel)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(run.parameters['seed'])
            model = reference_model(root, spec, torch)
            before = {k: sha256(p.detach().numpy().tobytes()).hexdigest() for k, p in model.named_parameters()}
            def batch(split):
                pairs = [arrays[s['sample_id']] for s in samples if s['split'] == split]
                image = torch.from_numpy(np.stack([p[0].transpose(2, 0, 1) for p in pairs])).float()/255
                target = torch.from_numpy(np.stack([p[1] for p in pairs]).astype(np.int64))
                return image, target
            images, target = batch('train')
            optimizer = torch.optim.SGD(model.parameters(), lr=run.parameters['learning_rate'])
            losses = []
            model.train()
            for _ in range(run.parameters['steps']):
                _cancel(should_cancel)
                optimizer.zero_grad(set_to_none=True)
                logits = model(images)
                logits.retain_grad()
                loss = torch.nn.functional.cross_entropy(logits, target, ignore_index=255)
                if not torch.isfinite(loss).item():
                    raise ValueError('Nicht endlicher synthetischer Lernfehler.')
                loss.backward()
                unknown = (target == 255).unsqueeze(1).expand_as(logits)
                if torch.any(logits.grad[unknown] != 0).item():
                    raise ValueError('Ignorierpixel tragen zum Gradienten bei.')
                if any(p.grad is not None and not torch.isfinite(p.grad).all().item() for p in model.parameters()):
                    raise ValueError('Ungültiger synthetischer Parametergradient.')
                optimizer.step()
                losses.append(float(loss.detach()))
            optimizer.zero_grad(set_to_none=True)
            del logits, loss, optimizer
            changed = sum(sha256(p.detach().numpy().tobytes()).hexdigest() != before[k]
                          for k, p in model.named_parameters())
            if not changed:
                raise ValueError('Keine lernbaren Gewichte geändert.')
            model.eval()
            def evaluated(split, current):
                rgb, mask = batch(split)
                with torch.inference_mode():
                    output = current(rgb)
                    value = torch.nn.functional.cross_entropy(output, mask, ignore_index=255)
                if not torch.isfinite(output).all().item() or not torch.isfinite(value).item():
                    raise ValueError('Ungültige synthetische Prüfausgabe.')
                return output, float(value)
            validation_logits, validation_loss = evaluated('validation', model)
            test_logits, test_loss = evaluated('test', model)
            _cancel(should_cancel)
            def trainer(dataset, training_run):
                path = temporary/WEIGHTS
                with path.open('xb') as stream:
                    torch.save(model.state_dict(), stream)
                return path
            artifact = execute_training(build, run, trainer=trainer)
            del model
            _cancel(should_cancel)
            restored = reference_model(root, spec, torch)
            checked_state(torch, (temporary/WEIGHTS).read_bytes(), restored, spec)
            loaded_validation, _ = evaluated('validation', restored)
            loaded_test, _ = evaluated('test', restored)
            if not torch.equal(validation_logits, loaded_validation) or not torch.equal(test_logits, loaded_test):
                raise ValueError('Wieder geladene synthetische Gewichte liefern andere Ausgaben.')
        report = dict(check=CHECK, probe_id=probe_id, status='passed', synthetic_only=True,
            synthetic_training_started=True, synthetic_weights_changed=True,
            changed_parameter_tensors=changed, ignore_gradient_verified=True, reload_verified=True,
            initialization='seeded_random_not_published_weights', input_profile=PROFILE,
            source_commit=spec['source_commit'], torch_version=spec['torch_version'],
            training_run=asdict(run), run_id=run.run_id, dataset_sha256=build.dataset_id,
            split_counts=build.split_counts, synthetic_losses=losses,
            synthetic_validation_loss=validation_loss, synthetic_test_loss=test_loss,
            weights_sha256=artifact.weights_sha256, weights_bytes=(temporary/WEIGHTS).stat().st_size,
            notice='Nur synthetischer Techniknachweis. Kein trainiertes PV-Erkennungsmodell; nicht im Kundenvergleich verwenden.',
            **dict.fromkeys(FALSE_FLAGS, False))
        (temporary/REPORT).write_text(_json(report), encoding='utf-8')
        _cancel(should_cancel)
        temporary.rename(final)
        return read_probe(root, probe_id)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
