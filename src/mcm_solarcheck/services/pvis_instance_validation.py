"""Read-only validation of existing public pilot weights; no training or test images."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import cv2
import numpy as np
import PIL
from PIL import Image, ImageDraw

from . import pvis_instance_training as trained
from .pvis_public_training_data import fingerprint, read_arrays
from ..vision import pvis_instance_decoding as decoding
from ..vision import cvut_module_detector as model_factory

CHECK = 'solarcheck-pvis-instance-validation-1'
FOLDER = 'instance-validation'
INDEX = 'instance-validation.json'
FALSE_FLAGS = ('training_started', 'customer_training_started', 'customer_images_read',
    'customer_images_exported', 'model_updated', 'production_approved', 'automatically_accepted',
    'accuracy_verified', 'physical_module_ids_confirmed', 'coverage_verified',
    'georeferencing_verified', 'temperature_verified', 'pair_registered', 'commercial_training_approved',
    'published_weights_loaded', 'instance_detection_ready')


def _json(path):
    path = trained._local(path)
    if path.stat().st_size > 1_000_000: raise ValueError('Validation record too large')
    return json.loads(path.read_text('utf-8'))


def _sources():
    runner = Path(__file__).resolve().parents[3]/'scripts/MCM_SolarCheck_PVIS_INSTANZPRUEFUNG.py'
    return dict(decoder=sha256(Path(decoding.__file__).read_bytes()).hexdigest(),
        validation=sha256(Path(__file__).read_bytes()).hexdigest(), runner=sha256(runner.read_bytes()).hexdigest())


def _parent(package, manifest, parent_job, *, allow_synthetic=False):
    parent = trained.read_report(parent_job, parent_job.name)
    if (parent['dataset_id'] != manifest['dataset_id'] or parent['synthetic_only'] != allow_synthetic
            or parent['training_run']['snapshot_id'] != manifest['snapshot_id']):
        raise ValueError('Weights and public numeric data differ')
    actual = dict(trainer=sha256(Path(trained.__file__).read_bytes()).hexdigest(),
        model_factory=sha256(Path(model_factory.__file__).read_bytes()).hexdigest(),
        dataset_reader=sha256(Path(read_arrays.__globals__['__file__']).read_bytes()).hexdigest())
    if actual != parent['training_run']['parameters']['source_sha256']:
        raise ValueError('Original qualified training loader changed; do not retrain automatically')
    rgb, targets = read_arrays(package, manifest, allow_synthetic=allow_synthetic)
    ids = [i for i, sample in enumerate(manifest['samples']) if sample['split'] == 'validation']
    if not ids or any(manifest['samples'][i]['station'] != '033' for i in ids):
        raise ValueError('Only fixed validation station 033 allowed')
    return parent, rgb, targets, ids


def _configuration(parent, manifest, runtime):
    return dict(parent_run_id=parent['run_id'], parent_report_sha256=parent['report_sha256'],
        weights_sha256=parent['weights_sha256'], dataset_id=manifest['dataset_id'],
        package_manifest_sha256=manifest['manifest_sha256'], profile=decoding.PROFILE,
        input_profile=manifest['profile'], label_policy=manifest['label_policy'],
        source_sha256=_sources(), runtime=runtime)


def _key(sample):
    return 'crop-'+sha256(sample['sample_id'].encode()).hexdigest()


def _png(path, image):
    path = trained._local(path); temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.next', delete=False) as stream:
            temporary = Path(stream.name); image.save(stream, format='PNG')
        temporary.replace(path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def preview(rgb, reference, prediction, probability):
    """RGB / reference / independent prediction / probability; metadata-free."""
    palette = np.array([[0, 220, 120], [255, 190, 0], [0, 170, 255], [255, 80, 100],
                        [170, 140, 255], [120, 230, 40]], np.uint8)
    def overlay(mask):
        colored = np.zeros_like(rgb); positive = mask > 0
        colored[positive] = palette[(mask[positive]-1) % len(palette)]
        colored[mask < 0] = (255, 0, 255)
        output = rgb.copy(); marked = mask != 0
        output[marked] = ((rgb[marked].astype(np.uint16)+colored[marked])/2).astype(np.uint8)
        # Draw per-instance contours; neighboring modules must have a visible shared edge.
        for identity in np.unique(mask[positive]):
            contours, _ = cv2.findContours((mask == identity).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(output, contours, -1, (255, 255, 0), 1)
        return output
    gray = np.repeat((probability*255).astype(np.uint8)[:, :, None], 3, axis=2)
    size = rgb.shape[0]; sheet = Image.new('RGB', (size*4, size+24), 'white')
    draw = ImageDraw.Draw(sheet)
    labels = ('RGB / 256', 'Referenz / Magenta: ignoriert', 'Versuch / KEINE FREIGABE', 'PV-Wahrscheinlichkeit')
    for i, (pixels, label) in enumerate(zip((rgb, overlay(reference), overlay(prediction), gray), labels)):
        sheet.paste(Image.fromarray(pixels), (size*i, 24)); draw.text((size*i+3, 4), label, fill='black')
    return sheet


def _row(folder, sample, target):
    key = _key(sample); row = _json(folder/(key+'.json'))
    body = dict(row); saved = body.pop('row_sha256', None)
    if (saved != fingerprint(body) or row.get('sample_id') != sample['sample_id']
            or row.get('evaluation_id') != folder.name
            or row.get('source_record_sha256') != sample['source_record_sha256']
            or trained._digest(folder/(key+'-mask.png')) != row.get('mask_sha256')
            or trained._digest(folder/(key+'-preview.png')) != row.get('preview_sha256')):
        raise ValueError('Saved validation crop or preview changed')
    with Image.open(trained._local(folder/(key+'-mask.png'))) as image:
        if image.size != (target.shape[1], target.shape[0]) or image.format != 'PNG':
            raise ValueError('Wrong saved instance raster dimensions')
        prediction = np.array(image, dtype=np.int32)
    if (prediction.shape != target.shape or prediction.min() < 0 or prediction.max() > 128
            or decoding.describe(prediction) != row['decoding']['candidates']
            or len(row['decoding']['candidates']) != row['decoding']['candidate_instances']):
        raise ValueError('Saved proposal raster differs')
    status = row['decoding']['status']
    if status not in ('complete', 'limit_exceeded_unscored'):
        raise ValueError('Invalid decoding status')
    expected = decoding.score_instances(target, prediction) if status == 'complete' else None
    if (row.get('score') != expected
            or row.get('reference_instance_observations') != len(np.unique(target[target > 0]))):
        raise ValueError('Saved mask scores differ')
    return row


def _summary(config, rows, synthetic):
    scored = [r['score'] for r in rows if r['score'] is not None]
    return dict(check=CHECK, status='finished_validation_only', evaluation_id=fingerprint(config), config=config,
        parent_run_id=config['parent_run_id'], weights_sha256=config['weights_sha256'],
        validation_crops=len(rows), scored_crops=len(scored), unscored_crops=len(rows)-len(scored),
        all_validation_crops_scored=len(scored) == len(rows),
        reference_instance_observations_all_crops=sum(r['reference_instance_observations'] for r in rows),
        candidate_instances_complete_crops=sum(r['decoding']['candidate_instances'] for r in rows if r['score'] is not None),
        partial_diagnostic_regions_unscored_crops=sum(r['decoding']['candidate_instances'] for r in rows if r['score'] is None),
        metrics_scope='only_complete_decoding_on_selected_station033_crops_not_full_images_or_final_test',
        metrics=decoding.aggregate(scored) if scored else None,
        synthetic_only=synthetic, inference_images_by_split=dict(train=0, validation=len(rows), test=0),
        inference_started=True, pixel_test_images_read=0, license_declared='CC-BY-4.0', license_decision='unreviewed',
        rows={_key(dict(sample_id=r['sample_id'])): r['row_sha256'] for r in rows},
        **dict.fromkeys(FALSE_FLAGS, False),
        notice='Nur Instanzvorschlaege aus vorhandenen Versuchsgewichten auf acht oeffentlichen Validierungscrops. '
               'Keine neue Trainingsrunde, Gesamtmodulzahl oder Freigabe. Grenzberuehrende Kandidaten bleiben ungeprueft; '
               'Praezision/Recall nur gegen veroeffentlichte projizierte Masken auf gueltigen Pixeln. '
               'Begrenzungsfehler bleiben unbewertet und werden nicht als null Fehler behandelt.')


def read_result(package, manifest, parent_job, output, report, *, allow_synthetic=False):
    parent, _, targets, ids = _parent(package, manifest, parent_job, allow_synthetic=allow_synthetic)
    body = dict(report); saved = body.pop('report_sha256', None)
    config = report.get('config', {})
    if (saved != fingerprint(body) or config != _configuration(parent, manifest, config.get('runtime'))
            or report.get('evaluation_id') != fingerprint(config)):
        raise ValueError('Validation lineage or sources changed')
    folder = trained._local(output/report['evaluation_id'])
    rows = [_row(folder, manifest['samples'][i], targets[i]) for i in ids]
    expected = _summary(config, rows, allow_synthetic)
    expected['report_sha256'] = fingerprint(expected)
    if report != expected: raise ValueError('Validation counts or flags changed')
    if _json(folder/'report.json') != report: raise ValueError('Validation publication differs')
    return report


def run_validation(package, manifest, parent_job, reference_root, output, *, should_cancel=lambda: False,
                   allow_synthetic=False):
    parent, rgb, targets, ids = _parent(package, manifest, parent_job, allow_synthetic=allow_synthetic)
    config = _configuration(parent, manifest, dict(numpy=np.__version__, opencv=cv2.__version__,
        pillow=PIL.__version__, torch=parent['torch_version']))
    folder = trained._local(output/fingerprint(config)); folder.mkdir(parents=True, exist_ok=True)
    if (folder/'report.json').exists():
        return read_result(package, manifest, parent_job, output, _json(folder/'report.json'), allow_synthetic=allow_synthetic)
    def cancel():
        if should_cancel(): raise KeyboardInterrupt
    cancel(); model = None; rows = []
    for position, index in enumerate(ids):
        cancel(); sample = manifest['samples'][index]; key = _key(sample)
        if (folder/(key+'.json')).exists():
            row = _row(folder, sample, targets[index])
        else:
            if model is None:
                import torch
                spec = trained.specification()
                if torch.__version__ != spec['torch_version'] or torch.version.cuda is not None:
                    raise ValueError('Existing qualified Torch CPU runtime required')
                torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
                model = trained.reference_model(reference_root, spec, torch, n_classes=4)
                trained.checked_state(torch, trained._local(parent_job/trained.WEIGHTS).read_bytes(), model, trained._four_spec(spec))
            tensor = torch.from_numpy(rgb[index].transpose(2, 0, 1).copy()).float().div(255).unsqueeze(0)
            with torch.inference_mode(): logits = model(tensor)[0].numpy().copy()
            prediction, probability, diagnostic = decoding.decode(logits, should_cancel=should_cancel)
            cancel()
            _png(folder/(key+'-mask.png'), Image.fromarray(prediction.astype(np.uint16)))
            _png(folder/(key+'-preview.png'), preview(rgb[index], targets[index], prediction, probability))
            row = dict(evaluation_id=folder.name, sample_id=sample['sample_id'], source_record_sha256=sample['source_record_sha256'],
                reference_instance_observations=len(np.unique(targets[index][targets[index] > 0])),
                decoding=diagnostic, score=decoding.score_instances(targets[index], prediction)
                    if diagnostic['status'] == 'complete' else None,
                mask_sha256=trained._digest(folder/(key+'-mask.png')),
                preview_sha256=trained._digest(folder/(key+'-preview.png')))
            row['row_sha256'] = fingerprint(row)
            cancel(); trained._json_atomic(folder/(key+'.json'), row)
        rows.append(row)
        print(f'Instanzpruefung Validierung: {position+1}/{len(ids)} Ausschnitte', flush=True)
    cancel()
    if trained.read_report(parent_job, parent_job.name) != parent: raise ValueError('Parent weights or report changed')
    if read_arrays(package, manifest, allow_synthetic=allow_synthetic)[0].shape != rgb.shape:
        raise ValueError('Numeric inputs changed')
    report = _summary(config, rows, allow_synthetic); report['report_sha256'] = fingerprint(report)
    trained._json_atomic(folder/'report.json', report)
    return read_result(package, manifest, parent_job, output, report, allow_synthetic=allow_synthetic)
