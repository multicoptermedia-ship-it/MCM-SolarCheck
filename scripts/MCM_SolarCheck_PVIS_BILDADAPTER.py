"""Audit verified public RGB/instance crops locally, without training or downloads."""
import argparse
from collections import defaultdict
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

sys.path[:0] = [str(Path(__file__).resolve().parent),
                 str(Path(__file__).resolve().parents[1] / 'src')]
import MCM_SolarCheck_PVIS_REFERENZ as reference
from MCM_SolarCheck_CVUT_PAKETPRUEFUNG import atomic_json, digest, local, package_lock

REPORT = 'image-adapter.json'
FOLDER = 'image-adapter'
FALSE_FLAGS = ('training_started', 'training_authorized', 'customer_images_read',
    'customer_images_exported', 'training_dataset_exported', 'model_updated',
    'accuracy_verified', 'automatically_accepted', 'physical_module_ids_confirmed',
    'coverage_verified', 'georeferencing_verified', 'temperature_verified',
    'pair_registered', 'production_approved', 'visible_corner_eligibility_verified',
    'original_cvut_profile_verified', 'test_pixels_read')


def _json(path):
    path = local(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError('Adapter metadata too large')
    return json.loads(path.read_text('utf-8'))


def _checked_reference(root, should_cancel):
    base = reference._saved_base(root, should_cancel)
    actual = reference._split_report(root, base, should_cancel)
    if _json(root/reference.REPORT) != actual:
        raise ValueError('Confirmed station partition changed')
    return actual


def _sources(root):
    # Test archive metadata is verified by _checked_reference, but test JPEGs
    # are NEVER opened, sampled, previewed or used to choose this profile.
    for spec, role in ((reference.STATIONS[0], 'train'), (reference.VALIDATION, 'validation')):
        with zipfile.ZipFile(local(root/spec.name)) as archive:
            data = reference._read_json(archive, archive.getinfo(spec.prefix+'instances.json'))
            annotations = defaultdict(list)
            for annotation in data['annotations']:
                annotations[annotation['image_id']].append(annotation)
            for image in sorted(data['images'], key=lambda i: i['id']):
                yield spec, role, archive, image, annotations[image['id']]


def _key(station, image_id):
    from hashlib import sha256
    return 'sample-'+sha256(f'{station}:{image_id}'.encode('ascii')).hexdigest()+'.json'


def _record(folder, station, role, image, annotations, size, adapter):
    name = _key(station, image['id'])
    path = local(folder/name)
    value = _json(path)
    content = dict(value)
    check = content.pop('record_sha256', None)
    if (check != adapter.value_digest(content)
            or (value.get('station'), value.get('split'), value.get('image_id')) != (station, role, image['id'])
            or value.get('unannotated_image') != (not bool(annotations))):
        raise ValueError('Adapter image record changed')
    counts = value.get('pixels', {})
    if (set(counts) != {'background', 'pv', 'ignored'}
            or any(type(v) is not int or v < 0 for v in counts.values())
            or sum(counts.values()) != size**2):
        raise ValueError('Invalid adapter pixel totals')
    return name, value


def _summary(folder, config, records, adapter, ref):
    pixels = {role: dict(background=0, pv=0, ignored=0) for role in ('train', 'validation')}
    decoded, eligible, unknown, instances, boundary = (dict(train=0, validation=0, test=0) for _ in range(5))
    for record in records:
        role = record['split']
        decoded[role] += 1
        eligible[role] += int(record['eligible'])
        unknown[role] += int(record['unannotated_image'])
        instances[role] += record['retained_instances']
        boundary[role] += record['boundary_instances_ignored']
        for key, count in record['pixels'].items(): pixels[role][key] += count
    if not all(eligible[role] for role in ('train', 'validation')):
        raise ValueError('No eligible complete module crop for one preparation split')
    previews = {role: digest(local(folder/(role+'-preview.png'))) for role in ('train', 'validation')}
    return dict(check=adapter.CHECK, status='adapter_verified_no_training',
        adapter_id=adapter.value_digest(config), partition_sha256=ref['partition_sha256'],
        source_url=ref['source_url'], dataset_version=ref['version'],
        profile=config['profile'], runtime=config['runtime'], source_code_sha256=config['source_code_sha256'],
        decoded_images_by_split=decoded, eligible_crops_by_split=eligible,
        unannotated_images_ignored_by_split=unknown, cropped_instance_observations=instances,
        boundary_instances_ignored=boundary, crop_pixels_by_split=pixels,
        public_preview_images_written=2, preview_sha256=previews,
        training_validation_image_decoding_verified=True, full_dataset_image_decoding_verified=False,
        license_declared=ref['license_declared'], license_decision=ref['license_decision'],
        commercial_training_approved=False, **dict.fromkeys(FALSE_FLAGS, False),
        notice='Nur öffentlicher Bild-/Instanzmaskenadapter: ein nativer Ausschnitt je Trainings-/Validierungsbild. '
               'Keine vollständige Bild-/Anlagenabdeckung. Bilder ohne Annotationen vollständig ignoriert, '
               'keine bestätigten Negativbilder. Testpixel unangetastet. Projizierte Modulflächen sind keine '
               'sichtbaren manuellen Eckenumrisse. Kein Training oder Modell gestartet.')


def _read_completed(root, ref, config, adapter, should_cancel):
    state = _json(root/REPORT)
    adapter_id = adapter.value_digest(config)
    if state.get('adapter_id') != adapter_id:
        raise ValueError('Adapter profile or runtime changed; use original Python or prepare a new audit')
    folder = local(root/FOLDER/adapter_id)
    manifest = _json(folder/'completed.json')
    if (_json(folder/'config.json') != config or manifest.get('config') != config
            or digest(folder/'completed.json') != state.get('manifest_sha256')):
        raise ValueError('Adapter manifest changed')
    records, index = [], {}
    for spec, role, _, image, annotations in _sources(root):
        reference._cancel(should_cancel)
        name, record = _record(folder, spec.station, role, image, annotations, config['profile']['size'], adapter)
        records.append(record)
        index[name] = digest(folder/name)
    if index != manifest.get('records'):
        raise ValueError('Adapter records differ from committed manifest')
    actual = _summary(folder, config, records, adapter, ref)
    actual['manifest_sha256'] = digest(folder/'completed.json')
    if state != actual:
        raise ValueError('Adapter report, previews or verification flags changed')
    return actual


def _png(target, sheet):
    target = local(target)
    buffer = BytesIO()
    sheet.save(buffer, format='PNG')
    data = buffer.getvalue()
    if target.exists():
        if target.stat().st_size > 8_000_000 or target.read_bytes() != data:
            raise ValueError('Existing public preview changed')
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='pvis-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(target)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def audit(prefix, *, show=False, should_cancel=lambda: False):
    root = local(prefix)
    if not root.is_dir(): raise FileNotFoundError('Confirmed public reference required')
    with package_lock(root, 'pvis-package.lock'):
        ref = _checked_reference(root, should_cancel)
        # Lazy dependency boundary: the prior intake remains standard-library only.
        from mcm_solarcheck.services import pvis_image_adapter as adapter
        config = dict(schema=1, partition_sha256=ref['partition_sha256'],
            profile=adapter.PROFILE, runtime=adapter.runtime(),
            source_code_sha256=dict(adapter=digest(Path(adapter.__file__)),
                runner=digest(Path(__file__)), reference=digest(Path(reference.__file__)),
                rasterizer=digest(Path(sys.modules[adapter._polygons_mask.__module__].__file__))))
        target = local(root/REPORT)
        if show or (target.exists() and _json(target).get('adapter_id') == adapter.value_digest(config)):
            return _read_completed(root, ref, config, adapter, should_cancel)
        reference._cancel(should_cancel)
        if shutil.disk_usage(root).free < 50_000_000: raise OSError(28, 'Adapter audit needs 50MB free')
        folder = local(root/FOLDER/adapter.value_digest(config))
        if folder.exists():
            if _json(folder/'config.json') != config: raise ValueError('Unowned adapter folder')
        else:
            folder.mkdir(parents=True)
            atomic_json(folder/'config.json', config)
        records, index, previews = [], {}, set()
        for number, (spec, role, archive, image, annotations) in enumerate(_sources(root), 1):
            reference._cancel(should_cancel)
            name = image['file_name']
            name = name if name.startswith('images/') else 'images/'+name
            info = archive.getinfo(spec.prefix+name)
            if info.file_size > adapter.MAX_JPEG: raise ValueError('Public JPEG exceeds byte cap')
            sample = adapter.load_sample(archive.read(info), image, annotations,
                station=spec.station, split=role, should_cancel=should_cancel)
            path = local(folder/_key(spec.station, image['id']))
            if path.exists():
                if _json(path) != sample.record: raise ValueError('Partial adapter record changed; not reused')
            else:
                atomic_json(path, sample.record)
            records.append(sample.record)
            index[path.name] = digest(path)
            if role not in previews and sample.record['eligible']:
                _png(folder/(role+'-preview.png'), adapter.preview(sample))
                previews.add(role)
            if number % 10 == 0:
                print(f'Oeffentliche RGB-/Maskenpruefung: {number} Bilder ...', file=sys.stderr, flush=True)
        result = _summary(folder, config, records, adapter, ref)
        reference._cancel(should_cancel)
        atomic_json(folder/'completed.json', dict(config=config, records=index))
        result['manifest_sha256'] = digest(folder/'completed.json')
        reference._cancel(should_cancel)
        atomic_json(target, result)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-PVIS-Referenz')
    parser.add_argument('--show', action='store_true', help='Gespeicherten Adapter ohne JPEG-Dekodierung pruefen')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(audit(args.prefix, show=args.show), indent=2, ensure_ascii=False), flush=True)
        return 0
    except KeyboardInterrupt:
        code, status = 'CANCELLED', 'cancelled'
    except Exception as error:
        code = ('APP_RUNTIME_MISSING' if isinstance(error, ImportError)
                else 'REFERENCE_OR_AUDIT_MISSING' if isinstance(error, FileNotFoundError)
                else 'ADAPTER_VERIFICATION_FAILED' if isinstance(error, ValueError)
                else 'LOCAL_IO' if isinstance(error, OSError) else 'ADAPTER_FAILED')
        status = 'failed'
    print(json.dumps(dict(check='solarcheck-pvis-image-adapter-failure-1', status=status,
        error_code=code, training_started=False, model_updated=False, customer_images_read=False,
        next_step='Nur diesen Diagnoseblock mitteilen. Vorhandenes App-Python auf F: verwenden; '
                  'keine Neuinstallation oder erneuten Referenzdownloads. Bestehende Berichte bleiben erhalten.')))
    return 130 if code == 'CANCELLED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
