"""Inspect the public CVUT U-Net package without extracting/loading any model."""
import argparse
from contextlib import contextmanager
import errno
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import pickletools
import re
import stat
import socket
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

URL = 'https://imr.ciirc.cvut.cz/uploads/Datasets/PV_UNET_models.zip'
ARCHIVE = 'PV_UNET_models.zip'
CHECK = 'solarcheck-cvut-package-inspection-1'
REPORT = 'cvut-package.LOCAL.json'
MAX_ARCHIVE = 400 * 1024**2
MAX_EXPANDED = 1024**3
MAX_TEXT = 64 * 1024
WEIGHT_SUFFIXES = {'.onnx', '.h5', '.hdf5', '.keras', '.pt', '.pth', '.ckpt', '.pb'}
FAILURE_CHECK = 'solarcheck-cvut-failure-1'
RGB_REPORT = 'cvut-rgb-layout.LOCAL.json'
# User-observed public archive, 20 November 2026; NOT a publisher attestation.
CVUT_ARCHIVE = dict(bytes=344288853,
                    sha256='61d981c2ebdd180f184265fb2429dc4151463721fc9121f805f1b84c8b8ab14b',
                    rgb_name='UNet_pv_module_rgb.pth', rgb_bytes=124239509)
MAX_PICKLE_METADATA = 2 * 1024**2


class PackageCheckError(ValueError):
    """Only fixed, path-free validation messages authored in this script."""


def failure_details(error):
    """Shareable diagnosis: never copy exception text, filenames or URLs."""
    cause = error.reason if isinstance(error, urllib.error.URLError) else error
    action = 'Offiziellen Download im Browser pruefen; oeffentliches ZIP optional mit --archive pruefen.'
    if isinstance(error, PackageCheckError):
        code, message = 'PACKAGE_CHECK', str(error)
        action = 'Genannte Paket-/Ordnerbedingung pruefen. Vorhandenen Bericht erhalten.'
    elif isinstance(error, urllib.error.HTTPError):
        code, message = 'HTTP_ERROR', 'Der Downloadserver meldet einen HTTP-Fehler.'
    elif isinstance(cause, ssl.SSLCertVerificationError):
        code, message = 'TLS_CERTIFICATE', 'Python kann das HTTPS-Zertifikat nicht bestaetigen.'
        action = 'Zertifikatspruefung eingeschaltet lassen; offiziellen Download bewusst im Browser pruefen.'
    elif isinstance(cause, ssl.SSLError):
        code, message = 'TLS_CONNECTION', 'Die verschluesselte Verbindung ist fehlgeschlagen.'
    elif isinstance(cause, socket.gaierror):
        code, message = 'DNS_LOOKUP', 'Der Downloadserver konnte nicht per Namensaufloesung erreicht werden.'
    elif isinstance(cause, TimeoutError):
        code, message = 'NETWORK_TIMEOUT', 'Verbindung oder Download hat das Zeitlimit von30Sekunden erreicht.'
    elif isinstance(error, (http.client.IncompleteRead, ConnectionError, urllib.error.ContentTooShortError)):
        code, message = 'DOWNLOAD_INTERRUPTED', 'Die Uebertragung wurde vorzeitig unterbrochen.'
    elif isinstance(error, urllib.error.URLError):
        code, message = 'NETWORK_CONNECTION', 'Python konnte den Downloadserver nicht erreichen.'
    elif isinstance(error, (zipfile.BadZipFile, zipfile.LargeZipFile)):
        code, message = 'INVALID_ZIP', 'Die erhaltene Datei ist kein lesbares vollstaendiges ZIP-Archiv.'
    elif isinstance(error, (json.JSONDecodeError, UnicodeError)):
        code, message = 'LOCAL_METADATA', 'Eine lokale Steuer-/Berichtsdatei ist nicht lesbar.'
        action = 'Diagnosecode mitteilen; gespeicherte Berichte nicht loeschen.'
    elif isinstance(error, PermissionError):
        code, message = 'LOCAL_ACCESS', 'Eine lokale Datei ist gesperrt oder nicht beschreibbar.'
        action = 'Andere Paketpruefung schliessen; Schreibzugriff auf den eigenen Pilotordner pruefen.'
    elif isinstance(error, OSError) and (error.errno == errno.ENOSPC or getattr(error, 'winerror', None) == 112):
        code, message = 'DISK_FULL', 'Auf dem Ziellaufwerk ist zu wenig freier Platz.'
        action = 'Freien Platz im Pilotlaufwerk pruefen; vorhandene Projektdateien erhalten.'
    elif isinstance(error, FileNotFoundError):
        code, message = 'LOCAL_FILE_MISSING', 'Eine benoetigte lokale Datei oder ein Ordner fehlt.'
        action = 'Ausgewaehltes oeffentliches Archiv und Pilotordner pruefen.'
    elif isinstance(error, OSError):
        code, message = 'LOCAL_IO', 'Ein lokaler Datei-/Sperrzugriff ist fehlgeschlagen.'
        action = 'Diagnosecode und Fehlernummer mitteilen; keine Dateien vorsorglich loeschen.'
    else:
        code, message = 'UNEXPECTED_ERROR', 'Die Paketpruefung wurde durch einen weiteren Fehler beendet.'
        action = 'Diesen Diagnoseblock als Text mitteilen; keine Bilder oder Projektdateien senden.'
    record = dict(check=FAILURE_CHECK, error_code=code, message=message, next_step=action,
                  exception_type=type(error).__name__, model_loaded=False,
                  training_started=False, inference_started=False, production_approved=False)
    if isinstance(error, urllib.error.HTTPError):
        record['http_status'] = error.code
    for name in ('errno', 'winerror'):
        value = getattr(cause, name, None)
        if type(value) is int:
            record[name] = value
    return record


def local(path):
    path = Path(path)
    if (not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in (path, *path.parents))):
        raise PackageCheckError('Absoluten privaten Ordner ausserhalb eines Git-Checkout verwenden.')
    return path


def digest(path):
    value = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            value.update(block)
    return value.hexdigest()


def checked_member_name(member, seen):
    # ZipInfo.filename normalizes backslashes on Windows; inspect original bytes' spelling.
    name = member.orig_filename
    if (not name or len(name) > 512 or name.startswith('/') or '\\' in name
            or ':' in name or '..' in PurePosixPath(name).parts or name in seen
            or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1):
        raise PackageCheckError('Unerwarteter/verknuepfter/verschluesselter ZIP-Eintrag.')
    seen.add(name)
    return name


def inventory(path):
    """Central directory plus bounded documentation; never deserialize weights."""
    if not 0 < path.stat().st_size <= MAX_ARCHIVE:
        raise PackageCheckError('Modellarchiv fehlt/ist zu gross; Grenze400MiB.')
    entries, documents, seen, expanded, text_bytes = [], [], set(), 0, 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not 0 < len(members) <= 1000:
            raise PackageCheckError('Unerwartete Anzahl ZIP-Eintraege.')
        for member in members:
            name = checked_member_name(member, seen)
            expanded += member.file_size
            if expanded > MAX_EXPANDED:
                raise PackageCheckError('Entpackte Paketgroesse ueber1GiB; keine Verarbeitung.')
            suffix = PurePosixPath(name).suffix.lower()
            entries.append(dict(name=name, bytes=member.file_size,
                                compressed_bytes=member.compress_size,
                                possible_weights=suffix in WEIGHT_SUFFIXES))
            basename = PurePosixPath(name).name.lower()
            if (not member.is_dir() and basename.startswith(('license', 'licence', 'copying', 'readme'))
                    and suffix in {'.txt', '.md', '.rst', ''} and member.file_size <= MAX_TEXT):
                text_bytes += member.file_size
                if text_bytes > 4 * MAX_TEXT:
                    raise PackageCheckError('Zu viele Dokumentationstexte im Modellpaket.')
                with archive.open(member) as stream:
                    content = stream.read(MAX_TEXT + 1)
                if len(content) > MAX_TEXT:
                    raise PackageCheckError('Dokumentation groesser als angekuendigt.')
                documents.append(dict(name=name, text=content.decode('utf-8', errors='replace')))
    return dict(check=CHECK, source_url=URL, archive_bytes=path.stat().st_size,
                archive_sha256=digest(path), checksum_kind='locally_observed_not_publisher_verified',
                entries=entries, documentation=documents,
                status='inventory_only_model_not_loaded', training_started=False,
                inference_started=False, dependencies_installed=False,
                model_license_verified=False, production_approved=False,
                accuracy_verified=False, automatically_accepted=False,
                notice='Datensatz CC BY4.0 laut Anbieterseite; Gewichts-/Code-/Runtime-Rechte separat offen.')


def atomic_json(target, value):
    local(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='cvut-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def package_lock(prefix, lock_name='cvut-package.lock'):
    # OS releases this lock on exit, cancellation and hard kill. The tiny lock
    # file remains so a second process cannot lock an unlinked replacement.
    if Path(lock_name).name != lock_name or not lock_name.endswith('.lock'):
        raise ValueError('Invalid package lock name')
    with local(prefix / lock_name).open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            if stream.tell() == 0:
                stream.write(b'0')
            stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def prepare_intake(prefix, archive_path=None):
    prefix = local(prefix)
    if archive_path is not None:
        archive_path = local(archive_path)
        if archive_path.name != ARCHIVE or not archive_path.is_file():
            raise PackageCheckError('Nur bewusst heruntergeladenes PV_UNET_models.zip auswaehlen.')
    marker = prefix / 'cvut-intake.json'
    local(marker)
    if prefix.exists() and any(prefix.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')) != {'check': CHECK}:
            raise PackageCheckError('Ziel ist kein eigener CVUT-Paketpruefordner; leeren Ordner waehlen.')
    prefix.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        atomic_json(marker, {'check': CHECK})
    return prefix, archive_path


def inspect_package(prefix, archive_path=None):
    prefix, archive_path = prepare_intake(prefix, archive_path)
    with package_lock(prefix):
        return _inspect_locked(prefix, archive_path)


def pickle_layout(data):
    """Lexical disassembly only. No pickle interpreter, imports or constructors."""
    operations, globals_seen, parameters = [], set(), []
    stack_globals, extensions, protocol = 0, 0, None
    for opcode, argument, _position in pickletools.genops(data):
        if len(operations) >= 100000:
            raise PackageCheckError('Zu viele Operationen in den Gewichtsmetadaten.')
        operations.append((opcode.name, argument))
        if opcode.name == 'PROTO':
            protocol = argument
        elif opcode.name == 'GLOBAL':
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]* [A-Za-z_][A-Za-z0-9_]*', argument):
                raise PackageCheckError('Unbekannte Bezeichnerform in den Gewichtsmetadaten.')
            globals_seen.add(argument)
        elif opcode.name == 'STACK_GLOBAL':
            stack_globals += 1
        elif opcode.name in {'EXT1', 'EXT2', 'EXT4'}:
            extensions += 1
        elif opcode.name in {'BINUNICODE', 'SHORT_BINUNICODE', 'UNICODE'}:
            if re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.]{0,240}\.(weight|bias|running_mean|running_var|num_batches_tracked)', argument):
                if argument not in parameters:
                    parameters.append(argument)
                if len(parameters) > 1024:
                    raise PackageCheckError('Zu viele Parameterbezeichner in den Gewichtsmetadaten.')
    if not operations or operations[-1][0] != 'STOP':
        raise PackageCheckError('Unvollstaendige Gewichtsmetadaten.')
    # Hints describe integer tuples after persistent storage references. They
    # do not reconstruct tensors and do not establish a compatible architecture.
    hints, current = [], None
    integer_ops = {'BININT', 'BININT1', 'BININT2', 'LONG', 'LONG1', 'LONG4', 'INT'}
    memo_ops = {'BINPUT', 'LONG_BINPUT', 'MEMOIZE'}
    for i, (name, value) in enumerate(operations):
        if name in {'BINUNICODE', 'SHORT_BINUNICODE', 'UNICODE'} and value in parameters:
            current = value
        if name != 'BINPERSID' or current is None:
            continue
        following = [(op, arg) for op, arg in operations[i+1:i+22] if op not in memo_ops]
        if not following or following[0][0] not in integer_ops:
            continue
        dims = []
        for op, arg in following[1:]:  # first integer is storage offset
            if op == 'MARK' and not dims:
                continue
            if op in integer_ops and type(arg) is int and 0 <= arg <= 1000000000 and len(dims) < 8:
                dims.append(arg)
                continue
            if (op == 'TUPLE' or op == 'EMPTY_TUPLE' and not dims
                    or op in {'TUPLE1', 'TUPLE2', 'TUPLE3'} and len(dims) == int(op[-1])):
                hints.append(dict(parameter=current, shape=dims))
            break
        current = None
    return dict(pickle_protocol=protocol, global_references=sorted(globals_seen),
                stack_global_count=stack_globals, extension_count=extensions,
                parameter_names=parameters, tensor_shape_hints=hints,
                shape_scope='syntactic_hints_not_loaded_tensors')


def inspect_rgb_layout(prefix, archive_path):
    if archive_path is None:
        raise PackageCheckError('RGB-Strukturpruefung erfordert das bewusst gewaehlte lokale --archive.')
    prefix, archive_path = prepare_intake(prefix, archive_path)
    with package_lock(prefix):
        public = inventory(archive_path)
        if (public['archive_bytes'] != CVUT_ARCHIVE['bytes']
                or public['archive_sha256'] != CVUT_ARCHIVE['sha256']):
            raise PackageCheckError('Fuer RGB-Strukturpruefung anderes als das beobachtete oeffentliche CVUT-Paket gewaehlt.')
        model_hash, total = sha256(), 0
        print('Nur oeffentliche RGB-Gewichtsstruktur lesen; kein PyTorch/Modellcode wird gestartet.', flush=True)
        with zipfile.ZipFile(archive_path) as outer, tempfile.TemporaryFile(mode='w+b', dir=prefix) as copy:
            member = outer.getinfo(CVUT_ARCHIVE['rgb_name'])
            if member.file_size != CVUT_ARCHIVE['rgb_bytes']:
                raise PackageCheckError('Unerwartete Groesse der RGB-Gewichtsdatei.')
            with outer.open(member) as stream:
                for block in iter(lambda: stream.read(1024**2), b''):
                    total += len(block)
                    if total > CVUT_ARCHIVE['rgb_bytes']:
                        raise PackageCheckError('RGB-Gewichtsdatei groesser als beobachtet.')
                    model_hash.update(block)
                    copy.write(block)
            if total != CVUT_ARCHIVE['rgb_bytes']:
                raise PackageCheckError('RGB-Gewichtsdatei unvollstaendig.')
            copy.seek(0)
            metadata = {}
            if zipfile.is_zipfile(copy):
                copy.seek(0)
                with zipfile.ZipFile(copy) as inner:
                    members, seen, expanded, metadata_members = inner.infolist(), set(), 0, []
                    if len(members) > 2048:
                        raise PackageCheckError('Zu viele Eintraege im RGB-Gewichtscontainer.')
                    for item in members:
                        name = checked_member_name(item, seen)
                        expanded += item.file_size
                        if expanded > 256 * 1024**2:
                            raise PackageCheckError('RGB-Gewichtscontainer zu gross.')
                        if PurePosixPath(name).name == 'data.pkl':
                            metadata_members.append(item)
                    if len(metadata_members) != 1:
                        raise PackageCheckError('Kein eindeutiger data.pkl-Metadatensatz im RGB-Gewichtscontainer.')
                    item = metadata_members[0]
                    if item.file_size > MAX_PICKLE_METADATA:
                        raise PackageCheckError('Gewichtsmetadaten groesser als2MiB.')
                    with inner.open(item) as stream:
                        data = stream.read(MAX_PICKLE_METADATA + 1)
                    if len(data) > MAX_PICKLE_METADATA:
                        raise PackageCheckError('Gewichtsmetadaten groesser als2MiB.')
                    metadata = pickle_layout(data)
                    metadata.update(format='pytorch_zip_metadata_only', container_entries=len(members))
            else:
                metadata = dict(format='legacy_or_unknown_not_loaded')
        if digest(archive_path) != public['archive_sha256']:
            raise PackageCheckError('Oeffentliches Quellarchiv waehrend der Strukturpruefung geaendert.')
        record = dict(check='solarcheck-cvut-rgb-layout-1', source_url=URL,
                      archive_bytes=public['archive_bytes'], archive_sha256=public['archive_sha256'],
                      checksum_kind=public['checksum_kind'], selected_model=CVUT_ARCHIVE['rgb_name'],
                      model_bytes=total, model_sha256=model_hash.hexdigest(), metadata=metadata,
                      status='metadata_only_architecture_not_verified', model_loaded=False,
                      training_started=False, inference_started=False, dependencies_installed=False,
                      model_license_verified=False, production_approved=False)
        atomic_json(prefix / RGB_REPORT, record)
        return record


def _inspect_locked(prefix, archive_path):
    target, report = local(prefix / ARCHIVE), local(prefix / REPORT)
    temporary = local(prefix / (ARCHIVE + '.download'))
    # A hard-killed download is deliberately restarted; never trust a partial ZIP.
    if temporary.exists():
        temporary.unlink()
    previous = json.loads(report.read_text(encoding='utf-8')) if report.exists() else None
    if archive_path is None and target.exists():
        archive_path = target
    if archive_path is not None:
        record = inventory(archive_path)
    else:
        print('Oeffentliches CVUT-U-Net-Modellpaket laden (ca.344MB), keine Bilder/Pakete installieren.', flush=True)
        try:
            with urllib.request.urlopen(URL, timeout=30) as response, temporary.open('xb') as output:
                if response.status != 200 or response.geturl() != URL:
                    raise PackageCheckError('Unerwartete Downloadantwort; keine fremde Quelle verwenden.')
                total = 0
                while True:
                    block = response.read(1024**2)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_ARCHIVE:
                        raise PackageCheckError('Download groesser als400MiB.')
                    output.write(block)
                    if total % (16 * 1024**2) < len(block):
                        print('Modellpaket geladen: ' + str(total // 1024**2) + 'MiB', flush=True)
            record = inventory(temporary)
            if previous is not None and previous.get('archive_sha256') != record['archive_sha256']:
                raise PackageCheckError('Paket unterscheidet sich vom gespeicherten Stand; nicht uebernommen.')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    if previous is not None and previous.get('archive_sha256') != record['archive_sha256']:
        raise PackageCheckError('Paket unterscheidet sich vom gespeicherten Stand; Bericht erhalten.')
    atomic_json(report, record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-CVUT-Paketpruefung')
    parser.add_argument('--archive', help='Optional: manuell geladenes oeffentliches PV_UNET_models.zip')
    parser.add_argument('--inspect-rgb-layout', action='store_true',
                        help='Nur Metadaten der RGB-Modulgewichte im lokalen oeffentlichen ZIP lesen; keine Modellausfuehrung')
    args = parser.parse_args(argv)
    try:
        if args.inspect_rgb_layout:
            record = inspect_rgb_layout(args.prefix, args.archive)
            print(json.dumps(record, ensure_ascii=True, indent=2))
            print('RGB-Struktur gespeichert. Noch keine bestaetigte Architektur oder Modellaktivierung.')
            return 0
        record = inspect_package(args.prefix, args.archive)
        # Public package metadata only; no local path, documentation text or customer input.
        print(json.dumps({k: record[k] for k in (
            'check', 'source_url', 'archive_bytes', 'archive_sha256', 'checksum_kind',
            'entries', 'status', 'training_started', 'inference_started',
            'model_license_verified', 'production_approved')}, ensure_ascii=True, indent=2))
        print('Paketliste gespeichert. Noch kein KI-Ergebnis; nichts als Modellmanifest im Vergleich auswaehlen.')
        return 0
    except KeyboardInterrupt:
        print('Paketpruefung abgebrochen. Erneuter Start verwendet ein fertig geprueftes Paket.')
        return 130
    except Exception as error:
        print('CVUT-Paketpruefung nicht abgeschlossen. Diagnose (ohne lokale Pfade):')
        print(json.dumps(failure_details(error), ensure_ascii=True, indent=2))
        print('Kein Modell ausgefuehrt. Bitte nur diesen Diagnoseblock als Text mitteilen.')
        return 2


if __name__ == '__main__':
    sys.exit(main())
