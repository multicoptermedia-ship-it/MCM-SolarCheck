"""Explicit isolated CPU candidate setup/probe. Public weights, synthetic probe only."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

from MCM_SolarCheck_CVUT_PAKETPRUEFUNG import local, digest, atomic_json, package_lock, failure_details, PackageCheckError
from MCM_SolarCheck_PV_HAWK_SETUP import download

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / 'config/cvut/rgb-candidate-v1.json'
MARKER = 'solarcheck-cvut-cpu-candidate-1'
MANIFEST = 'cvut-rgb.LOCAL.json'
PROBE_MANIFEST = 'cvut-rgb-probe.LOCAL.json'
PROBE_REPORT = 'cvut-cpu-probe.LOCAL.json'


def extract_rgb(archive, prefix, spec):
    archive = local(archive)
    if (archive.stat().st_size != spec['archive_bytes'] or digest(archive) != spec['archive_sha256']):
        raise PackageCheckError('Das beobachtete oeffentliche CVUT-ZIP erforderlich; Originale erhalten.')
    target = local(prefix / spec['weights'])
    if target.exists():
        if target.stat().st_size == spec['weights_bytes'] and digest(target) == spec['weights_sha256']:
            return
        raise PackageCheckError('Vorhandene RGB-Gewichte abweichend; nicht ueberschrieben.')
    temporary = local(prefix / (spec['weights'] + '.download'))
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(archive) as source, source.open(spec['weights']) as stream, temporary.open('xb') as output:
            total, checksum = 0, sha256()
            for block in iter(lambda: stream.read(1024**2), b''):
                total += len(block)
                if total > spec['weights_bytes']:
                    raise PackageCheckError('RGB-Gewichte groesser als beobachtet.')
                checksum.update(block)
                output.write(block)
        if total != spec['weights_bytes'] or checksum.hexdigest() != spec['weights_sha256']:
            raise PackageCheckError('RGB-Gewichtspruefsumme stimmt nicht.')
        if digest(archive) != spec['archive_sha256']:
            raise PackageCheckError('Oeffentliches Quellarchiv waehrend Kopie geaendert.')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def setup(prefix, archive):
    prefix = local(prefix)
    if sys.version_info[:2] not in {(3, 11), (3, 12)} or struct.calcsize('P') != 8:
        raise PackageCheckError('Vorhandenes App-Python3.11/3.12 x64 verwenden, nicht OpenSfM-Python3.10.')
    marker = local(prefix / 'cvut-cpu-pilot.json')
    if prefix.exists() and any(prefix.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text()) != {'check': MARKER}:
            raise PackageCheckError('Eigenen leeren CVUT-CPU-Pilotordner verwenden.')
    prefix.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        atomic_json(marker, {'check': MARKER})
    with package_lock(prefix):
        spec = json.loads(SPEC.read_text())
        if shutil.disk_usage(prefix).free < 4 * 1024**3:
            raise PackageCheckError('Fuer eigene CPU-Umgebung/Cache mindestens4GiB freien Platz vorsehen.')
        print('1/5: Oeffentliche RGB-Gewichte lokal kopieren und SHA pruefen; Original-ZIP bleibt erhalten.', flush=True)
        extract_rgb(archive, prefix, spec)
        for folder in ('cache', 'tmp'):
            local(prefix / folder).mkdir(exist_ok=True)
        environment = dict(os.environ, TMP=str(prefix/'tmp'), TEMP=str(prefix/'tmp'),
                           PIP_CACHE_DIR=str(prefix/'cache'), PYTHONNOUSERSITE='1',
                           PIP_DISABLE_PIP_VERSION_CHECK='1', OMP_NUM_THREADS='2')
        environment.pop('PYTHONPATH', None)
        local(prefix / 'env')
        python = prefix / ('env/Scripts/python.exe' if os.name == 'nt' else 'env/bin/python')
        print('2/5: Eigene Umgebung; vorhandenes App-/OpenSfM-/PV-Hawk-Python unveraendert.', flush=True)
        if not python.is_file():
            subprocess.run([sys.executable, '-m', 'venv', str(prefix/'env')], env=environment, check=True, timeout=120)
        print('3/5: PyTorch2.15.0 CPU und eigene Pakete installieren; kein CUDA/Compiler/TorchVision.', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--only-binary=:all:', 'torch==2.15.0',
                        '--index-url', 'https://download.pytorch.org/whl/cpu'],
                       env=environment, check=True, timeout=1200)
        subprocess.run([str(python), '-m', 'pip', 'install', '--only-binary=:all:',
                        '-r', str(REPO/'requirements-cvut-cpu.txt')], env=environment, check=True, timeout=900)
        print('4/5: Externe GPL-3.0-Referenz samt Lizenz fest pruefen; nur lokaler Versuch, kein Produktpaket.', flush=True)
        for name, check in spec['sources'].items():
            download(spec['source_url'] + spec['source_commit'] + '/' + name, prefix/'vendor'/name, check)
        candidate = dict(profile=spec['profile'], source_commit=spec['source_commit'],
                         weights_sha256=spec['weights_sha256'], evaluation_allowed=True,
                         production_approved=False,
                         notice='GPL-3.0 reference / experimental CVUT candidate; input/class mapping and production rights unverified.')
        staged = local(prefix / PROBE_MANIFEST)
        atomic_json(staged, candidate)
        try:
            print('5/5: Eingeschraenkt Gewichte laden, alle118Schichten pruefen, schwarzes RGB-Testbild rechnen.', flush=True)
            result = subprocess.run([str(python), str(Path(__file__).resolve()), '--probe', '--prefix', str(prefix)],
                                    env=environment, capture_output=True, timeout=300)
            if result.returncode:
                raise PackageCheckError('CPU-Probe nicht bestanden; kein neues Modellmanifest uebernommen.')
            final = local(prefix / MANIFEST)
            staged.replace(final)
        finally:
            staged.unlink(missing_ok=True)
        (prefix/'runtime-packages.LOCAL.txt').write_bytes(subprocess.check_output(
            [str(python), '-m', 'pip', 'freeze'], env=environment, timeout=30))
        print(result.stdout.decode('utf-8').strip(), flush=True)
        print('CPU-Kandidat bereit. Noch kein Anlagenbild verarbeitet oder Modell nachtrainiert.', flush=True)
        print('Fuer den begrenzten lokalen Vergleich: gespeicherten PV-Ausschnitt oeffnen und cvut-rgb.LOCAL.json waehlen.', flush=True)


def probe(prefix):
    prefix = local(prefix)
    sys.path.insert(0, str(REPO/'src'))
    import numpy as np
    from mcm_solarcheck.vision.cvut_module_detector import CVUTModuleDetector
    path = prefix / PROBE_MANIFEST
    if not path.exists():
        path = prefix / MANIFEST
    detector = CVUTModuleDetector(path)
    probabilities = detector.probabilities(np.zeros((270,480,3), np.uint8))
    record = dict(check='solarcheck-cvut-cpu-probe-1', status='passed', synthetic_only=True,
                  pretrained_weights_loaded=True, state_entries=len(detector.spec['state_shapes']),
                  output_classes=2, foreground_pixels_at_080=int((probabilities >= .8).sum()),
                  torch_version=detector.torch.__version__, source_commit=detector.spec['source_commit'],
                  weights_sha256=detector.spec['weights_sha256'], preprocessing_verified=False,
                  class_mapping_verified=False, accuracy_verified=False, production_approved=False,
                  coverage_verified=False, georeferencing_verified=False, temperature_verified=False)
    atomic_json(prefix / PROBE_REPORT, record)
    print(json.dumps(record, indent=2), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-CVUT-KI-Pilot')
    parser.add_argument('--archive', help='Bereits geladenes oeffentliches CVUT-ZIP')
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.probe:
            probe(args.prefix)
        elif args.archive:
            setup(args.prefix, args.archive)
        else:
            raise PackageCheckError('Vorhandenes oeffentliches ZIP bewusst mit --archive waehlen.')
        return 0
    except KeyboardInterrupt:
        print('CVUT-CPU-Einrichtung/Probe abgebrochen. Denselben Start erneut verwenden.')
        return 130
    except Exception as error:
        print(json.dumps(failure_details(error), ensure_ascii=True, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
