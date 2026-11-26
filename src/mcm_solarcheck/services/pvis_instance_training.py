"""Isolated public U-Net research: semantic CE + discriminative instance embeddings.

Loss: De Brabandere, Neven, Van Gool (2017), arXiv:1708.02551.
Existing pinned external U-Net, random four-channel head, never published weights.
"""
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile

import numpy as np

from .pvis_public_training_data import encoded, fingerprint, read_arrays
from .pv_synthetic_training import _local
from ..review.dataset_build import DatasetBuild
from ..review.model_lineage import TrainingRun
from ..review.training_runner import execute_training
from ..vision.cvut_module_detector import specification, reference_model, checked_state

CHECK = 'solarcheck-pvis-instance-training-1'
WEIGHTS = 'EXPERIMENTAL_PVIS_INSTANCE_NOT_APPROVED.pt'
PARAMETERS = dict(seed=6400, epochs=3, learning_rate=.001, optimizer='SGD',
    momentum=0, clip_grad_norm=1., delta_variance=.5, delta_distance=1.5,
    instance_regularization=.001, output_channels=4, test_samples=0)


def instance_loss(torch, logits, instances):
    """Direct logit gradients at unknown pixels are zero in ALL four channels."""
    if (logits.ndim != 4 or logits.shape[:2] != (1, 4)
            or instances.shape != logits.shape[:1]+logits.shape[2:]
            or not torch.isfinite(logits).all().item()):
        raise ValueError('One finite four-channel instance batch required')
    valid = instances >= 0
    semantic = torch.where(valid, (instances > 0).long(), 255)
    if not valid.any().item(): raise ValueError('No valid target pixels')
    foreground = torch.nn.functional.cross_entropy(logits[:, :2], semantic, ignore_index=255)
    embeddings = logits[0, 2:].permute(1, 2, 0)
    identities = torch.unique(instances[instances > 0])
    if not 1 <= len(identities) <= 128: raise ValueError('Bounded positive instances required')
    centers, variances = [], []
    for identity in identities:
        values = embeddings[instances[0] == identity]
        center = values.mean(dim=0)
        centers.append(center)
        variances.append(torch.relu(torch.linalg.vector_norm(values-center, dim=1)-.5).square().mean())
    means = torch.stack(centers)
    variance = torch.stack(variances).mean()
    distance = logits.sum()*0
    if len(identities) > 1:
        distances = torch.cdist(means, means)
        pairs = ~torch.eye(len(identities), dtype=torch.bool, device=logits.device)
        distance = torch.relu(3.-distances[pairs]).square().mean()
    regularizer = torch.linalg.vector_norm(means, dim=1).mean()
    total = foreground+variance+distance+.001*regularizer
    return total, dict(foreground=foreground, variance=variance, distance=distance,
                      regularizer=regularizer)


def _digest(path):
    path = _local(path)
    h = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''): h.update(chunk)
    return h.hexdigest()


def _atomic_state(torch, path, value):
    path = _local(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.next', delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(value, stream)
        temporary.replace(path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def _state_hash(model):
    h = sha256()
    for key, value in model.state_dict().items():
        h.update(key.encode()); h.update(value.detach().contiguous().numpy().tobytes())
    return h.hexdigest()


def _four_spec(spec):
    spec = json.loads(json.dumps(spec))
    for key in ('outc.conv.weight', 'outc.conv.bias'): spec['state_shapes'][key][0] = 4
    return spec


def _json_atomic(path, value):
    path = _local(path)
    temporary = _local(path.with_suffix('.next'))
    try:
        temporary.write_text(encoded(value), encoding='utf-8'); temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def run_training(package, manifest, reference_root, output, *, should_cancel=lambda: False,
                 allow_synthetic=False, parameters=None):
    """Epoch checkpoints resume exactly with stateless fixed-LR SGD and CPU RNG."""
    import torch
    spec = specification()
    if torch.__version__ != spec['torch_version'] or torch.version.cuda is not None:
        raise ValueError('Existing pinned Torch CPU runtime required')
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    params = dict(PARAMETERS if parameters is None else parameters)
    if parameters is not None and not allow_synthetic: raise ValueError('Production pilot parameters are fixed')
    if (type(params.get('epochs')) is not int or not 1 <= params['epochs'] <= 3
            or params.get('optimizer') != 'SGD' or params.get('momentum') != 0):
        raise ValueError('Bounded stateless SGD pilot required')
    params['reference_commit'] = spec['source_commit']
    params['source_sha256'] = dict(trainer=sha256(Path(__file__).read_bytes()).hexdigest(),
        model_factory=sha256(Path(reference_model.__globals__['__file__']).read_bytes()).hexdigest(),
        dataset_reader=sha256(Path(read_arrays.__globals__['__file__']).read_bytes()).hexdigest())
    package, reference_root, output = _local(package), _local(reference_root), _local(output)
    rgb, labels = read_arrays(package, manifest, allow_synthetic=allow_synthetic)
    build = DatasetBuild(manifest['snapshot_id'], manifest['dataset_id'], len(rgb),
        {'pv_instance_crop': len(rgb)}, manifest['split_counts'], encoded(manifest))
    code_version = sha256(Path(__file__).read_bytes()).hexdigest()
    run = TrainingRun(build.dataset_id, build.snapshot_id, 'public-unet-instance-embedding-pilot',
                      code_version, manifest['profile'], params)
    job = _local(output/run.run_id)
    job.mkdir(parents=True, exist_ok=True)
    report_path, progress_path = _local(job/'report.json'), _local(job/'progress.json')
    if report_path.exists():
        return read_report(job, run.run_id)
    def cancel():
        if should_cancel(): raise KeyboardInterrupt
    cancel()
    torch.manual_seed(params['seed'])
    model = reference_model(reference_root, spec, torch, n_classes=4)
    model_spec = _four_spec(spec)
    before = {key: sha256(p.detach().numpy().tobytes()).hexdigest() for key, p in model.named_parameters()}
    initial_hash = _state_hash(model)
    optimizer = torch.optim.SGD(model.parameters(), lr=params['learning_rate'])
    train_ids = [i for i, row in enumerate(manifest['samples']) if row['split'] == 'train']
    validation_ids = [i for i, row in enumerate(manifest['samples']) if row['split'] == 'validation']
    def batch(index):
        return (torch.from_numpy(rgb[index].transpose(2, 0, 1).copy()).float().div(255).unsqueeze(0),
                torch.from_numpy(labels[index].astype(np.int64)).unsqueeze(0))
    def evaluate(current):
        current.eval(); loss_sum, intersection, union = 0., 0, 0
        with torch.inference_mode():
            for index in validation_ids:
                cancel(); image, target = batch(index); logits = current(image)
                loss_sum += float(instance_loss(torch, logits, target)[0])
                valid = target >= 0; truth = target > 0; predicted = logits[:, :2].argmax(dim=1) == 1
                intersection += int((predicted & truth & valid).sum())
                union += int(((predicted | truth) & valid).sum())
        return dict(loss=loss_sum/len(validation_ids), foreground_iou=intersection/max(1, union))
    baseline = evaluate(model)
    history, completed_epochs, steps = [], 0, 0
    checkpoint = None
    if progress_path.exists():
        progress = json.loads(progress_path.read_text('utf-8'))
        epoch = progress.get('epoch')
        if progress.get('run_id') != run.run_id or type(epoch) is not int or not 1 <= epoch <= params['epochs']:
            raise ValueError('Checkpoint publication changed')
        checkpoint = _local(job/f'epoch-{epoch:03d}.pt')
        if _digest(checkpoint) != progress.get('sha256'): raise ValueError('Checkpoint bytes changed')
        state = torch.load(checkpoint, map_location='cpu', weights_only=True)
        if (type(state) is not dict or state.get('run_id') != run.run_id
                or state.get('parameters') != params or state.get('dataset_id') != build.dataset_id
                or type(state.get('completed_epochs')) is not int
                or state['completed_epochs'] != epoch):
            raise ValueError('Checkpoint lineage changed')
        buffer = BytesIO(); torch.save(state['model'], buffer)
        checked_state(torch, buffer.getvalue(), model, model_spec)
        rng = state['rng']
        if type(rng) is not torch.Tensor or rng.dtype != torch.uint8 or rng.shape != torch.get_rng_state().shape:
            raise ValueError('Invalid CPU random state')
        torch.set_rng_state(rng)
        history, completed_epochs, steps = state['history'], state['completed_epochs'], state['steps']
        if steps != completed_epochs*len(train_ids) or len(history) != completed_epochs:
            raise ValueError('Checkpoint progress inconsistent')
        _metrics(history, baseline, history[-1]['validation'])
        del state, buffer, rng
    for epoch in range(completed_epochs, params['epochs']):
        model.train(); losses = []
        for order in torch.randperm(len(train_ids)).tolist():
            cancel(); image, target = batch(train_ids[order])
            optimizer.zero_grad(set_to_none=True)
            logits = model(image); logits.retain_grad()
            loss = instance_loss(torch, logits, target)[0]
            if not torch.isfinite(loss).item(): raise ValueError('Nonfinite training loss')
            loss.backward()
            ignored = (target < 0).unsqueeze(1).expand_as(logits)
            if torch.any(logits.grad[ignored] != 0).item(): raise ValueError('Ignored pixels contribute direct gradient')
            torch.nn.utils.clip_grad_norm_(model.parameters(), params['clip_grad_norm'], error_if_nonfinite=True)
            optimizer.step(); steps += 1; losses.append(float(loss.detach()))
            del logits, loss, image, target
        optimizer.zero_grad(set_to_none=True)
        metrics = evaluate(model)
        history.append(dict(epoch=epoch+1, training_loss=float(np.mean(losses)), validation=metrics))
        cancel()
        new_checkpoint = _local(job/f'epoch-{epoch+1:03d}.pt')
        _atomic_state(torch, new_checkpoint, dict(run_id=run.run_id, dataset_id=build.dataset_id,
            parameters=params, completed_epochs=epoch+1, steps=steps, history=history,
            rng=torch.get_rng_state(), model=model.state_dict()))
        _json_atomic(progress_path, dict(run_id=run.run_id, epoch=epoch+1, sha256=_digest(new_checkpoint)))
        if checkpoint is not None and checkpoint != new_checkpoint: checkpoint.unlink(missing_ok=True)
        checkpoint = new_checkpoint
        print(f'Oeffentlicher Trainingspilot: Epoche {epoch+1}/{params["epochs"]}, Lernfehler {np.mean(losses):.4f}', flush=True)
    cancel()
    final_metrics = evaluate(model)
    expected_outputs = []
    with torch.inference_mode():
        for index in validation_ids: expected_outputs.append(sha256(model(batch(index)[0]).numpy().tobytes()).hexdigest())
    changed = sum(sha256(p.detach().numpy().tobytes()).hexdigest() != before[key]
                  for key, p in model.named_parameters())
    if not changed: raise ValueError('No trainable parameters changed')
    final_hash = _state_hash(model)
    def trainer(dataset, training_run):
        _atomic_state(torch, job/WEIGHTS, model.state_dict())
        return job/WEIGHTS
    artifact = execute_training(build, run, trainer=trainer)
    del optimizer, model
    restored = reference_model(reference_root, spec, torch, n_classes=4)
    checked_state(torch, (job/WEIGHTS).read_bytes(), restored, model_spec)
    with torch.inference_mode():
        actual = [sha256(restored(batch(index)[0]).numpy().tobytes()).hexdigest() for index in validation_ids]
    if actual != expected_outputs: raise ValueError('Reloaded weights produce different logits')
    report = dict(check=CHECK, status='finished_experimental_not_production', run_id=run.run_id,
        dataset_id=build.dataset_id, training_run=asdict(run), split_counts=build.split_counts,
        public_training_started=not allow_synthetic, synthetic_only=bool(allow_synthetic),
        training_started=True, training_authorized=True, authorization_scope='explicit_public_pvis_research_only',
        experimental_weights_changed=True, changed_parameter_tensors=changed,
        initial_state_sha256=initial_hash, final_state_sha256=final_hash,
        weights_sha256=artifact.weights_sha256, weights_bytes=(job/WEIGHTS).stat().st_size,
        epochs_completed=params['epochs'], steps=steps, history=history,
        baseline_validation=baseline, final_validation=final_metrics,
        ignore_gradient_verified=True, reload_verified=True, torch_version=torch.__version__,
        initialization='seeded_random_no_published_weights', external_reference_commit=spec['source_commit'],
        input_profile=manifest['profile'], output_channels=4, instance_detection_ready=False, pixel_test_images_read=0,
        license_declared='CC-BY-4.0', license_decision='unreviewed', commercial_training_approved=False,
        customer_training_started=False, customer_images_read=False, model_updated=False,
        customer_images_exported=False, original_cvut_profile_verified=False,
        production_approved=False, automatically_accepted=False, accuracy_verified=False,
        physical_module_ids_confirmed=False, coverage_verified=False, georeferencing_verified=False,
        temperature_verified=False, pair_registered=False, published_weights_loaded=False,
        notice='Begrenzter öffentlicher Forschungsversuch mit Flächen- und Instanzmerkmalen. '
               'Keine fertige Modulzählung, Kundenanalyse oder allgemeine Qualitätsfreigabe. '
               'Bestehende Erkennungsmodelle bleiben unverändert; Testanlage nicht gelesen.')
    cancel()
    report['report_sha256'] = fingerprint(report)
    _json_atomic(report_path, report)
    if checkpoint is not None: checkpoint.unlink(missing_ok=True)
    progress_path.unlink(missing_ok=True)
    return read_report(job, run.run_id)


def read_report(job, expected_run_id):
    job = _local(job)
    path = _local(job/'report.json')
    if path.stat().st_size > 100000: raise ValueError('Training report too large')
    report = json.loads(path.read_text('utf-8'))
    body = dict(report); saved_hash = body.pop('report_sha256', None)
    if (report.get('check') != CHECK or report.get('run_id') != expected_run_id
            or saved_hash != fingerprint(body)
            or report.get('reload_verified') is not True or report.get('ignore_gradient_verified') is not True
            or report.get('production_approved') is not False or report.get('model_updated') is not False
            or report.get('customer_images_read') is not False or report.get('pixel_test_images_read') != 0
            or not 1 <= (job/WEIGHTS).stat().st_size <= 150_000_000
            or (job/WEIGHTS).stat().st_size != report.get('weights_bytes')
            or _digest(job/WEIGHTS) != report.get('weights_sha256')):
        raise ValueError('Experimental training report or weights changed')
    run = TrainingRun(**report['training_run'])
    false_flags = ('customer_training_started', 'customer_images_read', 'production_approved',
        'automatically_accepted', 'accuracy_verified', 'physical_module_ids_confirmed', 'coverage_verified',
        'georeferencing_verified', 'temperature_verified', 'pair_registered', 'published_weights_loaded',
        'commercial_training_approved', 'instance_detection_ready', 'model_updated',
        'customer_images_exported', 'original_cvut_profile_verified')
    if (run.run_id != expected_run_id or run.dataset_id != report.get('dataset_id')
            or report.get('status') != 'finished_experimental_not_production'
            or any(report.get(flag) is not True for flag in ('training_started', 'training_authorized'))
            or report.get('authorization_scope') != 'explicit_public_pvis_research_only'
            or type(report.get('synthetic_only')) is not bool
            or report.get('public_training_started') is not (not report['synthetic_only'])
            or report.get('output_channels') != 4
            or report.get('input_profile') != run.preprocessing
            or report.get('initialization') != 'seeded_random_no_published_weights'
            or report.get('license_declared') != 'CC-BY-4.0' or report.get('license_decision') != 'unreviewed'
            or set(report.get('split_counts', {})) != {'train', 'validation'}
            or any(report.get(flag) is not False for flag in false_flags)
            or report.get('epochs_completed') != run.parameters.get('epochs')
            or report.get('steps') != run.parameters['epochs']*report['split_counts']['train']
            or report.get('experimental_weights_changed') is not True
            or type(report.get('changed_parameter_tensors')) is not int or report['changed_parameter_tensors'] < 1
            or len(report.get('history', [])) != run.parameters['epochs']):
        raise ValueError('Training lineage or restricted flags changed')
    _metrics(report['history'], report['baseline_validation'], report['final_validation'])
    return report


def _metrics(history, baseline, final):
    if not isinstance(history, list) or [r['epoch'] for r in history] != list(range(1, len(history)+1)):
        raise ValueError('Invalid epoch sequence')
    losses = [row['training_loss'] for row in history]
    for metrics in [baseline, final, *(r['validation'] for r in history)]:
        losses.append(metrics['loss'])
        if not 0 <= metrics['foreground_iou'] <= 1: raise ValueError('Invalid validation metric')
    if not np.isfinite(losses).all() or min(losses) < 0: raise ValueError('Invalid training losses')
