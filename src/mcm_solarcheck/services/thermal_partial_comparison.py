"""Local visual comparison only; never register an incomplete orthophoto pair."""
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

import numpy as np

from .opensfm_dense_continuation import _digest
from .opensfm_thermal_partial import read_partial_preview
from .orthomosaic_geotiff_contract import inspect_existing_geotiff
from .orthophoto_layer_alignment import (
    OrthophotoLayerPair, _rgb_band_indices, _thermal_bands, aligned_preview_arrays,
)

CHECK = 'solarcheck-incomplete-thermal-comparison-1'
STATE = 'rgb-comparison.LOCAL.json'
VERDICTS = ('not_reviewed', 'looks_aligned', 'visible_offset')
FLAGS = ('coverage_verified', 'georeferencing_verified', 'temperature_verified', 'pair_registered')


def _local(path):
    path = Path(path)
    if (not path.is_absolute() or not path.is_file()
            or any(p.is_symlink() for p in (path, *path.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in path.parents)):
        raise ValueError('Vorhandene lokale Vergleichsdatei ausserhalb Git ohne Verknuepfungen waehlen.')
    return path


def _view(data):
    opacity, zoom = data.get('opacity', 50), data.get('zoom', 1.0)
    verdict, note = data.get('verdict', 'not_reviewed'), data.get('note', '')
    if (type(opacity) is not int or not 0 <= opacity <= 100
            or type(zoom) not in (int, float) or not .25 <= zoom <= 4
            or verdict not in VERDICTS or not isinstance(note, str) or len(note) > 2000):
        raise ValueError('Ungueltiger gespeicherter Sichtvergleich.')
    return dict(opacity=opacity, zoom=zoom, verdict=verdict, note=note)


@dataclass
class PartialThermalComparison:
    folder: Path
    rgb_path: Path
    thermal_path: Path
    label: str
    fingerprints: dict
    rgb: np.ndarray
    thermal: np.ndarray
    view: dict
    _pair: OrthophotoLayerPair = field(repr=False)


def open_partial_comparison(source, rgb_path=None):
    """Explicit exception for viewing a finished labelled preview, not for intake.

    Uses the existing GDAL display reprojection and slider arrays. No image
    matching, coordinate adjustment, temperature conversion or database access.
    Saved paths and free text stay in the private preview folder only.
    """
    import rasterio
    _local(Path(source) / 'job.json')
    loaded = read_partial_preview(source)
    if not loaded or loaded[1]['status'] != 'finished':
        raise ValueError('Zuerst eine fertige unvollstaendige Thermal-Teilvorschau laden.')
    folder, report = loaded
    thermal = _local(folder / 'undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif')
    record = None
    state = folder / STATE
    if rgb_path is None:
        with _local(state).open(encoding='utf-8') as stream:
            record = json.load(stream)
        if (not isinstance(record, dict) or record.get('check') != CHECK
                or any(record.get(key) is not False for key in FLAGS)):
            raise ValueError('Ungueltiger lokaler Vergleichsbericht.')
        rgb_path = record.get('rgb_path', '')
    rgb = _local(rgb_path)
    if rgb.samefile(thermal):
        raise ValueError('RGB und Thermal muessen verschiedene Dateien sein.')
    signatures = {name: _digest(path, lambda: False) for name, path in (('rgb', rgb), ('thermal', thermal))}
    fingerprints = {name: value[0] for name, value in signatures.items()}
    if record is not None and (record.get('fingerprints') != fingerprints
                               or record.get('thermal_path') != str(thermal)
                               or record.get('label') != report['label']):
        raise ValueError('Vergleichsdateien seit Speicherung veraendert; RGB bewusst neu auswaehlen.')
    rgb_reference = inspect_existing_geotiff(rgb)  # Regular intake gate stays active for RGB.
    with rasterio.open(thermal) as raster:
        tags = raster.tags()
        expected = dict(SOLARCHECK_INCOMPLETE='true', SOLARCHECK_PREVIEW_KIND='thermal_partial',
            SOLARCHECK_LABEL=report['label'], SOLARCHECK_PAIR_IMPORT_ALLOWED='false',
            SOLARCHECK_COVERAGE_VERIFIED='false', SOLARCHECK_GEOMETRY_VERIFIED='false',
            SOLARCHECK_TEMPERATURE_VERIFIED='false',
            SOLARCHECK_INCLUDED_IMAGES=str(report['included_images']),
            SOLARCHECK_SOURCE_IMAGES=str(report['source_images']),
            SOLARCHECK_EXCLUDED_IMAGES=str(report['excluded_images']))
        if any(tags.get(k) != v for k, v in expected.items()):
            raise ValueError('Thermal-Datei ist keine passend gekennzeichnete unvollstaendige Vorschau.')
        kind, bands = _thermal_bands(raster)
        if kind != 'visual_rgb':
            raise ValueError('Dieser Sichtvergleich erwartet ein Thermal-Farbbild, keine Temperaturmatrix.')
    thermal_reference = inspect_existing_geotiff(thermal, allow_incomplete_preview=True)
    with rasterio.open(rgb) as raster:
        rgb_bands = _rgb_band_indices(raster)
    pair = OrthophotoLayerPair(rgb, thermal, rgb_reference, thermal_reference, kind, rgb_bands, bands)
    pixels, heat = aligned_preview_arrays(pair, max_dimension=2048)
    if not np.isfinite(heat).all(axis=2).any():
        raise ValueError('Keine gemeinsame gueltige Rasterflaeche in den gespeicherten Koordinaten.')
    for name, path in (('rgb', rgb), ('thermal', thermal)):
        stat = path.stat()
        if signatures[name][1] != (stat.st_size, stat.st_mtime_ns, stat.st_ino):
            raise ValueError('Vergleichsdatei beim Lesen veraendert; erneut bewusst waehlen.')
    return PartialThermalComparison(folder, rgb, thermal, report['label'], fingerprints,
                                    pixels, heat, _view(record or {}), pair)


def save_partial_comparison(comparison, *, opacity, zoom, verdict, note):
    view = _view(dict(opacity=opacity, zoom=zoom, verdict=verdict, note=note))
    for key, path in (('rgb', comparison.rgb_path), ('thermal', comparison.thermal_path)):
        if _digest(_local(path), lambda: False)[0] != comparison.fingerprints[key]:
            raise ValueError('Vergleichsdateien veraendert; keine Beurteilung speichern.')
    record = dict(check=CHECK, label=comparison.label, rgb_path=str(comparison.rgb_path),
        thermal_path=str(comparison.thermal_path), fingerprints=comparison.fingerprints,
        saved_at=datetime.now().astimezone().isoformat(timespec='seconds'), **view,
        **dict.fromkeys(FLAGS, False))
    target = comparison.folder / STATE
    temporary = comparison.folder / 'rgb-comparison.LOCAL.next.json'
    if target.is_symlink() or temporary.is_symlink():
        raise ValueError('Vergleichsbericht darf keine Verknuepfung sein.')
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(target)
    comparison.view = view
    return record


def verify_partial_comparison(comparison):
    """Recheck explicitly selected rasters before local module work; no intake exception."""
    if not isinstance(comparison, PartialThermalComparison):
        raise ValueError('Geoeffneten lokalen Teilvorschau-Vergleich verwenden.')
    for name, path in (('rgb', comparison.rgb_path), ('thermal', comparison.thermal_path)):
        if _digest(_local(path), lambda: False)[0] != comparison.fingerprints[name]:
            raise ValueError('Vergleichsdateien veraendert; Modulpruefung gestoppt.')
    return comparison._pair
