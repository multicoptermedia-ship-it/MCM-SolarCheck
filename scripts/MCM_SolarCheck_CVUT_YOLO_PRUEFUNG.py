"""Explicit PUBLIC CVUT/PVIS validation; no training or customer registration.

Developer research entrypoint in an isolated, qualified CPU environment. --show
opens only a completed JSON report and never imports Torch or Ultralytics.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

sys.path[:0] = [str(Path(__file__).resolve().parent),
                 str(Path(__file__).resolve().parents[1]/'src')]
from MCM_SolarCheck_CVUT_PAKETPRUEFUNG import atomic_json, local, package_lock

CHECK = 'solarcheck-cvut-yolo-public-module-validation-1'
NATIVE_CHECK = 'solarcheck-cvut-yolo-native-comparison-1'
TILED_CHECK = 'solarcheck-cvut-yolo-full-image-tiling-1'
FALSE_FLAGS = ('test_pixels_read', 'customer_images_read', 'training_started',
    'model_updated', 'automatically_accepted', 'physical_module_ids_confirmed',
    'coverage_verified', 'georeferencing_verified', 'temperature_verified',
    'accuracy_verified', 'commercial_training_approved', 'production_approved')


def sealed(value):
    value = dict(value)
    value.pop('report_sha256', None)
    value['report_sha256'] = sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return value


def show(path):
    # Read-only public reports may be checked into the repository. The older
    # write-side helper intentionally forbids checkout paths and stays intact.
    path = Path(path).expanduser().resolve(strict=True)
    if path.stat().st_size > 1_000_000:
        raise ValueError('Bounded public research report required')
    value = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value != sealed(value) or value.get('check') not in (CHECK,NATIVE_CHECK,TILED_CHECK)
            or value.get('status') != 'finished_public_research_not_production'
            or any(value.get(k) is not False for k in FALSE_FLAGS)):
        raise ValueError('Public report identity or scope changed')
    if value['check'] == TILED_CHECK:
        from mcm_solarcheck.services.cvut_yolo_tiled_comparison import verify_report
        return verify_report(value)
    from mcm_solarcheck.vision.pvis_instance_decoding import aggregate
    rows = value.get('crops')
    if not isinstance(rows,list) or len(rows)!=24:
        raise ValueError('Public report totals differ')
    if value['check']==NATIVE_CHECK:
        from mcm_solarcheck.services.cvut_yolo_native_comparison import METRICS
        if (value.get('metrics')!={k:aggregate([r[k] for r in rows]) for k in METRICS}
                or value.get('reference_geometry')!={k:sum(r['reference_geometry'][k] for r in rows)
                    for k in ('reference_instances','old_aspect_rejected')}):
            raise ValueError('Public native comparison totals differ')
    elif (value.get('raw_mask_metrics') != aggregate([r['raw_masks'] for r in rows])
            or value.get('module_outline_metrics') != aggregate([r['module_outlines'] for r in rows])):
        raise ValueError('Public report totals differ')
    return value


def validate(corpus_path, published_path, output, *, candidate=None, candidate_sha256=None,
             should_cancel=lambda: False, native_source=None, tiled_source=None):
    if native_source is not None and tiled_source is not None:
        raise ValueError('Select one explicit public comparison mode')
    if should_cancel():
        raise KeyboardInterrupt
    from mcm_solarcheck.services import pvis_learning_corpus as corpus
    from mcm_solarcheck.vision import cvut_yolo_research as reference
    from mcm_solarcheck.vision import cvut_yolo_validation as validation
    from mcm_solarcheck.vision.pvis_instance_decoding import aggregate
    folder, published, output = local(corpus_path), local(published_path), local(output)
    if output.exists():
        raise ValueError('Preserve completed report; use a new public output filename')
    if published.stat().st_size != reference.PUBLIC_RGB['n'][0]:
        raise ValueError('Observed public RGB n checkpoint required')
    if candidate is not None and (not isinstance(candidate_sha256, str)
            or not re.fullmatch('[0-9a-f]{64}', candidate_sha256)):
        raise ValueError('Explicit observed candidate SHA256 required')
    manifest = json.loads(local(folder/'corpus.json').read_text(encoding='utf-8'))
    rgb, targets = corpus.read_corpus(folder, manifest)
    indices = [i for i,r in enumerate(manifest['samples']) if r['split'] == 'validation']
    if len(indices) != 24 or any(manifest['samples'][i]['station'] != '033' for i in indices):
        raise ValueError('Existing separate public033 validation corpus required')
    # The caller selects an isolated environment. Never install or fetch packages here.
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    import torch
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    data = published.read_bytes()
    state = reference.published_rgb_state(data, torch)
    weights_sha = sha256(data).hexdigest()
    if candidate is not None:
        path = local(candidate)
        if not 1 <= path.stat().st_size <= 30_000_000:
            raise ValueError('Bounded separate public candidate required')
        data = path.read_bytes()
        if sha256(data).hexdigest() != candidate_sha256:
            raise ValueError('Candidate SHA256 differs')
        from io import BytesIO
        state = torch.load(BytesIO(data), map_location='cpu', weights_only=True)
        weights_sha = candidate_sha256
    model = reference.reference_model(torch, state)
    native_result = None
    native_sources = {}
    if tiled_source is not None:
        import MCM_SolarCheck_PVIS_REFERENZ as public_reference
        from mcm_solarcheck.services import cvut_yolo_tiled_comparison as comparison
        from mcm_solarcheck.vision import module_tiles, cvut_yolo_outlines, module_quality, polygon_geometry
        native_result = comparison.compare(torch,model,local(tiled_source),manifest,public_reference,
            should_cancel=should_cancel,
            progress=lambda n,total: print(f'Oeffentliche Vollbildpruefung: {n}/{total} Abschnitte',
                file=sys.stderr) if n%60==0 else None)
        native_sources = dict(comparison=comparison,tiles=module_tiles,outlines=cvut_yolo_outlines,
            geometry=module_quality,polygon_geometry=polygon_geometry,public_reference=public_reference)
    if native_source is not None:
        import MCM_SolarCheck_PVIS_REFERENZ as public_reference
        from mcm_solarcheck.services import pvis_native_validation as native
        from mcm_solarcheck.services import cvut_yolo_native_comparison as comparison
        from mcm_solarcheck.vision import cvut_yolo_outlines
        from mcm_solarcheck.vision import module_quality
        from mcm_solarcheck.services import pvis_public_training_data
        rgb,targets,samples = native.native_crops(local(native_source),folder,manifest,
            public_reference,should_cancel=should_cancel)
        native_result = comparison.compare(torch,model,rgb,targets,samples,should_cancel=should_cancel)
        native_sources = dict(native_adapter=native,comparison=comparison,
            outlines=cvut_yolo_outlines,public_reference=public_reference,
            geometry=module_quality,original_adapter=native.pixels,
            original_reduction=pvis_public_training_data)
    rows = []
    for index in ([] if native_result is not None else indices):
        if should_cancel():
            raise KeyboardInterrupt
        boxes, masks, confidence = validation.infer(torch, model, rgb[index])
        outlines = validation.module_masks(boxes, masks, confidence)
        rows.append(dict(raw_masks=validation.score_masks(targets[index], masks),
            module_outlines=validation.score_masks(targets[index], outlines)))
    result = dict(check=CHECK, status='finished_public_research_not_production',
        profile=validation.PROFILE, corpus_manifest_sha256=sha256((folder/'corpus.json').read_bytes()).hexdigest(),
        weights_sha256=weights_sha, validation_station='033', crops=rows,
        raw_mask_metrics=aggregate([r['raw_masks'] for r in rows]),
        module_outline_metrics=aggregate([r['module_outlines'] for r in rows]),
        model_license_declared='AGPL-3.0', dataset_license_declared='CC-BY-4.0',
        runtime=dict(torch=torch.__version__, numpy=validation.np.__version__,
                     opencv=validation.cv2.__version__, ultralytics='8.1.29'),
        source_sha256={key: sha256(Path(module.__file__).read_bytes()).hexdigest()
            for key, module in dict(runner=sys.modules[__name__], reference=reference,
                                    validation=validation, corpus=corpus,**native_sources).items()},
        license_decision='unreviewed', **{k: False for k in FALSE_FLAGS})
    if native_source is not None:
        result.update(native_result,check=NATIVE_CHECK,profile=native.PROFILE,
            public_source_archive_sha256=public_reference.VALIDATION.sha256,
            public_source_archive_bytes=public_reference.VALIDATION.size,
            publisher_archive_sha256_verified=True)
        for key in ('raw_mask_metrics','module_outline_metrics'):
            result.pop(key)
    if tiled_source is not None:
        result.update(native_result,
            public_source_archive_sha256=public_reference.VALIDATION.sha256,
            public_source_archive_bytes=public_reference.VALIDATION.size,
            publisher_archive_sha256_verified=True)
        for key in ('raw_mask_metrics','module_outline_metrics','crops'):
            result.pop(key)
    result=sealed(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    with package_lock(output.parent, 'cvut-yolo-validation.lock'):
        if output.exists():
            raise ValueError('Preserve existing public result')
        if should_cancel():
            raise KeyboardInterrupt
        atomic_json(output, result)
        return show(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--show', type=Path, metavar='REPORT_JSON')
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--published-rgb', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compare-native-source',type=Path,
        help='Existing verified public PVIS folder; compare same24 crops at256 and512')
    parser.add_argument('--compare-tiled-source',type=Path,
        help='Existing verified public PVIS folder; compare fixed3 full033 images with overlapping native grids')
    args = parser.parse_args(argv)
    if args.show:
        value = show(args.show)
    else:
        if not all((args.corpus,args.published_rgb,args.output)):
            parser.error('--corpus, --published-rgb and a new --output are required')
        value = validate(args.corpus,args.published_rgb,args.output,
            candidate=args.candidate,candidate_sha256=args.candidate_sha256,
            native_source=args.compare_native_source,tiled_source=args.compare_tiled_source)
    print(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
