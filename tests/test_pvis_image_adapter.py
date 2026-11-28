"""Actual generated JPEG pixels/COCO masks, never network or customer images."""
from dataclasses import replace
from hashlib import sha256
import importlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import numpy as np
from PIL import Image
import pytest

from test_pvis_public_reference import pv, reference
from mcm_solarcheck.services import pvis_image_adapter as pixels

audit = importlib.import_module('MCM_SolarCheck_PVIS_BILDADAPTER')


def jpeg(mode='RGB', size=(64, 64), color=(250, 4, 8)):
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, format='JPEG', quality=100, subsampling=0)
    return buffer.getvalue()


def annotation(identity=1, rings=None):
    rings = rings or [[8, 8, 24, 8, 24, 24, 8, 24]]
    xs = [x for ring in rings for x in ring[::2]]
    ys = [y for ring in rings for y in ring[1::2]]
    return dict(id=identity, image_id=1, category_id=1, iscrowd=0,
        bbox=[min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)],
        area=100, segmentation=rings)


def sample(annotations=None, **kwargs):
    return pixels.load_sample(jpeg(), dict(id=1, width=64, height=64),
        [annotation()] if annotations is None else annotations,
        station='009', split='train', size=32, **kwargs)


def test_rgb_unit_chw_and_exact_coco_half_pixel_convention():
    value = sample([annotation(rings=[[10, 10, 12, 10, 12, 12, 10, 12]])], window=(0, 0, 32, 32))
    expected = np.zeros((32, 32), dtype=bool)
    expected[10:12, 10:12] = True
    assert np.array_equal(value.instances == 1, expected)
    assert value.record['pixels']['pv'] == 4
    rgb = value.model_rgb()
    assert rgb.shape == (3, 32, 32) and rgb.dtype == np.float32
    assert rgb[0, 0, 0] > .9 and max(rgb[1, 0, 0], rgb[2, 0, 0]) < .1
    assert 0 <= rgb.min() <= rgb.max() <= 1


def test_crop_translation_is_not_a_resize():
    a = annotation(rings=[[20, 20, 24, 20, 24, 24, 20, 24]])
    value = sample([a], window=(16, 16, 32, 32))
    expected = np.zeros((32, 32), dtype=bool); expected[4:8, 4:8] = True
    assert np.array_equal(value.instances == 1, expected)
    assert value.record['window'] == [16, 16, 32, 32]


def test_multipart_is_one_instance_and_adjacent_modules_stay_separate():
    a = annotation(1, [[8, 8, 12, 8, 12, 12, 8, 12], [16, 8, 20, 8, 20, 12, 16, 12]])
    b = annotation(2, [[12, 8, 16, 8, 16, 12, 12, 12]])
    value = sample([a, b], window=(0, 0, 32, 32))
    ids, masks = value.instance_masks()
    assert ids.tolist() == [1, 2] and masks.shape == (2, 32, 32)
    assert masks[0].sum() == 32 and masks[1].sum() == 16
    assert value.instances[9, 9] == value.instances[9, 17] == 1
    assert value.instances[9, 13] == 2


def test_overlap_and_boundary_modules_are_ignored_with_a_margin():
    a = annotation(1, [[8, 8, 16, 8, 16, 16, 8, 16]])
    b = annotation(2, [[12, 8, 20, 8, 20, 16, 12, 16]])
    cut = annotation(3, [[28, 8, 40, 8, 40, 16, 28, 16]])
    value = sample([a, b, cut], window=(0, 0, 32, 32))
    assert value.instances[10, 10] == 1 and value.instances[10, 18] == 2
    assert value.instances[10, 14] == -1 and value.semantic[10, 14] == 255
    assert value.semantic[7, 14] == 255  # one-pixel safety margin
    assert np.all(value.semantic[8:16, 28:32] == 255)
    assert value.record['boundary_instances_ignored'] == 1


def test_source_edge_and_padding_are_not_background():
    a = annotation(1, [[0, 8, 8, 8, 8, 16, 0, 16]])
    value = sample([a], window=(0, 0, 32, 32))
    assert np.all(value.semantic[8:16, :8] == 255)
    assert value.record['retained_instances'] == 0
    padded = sample(window=(48, 48, 32, 32))
    assert np.all(padded.semantic[16:, :] == 255)
    assert np.all(padded.rgb[16:, :] == 0)


def test_no_annotations_is_unknown_not_a_negative_sample():
    value = sample([])
    assert np.all(value.instances == -1) and np.all(value.semantic == 255)
    assert value.record['eligible'] is False and value.record['unannotated_image'] is True
    assert value.instance_masks()[1].shape == (0, 32, 32)


def test_instance_targets_carry_validity_instead_of_false_negative_labels():
    value = sample([])
    targets = value.instance_targets()
    assert targets['masks'].shape == (0, 32, 32)
    assert not np.any(targets['valid_pixels'])
    mixed = sample([annotation(), annotation(2, [[28, 8, 40, 8, 40, 16, 28, 16]])], window=(0, 0, 32, 32))
    assert not mixed.instance_targets()['valid_pixels'][10, 30]
    assert mixed.instance_targets()['valid_pixels'][10, 10]


def test_last_integer_source_pixel_is_not_claimed_as_a_complete_module():
    a = annotation(1, [[56, 8, 63, 8, 63, 16, 56, 16]])
    value = sample([a], window=(32, 0, 32, 32))
    assert value.record['boundary_instances_ignored'] == 1
    assert value.record['retained_instances'] == 0


@pytest.mark.parametrize('kwargs', [dict(station='024', split='test'), dict(station='033', split='train'),
                                  dict(station='009', split='validation')])
def test_test_pixels_and_changed_roles_rejected_before_decoding(kwargs):
    with pytest.raises(PermissionError):
        pixels.load_sample(b'never decode this', dict(id=1, width=64, height=64), [], **kwargs)


@pytest.mark.parametrize('data', [jpeg(size=(63, 64)), jpeg(mode='L', color=100)])
def test_decode_requires_actual_rgb_and_matching_dimensions(data):
    with pytest.raises(ValueError):
        pixels.load_sample(data, dict(id=1, width=64, height=64), [annotation()],
                           station='009', split='train', size=32)


def test_crop_selection_is_deterministic_and_preview_has_no_metadata():
    a = sample()
    b = sample()
    assert a.record == b.record
    sheet = pixels.preview(a)
    assert sheet.size == (96, 56) and not sheet.getexif() and not sheet.info


def pixel_station(source, spec, *, unknown=False):
    images = [dict(id=i, width=64, height=64, file_name=f'{i}.jpg') for i in (1, 2)]
    annotations = [annotation(1)]
    if not unknown:
        a = annotation(2); a['image_id'] = 2; annotations.append(a)
    # Invalid test JPEGs prove that preparation never reads those pixel inputs.
    payload = {spec.prefix+f'images/{i}.jpg': (b'test-pixels-must-not-be-read' if spec.split == 'test' else jpeg())
               for i in (1, 2)}
    payload[spec.prefix+'instances.json'] = json.dumps(dict(images=images, annotations=annotations,
        categories=[dict(id=1, name='pv_panel')])).encode()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for name, value in payload.items(): z.writestr(name, value)
    content = buffer.getvalue(); (source/spec.name).write_bytes(content)
    return replace(spec, images=2, annotations=len(annotations),
                   unpacked=sum(map(len, payload.values())), size=len(content), sha256=sha256(content).hexdigest())


@pytest.fixture
def public_pixels(reference, monkeypatch):
    source, root, specs = reference
    monkeypatch.setattr(pv, 'STATIONS', tuple(pixel_station(source, spec) for spec in specs))
    monkeypatch.setattr(pv, 'VALIDATION', pixel_station(source, pv.VALIDATION, unknown=True))
    pv.intake(root, source); pv.prepare_splits(root, source)
    return source, root


def test_audit_reopen_and_existing_reports_without_test_pixels(public_pixels, monkeypatch):
    _, root = public_pixels
    before = {name: (root/name).read_bytes() for name in ('reference.json', 'training-reference.json')}
    result = audit.audit(root)
    assert result['decoded_images_by_split'] == dict(train=2, validation=2, test=0)
    assert result['unannotated_images_ignored_by_split'] == dict(train=0, validation=1, test=0)
    assert result['eligible_crops_by_split'] == dict(train=2, validation=1, test=0)
    assert result['training_validation_image_decoding_verified'] is True
    for flag in audit.FALSE_FLAGS: assert result[flag] is False
    assert {name: (root/name).read_bytes() for name in before} == before
    monkeypatch.setattr(pixels, 'load_sample', lambda *a, **k: pytest.fail('Reopen decoded JPEGs'))
    assert audit.audit(root, show=True) == result
    assert audit.audit(root) == result  # complete same-profile audit is reused
    assert not list(root.rglob('*.jpg'))


def test_interruption_resumes_by_rechecking_existing_records(public_pixels):
    _, root = public_pixels
    with pytest.raises(KeyboardInterrupt):
        audit.audit(root, should_cancel=lambda: bool(list((root/audit.FOLDER).glob('*/sample-*.json'))))
    assert not (root/audit.REPORT).exists()
    record = next((root/audit.FOLDER).glob('*/sample-*.json'))
    before = record.read_bytes()
    result = audit.audit(root)
    assert record.read_bytes() == before and result == audit.audit(root, show=True)


@pytest.mark.parametrize('kind', ['record', 'preview', 'manifest', 'report', 'config'])
def test_tampering_blocks_reopen_without_changing_previous_reference(public_pixels, kind):
    _, root = public_pixels
    result = audit.audit(root)
    folder = root/audit.FOLDER/result['adapter_id']
    target = (next(folder.glob('sample-*.json')) if kind == 'record' else
              folder/'train-preview.png' if kind == 'preview' else
              folder/'completed.json' if kind == 'manifest' else
              folder/'config.json' if kind == 'config' else root/audit.REPORT)
    target.write_bytes(target.read_bytes()+b'changed')
    with pytest.raises(ValueError): audit.audit(root, show=True)
    assert pv.prepare_splits(root, show=True)['images'] == 6


def test_failure_of_new_profile_preserves_completed_report(public_pixels, monkeypatch):
    _, root = public_pixels
    audit.audit(root); before = (root/audit.REPORT).read_bytes()
    monkeypatch.setattr(pixels, 'runtime', lambda: dict(new_runtime='synthetic-change'))
    def cancel(*a, **k): raise KeyboardInterrupt
    monkeypatch.setattr(pixels, 'load_sample', cancel)
    with pytest.raises(KeyboardInterrupt): audit.audit(root)
    assert (root/audit.REPORT).read_bytes() == before


def test_full_disk_and_concurrent_intake_do_not_change_reports(public_pixels, monkeypatch):
    _, root = public_pixels
    before = (root/'training-reference.json').read_bytes()
    monkeypatch.setattr(audit.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    with pytest.raises(OSError): audit.audit(root)
    assert (root/'training-reference.json').read_bytes() == before
    with pv.package_lock(root, 'pvis-package.lock'):
        child = subprocess.run([sys.executable, str(Path(audit.__file__)), '--prefix', str(root)],
                               capture_output=True, text=True, timeout=15)
    assert child.returncode == 2 and json.loads(child.stdout)['error_code'] == 'LOCAL_IO'


def test_cli_show_outputs_only_safe_audit_summary(public_pixels, capsys):
    _, root = public_pixels
    audit.audit(root)
    assert audit.main(['--prefix', str(root), '--show']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['check'] == pixels.CHECK and str(root) not in json.dumps(result)
