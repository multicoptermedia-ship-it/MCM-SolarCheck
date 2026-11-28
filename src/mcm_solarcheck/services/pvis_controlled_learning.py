"""Bounded, resumable public learning; old pilot/source files remain immutable."""
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import time

import cv2
import numpy as np
from PIL import Image

from . import pvis_instance_training as base
from . import pvis_learning_corpus as corpus
from .pvis_public_training_data import fingerprint, encoded
from .pvis_instance_validation import FALSE_FLAGS, preview, _png
from ..vision import pvis_instance_decoding as decoder
from ..vision import cvut_module_detector as factory
from ..review.dataset_build import DatasetBuild
from ..review.model_lineage import TrainingRun
from ..review.training_runner import execute_training

CHECK = 'solarcheck-pvis-controlled-learning-1'
PARAMETERS = dict(seed=6400, epochs=8, optimizer='AdamW', learning_rate=.0003, weight_decay=.0001,
    checkpoint_steps=16, clip_grad_norm=1., augmentation='exact_rot90_and_horizontal_flip_train_only',
    sampling='alternating_single_multi_each_source_once_then_repeat_smaller_group',
    selection='all24_decoded_then_instance_f1_else0_then_raw_foreground_iou_all24')


def sources():
    runner = Path(__file__).resolve().parents[3]/'scripts/MCM_SolarCheck_PVIS_LERNEN.py'
    return {name: sha256(path.read_bytes()).hexdigest() for name, path in dict(
        learning=Path(__file__), corpus=Path(corpus.__file__), original_loss=Path(base.__file__),
        model_factory=Path(factory.__file__), decoder=Path(decoder.__file__), runner=runner).items()}


def sealed(value):
    result = dict(value); result.pop('report_sha256', None)
    result['report_sha256'] = fingerprint(result)
    return result


def read_json(path):
    path = base._local(path)
    if path.stat().st_size > 1_000_000: raise ValueError('Learning metadata too large')
    value = json.loads(path.read_text('utf-8'))
    if sealed(value) != value: raise ValueError('Learning metadata changed')
    return value


def order(rows, epoch, seed=6400):
    """Every source occurs; the smaller stratum repeats to balance single/multi."""
    groups = [[i for i, r in enumerate(rows) if r['split'] == 'train' and (r['instances'] > 1) == multi]
              for multi in (False, True)]
    rng = np.random.default_rng(seed+epoch)
    if not all(groups): return rng.permutation(groups[0]+groups[1]).tolist()
    length = max(map(len, groups)); padded = []
    for group in groups:
        values = []
        while len(values) < length: values.extend(rng.permutation(group).tolist())
        padded.append(values[:length])
    return [i for pair in zip(*padded) for i in pair]


def augment(rgb, target, step):
    # Balanced scheduling alternates the two strata. Each parity must receive
    # all eight transforms; step%4 alone would couple rotation and module count.
    turns, flip = ((step//2)+(step % 2)) % 4, (step//8) % 2
    rgb, target = np.rot90(rgb, turns), np.rot90(target, turns)
    if flip: rgb, target = rgb[:, ::-1], target[:, ::-1]
    return np.ascontiguousarray(rgb), np.ascontiguousarray(target)


def identity(manifest, parent, runtime, *, synthetic=False, parameters=None):
    if parameters is not None and not synthetic: raise ValueError('Fixed public learning parameters required')
    params = dict(PARAMETERS if parameters is None else parameters)
    if (type(params.get('epochs')) is not int or not 1 <= params['epochs'] <= 8
            or type(params.get('checkpoint_steps')) is not int or not 1 <= params['checkpoint_steps'] <= 16):
        raise ValueError('Bounded learning schedule required')
    params.update(parent_run_id=parent['run_id'], parent_report_sha256=parent['report_sha256'],
        parent_weights_sha256=parent['weights_sha256'], source_sha256=sources(), runtime=runtime)
    return TrainingRun(manifest['dataset_id'], manifest['snapshot_id'], 'public-unet-controlled-learning',
        params['source_sha256']['learning'], manifest['profile'], params)


def _parent(parent_job, synthetic):
    parent = base.read_report(parent_job, parent_job.name)
    if parent['synthetic_only'] is not synthetic: raise ValueError('Public parent pilot required')
    actual = dict(trainer=sha256(Path(base.__file__).read_bytes()).hexdigest(),
        model_factory=sha256(Path(factory.__file__).read_bytes()).hexdigest(),
        dataset_reader=sha256(Path(base.read_arrays.__globals__['__file__']).read_bytes()).hexdigest())
    if parent['training_run']['parameters']['source_sha256'] != actual:
        raise ValueError('Original qualified pilot loader changed')
    return parent


def _metrics(rows, raw, decoded, diagnostics):
    scores = []; intersection = union = legacy_i = legacy_u = 0
    for position, (target, foreground, prediction, diagnostic) in enumerate(zip(rows, raw, decoded, diagnostics)):
        valid = target >= 0; truth = target > 0
        a = int((foreground & truth & valid).sum()); b = int(((foreground | truth) & valid).sum())
        intersection += a; union += b
        if position < 8: legacy_i += a; legacy_u += b
        if diagnostic['status'] == 'complete': scores.append(decoder.score_instances(target, prediction))
    metrics = decoder.aggregate(scores) if scores else None
    complete = len(scores) == len(rows)
    raw_iou = intersection/max(1, union)
    return dict(validation_crops=len(rows), scored_crops=len(scores), unscored_crops=len(rows)-len(scores),
        raw_foreground_iou_all=raw_iou, previous_first8_foreground_iou=legacy_i/max(1, legacy_u),
        instance_metrics_complete_crops=metrics,
        selection_rank=[int(complete), (metrics['f1'] or 0) if complete else 0, raw_iou])


def _candidate(job, name, expected):
    if not isinstance(name, str) or not re.fullmatch('EXPERIMENTAL-CANDIDATE-[0-9]{8}\\.pt', name):
        raise ValueError('Invalid experimental candidate filename')
    path = base._local(job/name)
    if not 1 <= path.stat().st_size <= 150_000_000 or base._digest(path) != expected:
        raise ValueError('Selected candidate changed')
    return path


def read_status(folder, manifest, parent_job, job, *, synthetic=False):
    corpus.read_corpus(folder, manifest, synthetic=synthetic); parent = _parent(parent_job, synthetic)
    path = base._local(job/('report.json' if (job/'report.json').exists() else 'progress.json'))
    report = read_json(path); run = TrainingRun(**report['training_run'])
    params = {k: report['training_run']['parameters'][k] for k in PARAMETERS}
    expected = identity(manifest, parent, run.parameters['runtime'], synthetic=synthetic,
        parameters=params if synthetic else None)
    if (run != expected or run.run_id != job.name or report.get('check') != CHECK
            or report.get('synthetic_only') is not synthetic
            or any(report.get(k) is not False for k in FALSE_FLAGS if k != 'training_started')
            or report.get('training_started') is not True
            or report.get('training_authorized') is not True
            or report.get('public_training_started') is not (not synthetic)
            or report.get('authorization_scope') != 'explicit_public_pvis_research_only'
            or report.get('license_declared') != 'CC-BY-4.0' or report.get('license_decision') != 'unreviewed'
            or report.get('pixel_test_images_read') != 0):
        raise ValueError('Learning lineage or restricted flags changed')
    schedule_length = len(order(manifest['samples'], 0))
    epoch, cursor, steps = report['completed_epochs'], report['next_sample'], report['saved_steps']
    if (type(epoch) is not int or not 0 <= epoch <= params['epochs'] or type(cursor) is not int
            or not 0 <= cursor < schedule_length or steps != epoch*schedule_length+cursor
            or len(report['history']) != epoch or len(report['epoch_losses']) != cursor):
        raise ValueError('Learning cursor differs from fixed schedule')
    _candidate(job, report['candidate_file'], report['weights_sha256'])
    if report['status'] == 'checkpoint_available':
        name = report.get('checkpoint_file')
        if not isinstance(name, str) or not re.fullmatch('checkpoint-[0-9]{8}\\.pt', name):
            raise ValueError('Invalid checkpoint filename')
        checkpoint = base._local(job/name)
        if checkpoint.stat().st_size > 500_000_000 or base._digest(checkpoint) != report['checkpoint_sha256']:
            raise ValueError('Checkpoint changed')
    elif report['status'] == 'finished_experimental_not_production':
        if epoch != params['epochs'] or cursor or report.get('reload_verified') is not True:
            raise ValueError('Incomplete learning cannot publish a finished result')
        for name, expected_hash in report['artifacts'].items():
            if (not re.fullmatch('(mask|raw|preview)-[0-9]{2}\\.png', name)
                    or base._digest(job/name) != expected_hash): raise ValueError('Validation artifact changed')
    else: raise ValueError('Unknown learning status')
    return report


def run(folder, manifest, parent_job, reference_root, output, *, seconds=1200,
        should_cancel=lambda: False, now=time.monotonic, synthetic=False, parameters=None):
    """The time limit ends a session; all model/Adam moments/cursor state resume."""
    if not isinstance(seconds, (int, float)) or not 0 < seconds <= 1200: raise ValueError('Session <=20minutes required')
    import torch
    spec = factory.specification()
    if torch.__version__ != spec['torch_version'] or torch.version.cuda is not None:
        raise ValueError('Qualified existing Torch CPU runtime required')
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    parent = _parent(parent_job, synthetic); rgb, targets = corpus.read_corpus(folder, manifest, synthetic=synthetic)
    runtime = dict(torch=spec['torch_version'], numpy=np.__version__, opencv=cv2.__version__)
    training_run = identity(manifest, parent, runtime, synthetic=synthetic, parameters=parameters)
    params = training_run.parameters; job = base._local(output/training_run.run_id); job.mkdir(parents=True, exist_ok=True)
    if (job/'report.json').exists(): return read_status(folder, manifest, parent_job, job, synthetic=synthetic)
    started = now(); validation_ids = [i for i, r in enumerate(manifest['samples']) if r['split'] == 'validation']
    torch.manual_seed(params['seed']); model = factory.reference_model(reference_root, spec, torch, n_classes=4)
    model_spec = base._four_spec(spec)
    factory.checked_state(torch, (parent_job/base.WEIGHTS).read_bytes(), model, model_spec)
    parent_state_sha = base._state_hash(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=params['learning_rate'], weight_decay=params['weight_decay'], foreach=False)
    def cancel():
        if should_cancel(): raise KeyboardInterrupt
    def tensor(index, *, step=None):
        image, target = rgb[index], targets[index]
        if step is not None: image, target = augment(image, target, step)
        return (torch.from_numpy(image.transpose(2, 0, 1).copy()).float().div(255).unsqueeze(0),
                torch.from_numpy(target.astype(np.int64)).unsqueeze(0))
    def evaluate(*, write=False):
        model.eval(); masks, raw, diagnostics, hashes, artifacts = [], [], [], [], {}
        with torch.inference_mode():
            for position, index in enumerate(validation_ids):
                cancel(); logits = model(tensor(index)[0])[0].numpy().copy()
                hashes.append(sha256(logits.tobytes()).hexdigest())
                prediction, probability, diagnostic = decoder.decode(logits, should_cancel=should_cancel)
                foreground = logits[:2].argmax(axis=0) == 1
                masks.append(prediction); raw.append(foreground); diagnostics.append(diagnostic)
                if write:
                    images = dict(mask=Image.fromarray(prediction.astype(np.uint16)), raw=Image.fromarray(foreground.astype(np.uint8)),
                        preview=preview(rgb[index], targets[index], prediction, probability))
                    for kind, image in images.items():
                        name = f'{kind}-{position+1:02d}.png'; _png(job/name, image); artifacts[name] = base._digest(job/name)
        result = _metrics([targets[i] for i in validation_ids], raw, masks, diagnostics)
        result['logits_sha256'] = hashes
        return result, artifacts
    state = dict(completed_epochs=0, next_sample=0, saved_steps=0, epoch_losses=[], history=[])
    checkpoint, best_file = None, None
    def choose(metrics):
        nonlocal best_file
        previous = best_file
        best_file = f'EXPERIMENTAL-CANDIDATE-{state["saved_steps"]:08d}.pt'
        base._atomic_state(torch, job/best_file, model.state_dict())
        state.update(candidate_file=best_file, weights_sha256=base._digest(job/best_file),
            selected_validation=metrics, candidate_step=state['saved_steps'])
        return previous
    def metadata():
        return dict(check=CHECK, status='checkpoint_available', training_run=asdict(training_run), run_id=training_run.run_id,
            dataset_id=manifest['dataset_id'], parent_run_id=parent['run_id'], parent_state_sha256=parent_state_sha,
            split_counts=manifest['split_counts'], synthetic_only=synthetic, training_started=True,
            public_training_started=not synthetic, training_authorized=True, authorization_scope='explicit_public_pvis_research_only',
            pixel_test_images_read=0, license_declared='CC-BY-4.0', license_decision='unreviewed',
            **dict.fromkeys((k for k in FALSE_FLAGS if k != 'training_started'), False), **state)
    def save(old_best=None):
        nonlocal checkpoint
        # Every publication has a new step; same-step terminal pause needs no rewrite.
        name = f'checkpoint-{state["saved_steps"]:08d}.pt'; meta = metadata()
        if name == checkpoint: return  # do not replace bytes referenced by an existing pointer
        state['last_training_state_sha256'] = base._state_hash(model); meta = metadata()
        base._atomic_state(torch, job/name, dict(metadata=meta, model=model.state_dict(), optimizer=optimizer.state_dict(), rng=torch.get_rng_state()))
        progress = sealed(dict(meta, checkpoint_file=name, checkpoint_sha256=base._digest(job/name)))
        base._json_atomic(job/'progress.json', progress)
        if checkpoint and checkpoint != name: base._local(job/checkpoint).unlink(missing_ok=True)
        if old_best and old_best != best_file: base._local(job/old_best).unlink(missing_ok=True)
        checkpoint = name
    cancel()
    if (job/'progress.json').exists():
        progress = read_status(folder, manifest, parent_job, job, synthetic=synthetic)
        checkpoint = progress['checkpoint_file']; loaded = torch.load(job/checkpoint, map_location='cpu', weights_only=True)
        expected = {k: v for k, v in progress.items() if k not in ('checkpoint_file', 'checkpoint_sha256', 'report_sha256')}
        if loaded.get('metadata') != expected: raise ValueError('Checkpoint metadata changed')
        buffer = BytesIO(); torch.save(loaded['model'], buffer)
        factory.checked_state(torch, buffer.getvalue(), model, model_spec)
        if base._state_hash(model) != progress['last_training_state_sha256']:
            raise ValueError('Resumed model state differs')
        optimizer.load_state_dict(loaded['optimizer'])
        for parameter, moments in optimizer.state.items():
            for key in ('exp_avg', 'exp_avg_sq'):
                value = moments[key]
                if value.shape != parameter.shape or value.dtype != torch.float32 or not torch.isfinite(value).all():
                    raise ValueError('Invalid Adam moment')
        torch.set_rng_state(loaded['rng'])
        state = {k: progress[k] for k in ('completed_epochs', 'next_sample', 'saved_steps', 'epoch_losses', 'history',
            'candidate_file', 'weights_sha256', 'selected_validation', 'candidate_step', 'baseline_validation')}
        state['last_training_state_sha256'] = progress['last_training_state_sha256']
        best_file = state['candidate_file']; del loaded, buffer
    else:
        if not synthetic and shutil.disk_usage(job).free < 1_100_000_000:
            raise OSError(28, 'Controlled learning needs1.1GB free for atomic Adam checkpoints')
        baseline, _ = evaluate(); state['baseline_validation'] = baseline; choose(baseline); save()
    try:
        while state['completed_epochs'] < params['epochs']:
            schedule = order(manifest['samples'], state['completed_epochs'], params['seed'])
            while state['next_sample'] < len(schedule):
                cancel()
                if now()-started >= seconds:
                    if state['saved_steps'] % params['checkpoint_steps']: save()
                    print('Zeitgrenze erreicht; derselbe Lernstart setzt ab dem gespeicherten Schritt fort.', flush=True)
                    return read_status(folder, manifest, parent_job, job, synthetic=synthetic)
                index = schedule[state['next_sample']]; model.train(); optimizer.zero_grad(set_to_none=True)
                image, target = tensor(index, step=state['saved_steps']); logits = model(image); logits.retain_grad()
                loss = base.instance_loss(torch, logits, target)[0]; loss.backward()
                if torch.any(logits.grad[(target < 0).unsqueeze(1).expand_as(logits)] != 0):
                    raise ValueError('Unknown pixels contribute gradient')
                torch.nn.utils.clip_grad_norm_(model.parameters(), params['clip_grad_norm'], error_if_nonfinite=True)
                optimizer.step(); optimizer.zero_grad(set_to_none=True)
                state['saved_steps'] += 1; state['next_sample'] += 1; state['epoch_losses'].append(float(loss.detach()))
                del image, target, logits, loss
                # Validation belongs to a completed epoch, before publishing its cursor.
                if state['next_sample'] == len(schedule): break
                if state['saved_steps'] % params['checkpoint_steps'] == 0:
                    save(); print(f'Lernspeicherpunkt: {state["saved_steps"]} Schritte', flush=True)
            metrics, _ = evaluate(); old_best = None
            if metrics['selection_rank'] > state['selected_validation']['selection_rank']: old_best = choose(metrics)
            state['history'].append(dict(epoch=state['completed_epochs']+1,
                training_loss=float(np.mean(state['epoch_losses'])), validation=metrics))
            state['completed_epochs'] += 1; state['next_sample'] = 0; state['epoch_losses'] = []
            save(old_best)
            print(f'Kontrolliertes Lernen: Epoche {state["completed_epochs"]}/{params["epochs"]}, '
                  f'Validierungs-IoU {metrics["raw_foreground_iou_all"]:.4f}, '
                  f'bewertete Ausschnitte {metrics["scored_crops"]}/{metrics["validation_crops"]}', flush=True)
        factory.checked_state(torch, _candidate(job, best_file, state['weights_sha256']).read_bytes(), model, model_spec)
        reloaded, artifacts = evaluate(write=True)
        if reloaded != state['selected_validation']: raise ValueError('Selected weights produce different validation outputs')
        build = DatasetBuild(manifest['snapshot_id'], manifest['dataset_id'], len(rgb), {'pv_instance_crop': len(rgb)},
            manifest['split_counts'], encoded(manifest))
        artifact = execute_training(build, training_run, trainer=lambda *a: job/best_file)
        report = sealed(dict(metadata(), status='finished_experimental_not_production', reload_verified=True,
            ignore_gradient_verified=True, weights_sha256=artifact.weights_sha256, artifacts=artifacts,
            experimental_weights_changed=state['last_training_state_sha256'] != parent_state_sha,
            selected_state_sha256=base._state_hash(model),
            notice='Begrenztes oeffentliches Forschungstraining. Bestauswahl auf Validierung, keine unabhaengige '
                   'Abschlusspruefung oder Produktionsfreigabe. Maskenkennzahlen gelten nur fuer vollstaendig '
                   'segmentierte Crops; Rohflaechen-IoU fuer alle24. Keine automatische Uebernahme in Kundenvergleich.'))
        cancel(); base._json_atomic(job/'report.json', report)
        base._local(job/checkpoint).unlink(missing_ok=True); (job/'progress.json').unlink(missing_ok=True)
        return read_status(folder, manifest, parent_job, job, synthetic=synthetic)
    except KeyboardInterrupt:
        print('Abbruch: letzter vollstaendiger Speicherpunkt bleibt erhalten.', flush=True)
        return read_status(folder, manifest, parent_job, job, synthetic=synthetic)
