"""Run a separately installed MicMac on explicit local project working copies.

Only orchestration and standard GDAL/PROJ conversion live here. MicMac performs
matching, self calibration, orientation, surface reconstruction and mosaicking.
No execution occurs during imports, project opening or configuration reads.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import tempfile
import time


class MicMacCancelled(RuntimeError):
    pass


class MicMacError(RuntimeError):
    """Messages contain stage names, never private process output or GPS."""


@dataclass(frozen=True)
class MicMacResult:
    project_id: str
    input_signature: str
    rgb_geotiff: Path
    thermal_geotiff: Path
    workspace: Path
    crs: str


def _cancelled(should_cancel):
    if should_cancel():
        raise MicMacCancelled("Lokale Orthofoto-Erzeugung abgebrochen.")


def _inputs(database, project_id):
    uri = database.path.resolve(strict=True).as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        if db.execute("SELECT 1 FROM projects WHERE project_id=?", (project_id,)).fetchone() is None:
            raise MicMacError("Das ausgewählte Projekt existiert nicht mehr.")
        layers = []
        for table, modality in (("image_frames", "rgb"), ("thermal_frames", "thermal")):
            layers.append(tuple(dict(row) for row in db.execute(
                f"SELECT f.frame_id,f.source_file,f.latitude,f.longitude,f.altitude_m,"
                f"t.content_sha256 FROM {table} AS f LEFT JOIN training_samples AS t "
                "ON t.project_id=f.project_id AND t.source_frame_id=f.frame_id AND t.modality=? "
                "WHERE f.project_id=? ORDER BY f.frame_id", (modality, project_id),
            )))
    return tuple(layers)


def micmac_input_signature(database, project_id):
    return sha256(json.dumps(_inputs(database, project_id), sort_keys=True).encode()).hexdigest()


def _projected_crs(layers, requested):
    from pyproj import CRS, Transformer, network
    from pyproj.aoi import AreaOfInterest
    from pyproj.database import query_utm_crs_info

    # PROJ must use installed grids, even if the host enabled network access.
    network.set_network_enabled(False)

    points = [row for layer in layers for row in layer]
    if any(len(layer) < 3 for layer in layers):
        raise MicMacError("Mindestens drei importierte RGB- und drei Thermalbilder erforderlich.")
    for row in points:
        coords = tuple(row[k] for k in ("longitude", "latitude", "altitude_m"))
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in coords):
            raise MicMacError("Importierte Kamerapositionen benötigen Länge, Breite und absolute Höhe.")
        if not (-180 <= coords[0] <= 180 and -90 <= coords[1] <= 90):
            raise MicMacError("Importierte Kamerakoordinaten liegen außerhalb des gültigen Bereichs.")
    west, east = min(p['longitude'] for p in points), max(p['longitude'] for p in points)
    south, north = min(p['latitude'] for p in points), max(p['latitude'] for p in points)
    if requested:
        try:
            crs = CRS.from_user_input(requested)
        except Exception:
            raise MicMacError("Das angegebene Ziel-Koordinatensystem ist ungültig.") from None
    else:
        candidates = query_utm_crs_info(
            datum_name="WGS 84", area_of_interest=AreaOfInterest(west, south, east, north),
        )
        covering = [c for c in candidates if c.area_of_use.west <= west <= east <= c.area_of_use.east
                    and c.area_of_use.south <= south <= north <= c.area_of_use.north]
        if len(covering) != 1:
            raise MicMacError("Keine eindeutige UTM-Zone: Ziel-Koordinatensystem bitte angeben.")
        crs = CRS.from_authority(covering[0].auth_name, covering[0].code)
    if (not crs.is_projected or len(crs.axis_info) != 2
            or any(a.unit_conversion_factor != 1 for a in crs.axis_info)):
        raise MicMacError("Ein zweidimensionales projiziertes Zielsystem mit Metereinheiten ist erforderlich.")
    area = crs.area_of_use
    if area and not (area.west <= west <= east <= area.east and area.south <= south <= north <= area.north):
        raise MicMacError("Ziel-Koordinatensystem passt nicht zu den importierten Kamerapositionen.")
    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True, allow_ballpark=False)
    return crs, transformer


def _stop_process(process):
    if os.name == "nt":
        # MicMac starts helper processes. Stop the owned tree, not just mm3d.
        killer = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        subprocess.run([str(killer), "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _execute(executable, args, cwd, log, should_cancel, *, timeout=6 * 60 * 60):
    """Explicit argv; process output stays only in the local private job folder."""
    _cancelled(should_cancel)
    env = os.environ.copy()
    env["PATH"] = str(executable.parent) + os.pathsep + env.get("PATH", "")
    env["PROJ_NETWORK"] = "OFF"
    options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
               if os.name == "nt" else {"start_new_session": True})
    with log.open("xb") as stream:
        process = subprocess.Popen(
            [str(executable), *args], cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, **options,
        )
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                _cancelled(should_cancel)
                if time.monotonic() >= deadline:
                    raise MicMacError("Zeitlimit einer MicMac-Stufe überschritten; lokales Protokoll prüfen.")
                try:
                    process.wait(timeout=.15)
                except subprocess.TimeoutExpired:
                    pass
            _cancelled(should_cancel)
            if process.returncode != 0:
                raise MicMacError(f"MicMac-Stufe {args[0]} fehlgeschlagen (Code {process.returncode}); lokales Protokoll prüfen.")
        finally:
            if process.poll() is None:
                _stop_process(process)


def _copy_source(row, destination, database, should_cancel):
    source = Path(row['source_file'])
    if not source.is_absolute():
        source = database.path.parent / source
    if not source.is_file() or any(p.is_symlink() for p in (source, *source.parents)):
        raise MicMacError("Importierte Bildquelle fehlt oder ist kein reguläres lokales Bild.")
    if source.suffix.lower() not in (".jpg", ".jpeg"):
        raise MicMacError("Dieser MicMac-Ablauf erwartet importierte JPEG-Bildserien.")
    before = source.stat()
    digest = sha256()
    with source.open('rb') as original, destination.open('xb') as copy:
        while chunk := original.read(1024 * 1024):
            _cancelled(should_cancel)
            digest.update(chunk)
            copy.write(chunk)
    after = source.stat()
    if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
            (after.st_size, after.st_mtime_ns, after.st_ino)
            or (row['content_sha256'] and digest.hexdigest() != row['content_sha256'].lower())):
        raise MicMacError("Importierte Bildquelle wurde geändert; kein Ergebnis übernehmen.")
    return source, (after.st_size, after.st_mtime_ns, after.st_ino)


def _geotiff(source, destination, crs):
    """GDAL copies an actual MicMac mosaic/geotransform; no pixel reconstruction."""
    import rasterio
    from rasterio.shutil import copy
    from rasterio.transform import Affine
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import inspect_existing_geotiff

    if not source.is_file() or any(p.is_symlink() for p in (source, *source.parents)):
        raise MicMacError("MicMac hat kein lokales Mosaik ausgegeben.")
    with rasterio.open(source) as dataset:
        if dataset.driver != 'GTiff' or dataset.transform == Affine.identity():
            raise MicMacError("MicMac-Ausgabe enthält keinen verwendbaren Rastertransform.")
        if dataset.crs is not None and dataset.crs != rasterio.crs.CRS.from_wkt(crs.to_wkt()):
            raise MicMacError("MicMac-Ausgabe hat ein abweichendes Koordinatensystem.")
        if dataset.crs is None and not source.with_suffix('.tfw').is_file():
            raise MicMacError("MicMac-Ausgabe benötigt eine belegte Worldfile-Referenz.")
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        copy(source, destination, driver='GTiff')
    with rasterio.open(destination, 'r+') as dataset:
        dataset.crs = rasterio.crs.CRS.from_wkt(crs.to_wkt())
        dataset.update_tags(MCM_SOURCE='MicMac', MCM_GEOREFERENCE='camera_gnss_unverified',
                            MCM_PRODUCT_STATUS='unverified_display_raster')
    inspect_existing_geotiff(destination)


def generate_micmac_orthophotos(database, project_id, executable, output_parent, *,
                                target_crs=None, should_cancel=None, on_progress=None):
    """Produce both rasters in one fresh private folder; caller registers atomically.

    Only explicit user action may call this. Imported GNSS camera centers are
    transformed using PROJ; their heights are retained, never replaced by guessed
    ground heights. Results remain unverified and thermal is display-only.
    """
    cancel = should_cancel or (lambda: False)
    _cancelled(cancel)
    exe = Path(executable)
    if (exe.name.lower() not in ('mm3d', 'mm3d.exe') or not exe.is_file()
            or any(p.is_symlink() for p in (exe, *exe.parents))):
        raise MicMacError("Eine separat installierte lokale mm3d-Programmdatei auswählen.")
    exe = exe.resolve(strict=True)
    parent = Path(output_parent)
    if not parent.is_dir() or any(p.is_symlink() for p in (parent, *parent.parents)):
        raise MicMacError("Einen vorhandenen privaten Ausgabeordner auswählen.")
    parent = parent.resolve(strict=True)
    if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file()
           for p in (parent, *parent.parents)):
        raise MicMacError("Bildberechnung und Ausgaben dürfen nicht in einem Git-Checkout liegen.")
    layers = _inputs(database, project_id)
    signature = sha256(json.dumps(layers, sort_keys=True).encode()).hexdigest()
    crs, transformer = _projected_crs(layers, target_crs)
    for layer in layers:
        for row in layer:
            source = Path(row['source_file'])
            source = (source if source.is_absolute() else database.path.parent / source).resolve()
            if parent == source.parent or parent in source.parents or source.parent in parent.parents:
                raise MicMacError("Ausgabeordner muss getrennt von den Originalbildordnern liegen.")
    workspace = Path(tempfile.mkdtemp(prefix='micmac-', dir=parent))
    manifest = workspace / 'job.json'
    record = {'project_id': project_id, 'input_signature': signature,
              'crs': crs.to_string(), 'status': 'running', 'thermal_value_kind': 'visual',
              'georeferencing_verified': False, 'temperature_verified': False}
    def save_status(status):
        record['status'] = status
        manifest.write_text(json.dumps(record, indent=2), encoding='utf-8')
    save_status('running')
    source_signatures = []
    try:
        for modality, rows in zip(('rgb', 'thermal'), layers):
            folder = workspace / modality
            folder.mkdir()
            positions = ['#F=N X Y Z']
            for index, row in enumerate(rows, 1):
                _cancelled(cancel)
                if on_progress:
                    on_progress(f'{modality.upper()}: Arbeitskopie {index}/{len(rows)}')
                name = f'{index:06d}.JPG'
                source_signatures.append(_copy_source(row, folder / name, database, cancel))
                x, y = transformer.transform(row['longitude'], row['latitude'], errcheck=True)
                if not all(math.isfinite(v) for v in (x, y)):
                    raise MicMacError("Kameraposition konnte nicht ins Zielsystem übertragen werden.")
                positions.append(f"{name} {x:.9f} {y:.9f} {row['altitude_m']:.9f}")
            (folder / 'positions.txt').write_text('\n'.join(positions) + '\n', encoding='ascii')
            pattern = '[0-9]{6}[.]JPG'
            commands = (
                ('Tapioca', 'All', pattern, '1200', 'Detect=mm3d:Digeo', 'Match=mm3d:Ann'),
                ('Tapas', 'RadialBasic', pattern, 'Out=Rel'),
                # OriConvert instantiates cameras even for center-only input.
                # Retain its standard EXIF-based initialization; disabling it
                # leaves neither Interne nor FileInterne and aborts conversion.
                ('OriConvert', 'OriTxtInFile', 'positions.txt', 'GPS', 'AddCalib=1'),
                ('CenterBascule', pattern, 'Rel', 'GPS', 'Ground'),
                ('Malt', 'Ortho', pattern, 'Ground', 'ZoomF=2'),
                ('Tawny', 'Ortho-MEC-Malt/', 'RadiomEgal=0', 'Out=Orthophotomosaic.tif'),
            )
            for step, command in enumerate(commands, 1):
                _cancelled(cancel)
                if on_progress:
                    on_progress(f'{modality.upper()}: MicMac {command[0]} ({step}/{len(commands)})')
                log_name = f'step-{step:02d}.log'
                try:
                    _execute(exe, command, folder, folder / log_name, cancel)
                except MicMacError as error:
                    # Only fixed sensor/stage names, never a private job path
                    # or any of MicMac's raw process output, enter the UI.
                    raise MicMacError(f'{modality.upper()}: {error} [{modality}/{log_name}]') from None
            _cancelled(cancel)
            _geotiff(folder / 'Ortho-MEC-Malt' / 'Orthophotomosaic.tif',
                     workspace / f'{modality}_ortho.tif', crs)
        _cancelled(cancel)
        if signature != micmac_input_signature(database, project_id):
            raise MicMacError("Projekteingaben wurden während der Berechnung geändert; kein Ergebnis übernehmen.")
        for source, expected in source_signatures:
            current = source.stat()
            if expected != (current.st_size, current.st_mtime_ns, current.st_ino):
                raise MicMacError("Bildquelle während der Berechnung geändert; kein Ergebnis übernehmen.")
        from mcm_solarcheck.services.orthophoto_pair_audit import audit_orthophoto_pair
        audit = audit_orthophoto_pair(workspace / 'rgb_ortho.tif', workspace / 'thermal_ortho.tif')
        if not audit.comparison_ready or not audit.common_pixel_fraction > 0:
            raise MicMacError("MicMac-Ergebnisse haben keine verwendbare gemeinsame Rasterabdeckung.")
        _cancelled(cancel)
        save_status('rasters_ready_unverified')
        return MicMacResult(project_id, signature, workspace / 'rgb_ortho.tif',
                            workspace / 'thermal_ortho.tif', workspace, crs.to_string())
    except MicMacCancelled:
        save_status('cancelled')
        raise
    except Exception:
        save_status('failed')
        raise
