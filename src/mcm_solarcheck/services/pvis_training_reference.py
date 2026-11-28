"""Versioned PVIS pilot partition and label semantics, without pixels or training."""
from hashlib import sha256
import json
import re

from mcm_solarcheck.review.training_split import assert_no_group_leakage

LABEL_POLICY = 'pvis-projected-whole-module-1'
SPLIT_CHECK = 'solarcheck-pvis-training-reference-1'
REPORT = 'training-reference.json'
# 033 is held out from the publisher's training pool, never from its test set.
ROLES = {'009': ('train', 'train'), '033': ('train', 'validation'), '024': ('test', 'test')}


def annotation_contract(policy_id=LABEL_POLICY):
    """Do not reinterpret projected outlines as visible-only manual labels."""
    if policy_id != LABEL_POLICY:
        raise ValueError('PVIS projected labels cannot be mixed with a different label policy')
    return dict(id=LABEL_POLICY, target='whole_module_projected_including_occluded_parts',
        image_domain='undistorted_rgb_drone_single_views', task='instance_segmentation',
        multipart_annotation='keep_fragments_in_one_instance',
        occlusion='preserve_publisher_projection_no_inferred_visible_mask',
        instance_id_scope='station_and_image_annotation_not_cross_view_physical_id',
        visible_corner_labels_compatible=False, automatic_visibility_filter_available=False,
        occluded_module_count=None)


def build_partition(source_rows, *, label_policy=LABEL_POLICY):
    """Bind one entire station to each role; image/crop-level splitting is forbidden."""
    policy = annotation_contract(label_policy)
    if not isinstance(source_rows, (list, tuple)) or len(source_rows) != 3:
        raise ValueError('Exactly three source stations required')
    rows, seen = [], set()
    for row in source_rows:
        if not isinstance(row, dict) or row.get('station') not in ROLES:
            raise ValueError('Unknown PVIS pilot station')
        station = row['station']
        upstream, role = ROLES[station]
        if station in seen or row.get('split') != upstream:
            raise ValueError('Duplicate station or changed publisher split')
        if (not isinstance(row.get('archive_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', row['archive_sha256'])
                or any(type(row.get(k)) is not int or row[k] <= 0
                       for k in ('images', 'annotation_observations', 'archive_bytes'))):
            raise ValueError('Verified source identity and counts required')
        seen.add(station)
        rows.append(dict(row, source_split=upstream, split=role,
            group_id=f'pvis-10k:1.0.0:station-{station}'))
    if seen != set(ROLES):
        raise ValueError('Training, validation and untouched test stations required')
    assert_no_group_leakage((row['group_id'], row['split']) for row in rows)
    rows.sort(key=lambda row: ('train', 'validation', 'test').index(row['split']))
    partition = dict(schema=1, dataset='pvis-10k-1.0.0', stations=rows,
        annotation_contract=policy, model_selection_split='validation',
        test_reserved_for_final_evaluation=True, crops_inherit_station_split=True,
        split_scope='station_not_image_or_annotation')
    encoded = json.dumps(partition, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return dict(partition=partition, partition_sha256=sha256(encoded.encode('utf-8')).hexdigest(),
        stations=rows, split_images={row['split']: row['images'] for row in rows},
        split_annotation_observations={row['split']: row['annotation_observations'] for row in rows},
        images=sum(row['images'] for row in rows),
        annotation_observations=sum(row['annotation_observations'] for row in rows))
