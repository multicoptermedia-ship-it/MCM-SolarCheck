"""Recover exactly the existing public033 validation crops at native512.

No download, new split, test archive, training, private image or disk pixel cache.
The original source-bound adapter and saved256 corpus stay unchanged.
"""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import zipfile

import numpy as np

from . import pvis_image_adapter as pixels
from . import pvis_learning_corpus as corpus
from .pvis_public_training_data import fingerprint, training_arrays

PROFILE = dict(id='pvis-existing24-validation033-native512-1',
    source='https://zenodo.org/records/23886365', station='033',
    split='validation', crops=24, native_size=512, decoder='existing_native_adapter',
    source_hash='publisher_full_zip_sha256_before_jpeg_read',
    identity='original_record_sha_and_exact_existing_rgb_and_label_reduction',
    source_training_archive_used_as_local_validation=True,
    test_archive_opened=False, customer_images_read=False, pixel_cache_written=False)


def verify_native_pair(sample, stored_rgb, stored_labels, record_sha256):
    rgb, labels = training_arrays(sample.rgb,sample.instances)
    record=dict(sample.record)
    saved=record.pop('record_sha256',None)
    if (sample.record.get('station')!='033' or sample.record.get('split')!='validation'
            or sample.record.get('record_sha256')!=record_sha256
            or saved!=pixels.value_digest(record)
            or sha256(sample.rgb.tobytes()).hexdigest()!=record.get('rgb_sha256')
            or sha256(sample.instances.astype('<i4').tobytes()).hexdigest()!=record.get('instances_sha256')
            or not np.array_equal(rgb,stored_rgb) or not np.array_equal(labels,stored_labels)):
        raise ValueError('Native public validation crop differs from saved256 source')
    if set(np.unique(sample.instances[sample.instances>0]))!=set(np.unique(labels[labels>0])):
        raise ValueError('Native and reduced public reference instance identities differ')


def native_crops(source, folder, manifest, reference, *, should_cancel=lambda:False):
    corpus.validate(manifest)
    rgb,labels = corpus.read_corpus(folder,manifest)
    selected = {row['sample_id']:(i,row) for i,row in enumerate(manifest['samples'])
                if row['split']=='validation'}
    if len(selected)!=24:
        raise ValueError('Existing24 public validation crops required')
    spec = reference.VALIDATION
    if spec.station!='033' or spec.split!='train':
        raise PermissionError('Only the original public033 validation source')
    path = Path(source)/spec.name
    if should_cancel():
        raise KeyboardInterrupt
    # Reuse full checksum, directory and COCO validation; never iterate STATIONS.
    reference.inspect_station(path,spec,should_cancel)
    result = {}
    with zipfile.ZipFile(path) as archive:
        coco = reference._read_json(archive,archive.getinfo(spec.prefix+'instances.json'))
        annotations = defaultdict(list)
        for ann in coco['annotations']:
            annotations[ann['image_id']].append(ann)
        for image in sorted(coco['images'],key=lambda x:x['id']):
            key = fingerprint(dict(station='033',image_id=image['id']))
            if key not in selected:
                continue
            if should_cancel():
                raise KeyboardInterrupt
            index,row = selected[key]
            name = image['file_name']
            name = name if name.startswith('images/') else 'images/'+name
            entry = archive.getinfo(spec.prefix+name)
            if entry.file_size>pixels.MAX_JPEG:
                raise ValueError('Bounded public JPEG required')
            sample = pixels.load_sample(archive.read(entry),image,annotations[image['id']],
                station='033',split='validation',should_cancel=should_cancel)
            verify_native_pair(sample,rgb[index],labels[index],row['source_record_sha256'])
            result[index] = sample
    if len(result)!=24:
        raise ValueError('Public native crop recovery incomplete')
    return rgb,labels,[(i,result[i]) for i in sorted(result)]
