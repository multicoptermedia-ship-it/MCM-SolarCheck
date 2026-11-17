"""Explicitly invoked isolated PV-Hawk CPU setup/probe; no customer data access."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO/'config/pv-hawk/rgb-v1.json'
MARKER = 'solarcheck-pv-hawk-cpu-pilot-1'


def download(url, target, check):
    if any(p.is_symlink() for p in (target,*target.parents)):
        raise ValueError('Verknuepfung im Downloadziel abgelehnt.')
    if target.is_file() and sha256(target.read_bytes()).hexdigest() == check['sha256'] and target.stat().st_size == check['bytes']:
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary = target.with_suffix(target.suffix+'.download')
    if target.is_symlink() or temporary.is_symlink():
        raise ValueError('Verknuepfung als Downloadziel abgelehnt.')
    try:
        with urllib.request.urlopen(url,timeout=60) as response, temporary.open('wb') as output:
            total = 0
            while True:
                block=response.read(1024*1024)
                if not block: break
                total += len(block)
                if total > check['bytes']: raise ValueError('Download groesser als festgelegtes Artefakt.')
                output.write(block)
        if total != check['bytes'] or sha256(temporary.read_bytes()).hexdigest() != check['sha256']:
            raise ValueError('Downloadpruefsumme stimmt nicht; erneut starten.')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def setup(prefix, base_python):
    prefix, base_python = Path(prefix), Path(base_python)
    if (not prefix.is_absolute() or any(p.is_symlink() for p in (prefix,*prefix.parents))
            or any((p/'.git/HEAD').exists() for p in (prefix,*prefix.parents))):
        raise ValueError('Eigenen privaten absoluten Pilotordner ohne Verknuepfung verwenden.')
    marker = prefix/'pilot.json'
    if prefix.exists() and any(prefix.iterdir()):
        if not marker.is_file() or json.loads(marker.read_text()) != {'check':MARKER}:
            raise ValueError('Zielordner ist nicht leer und kein eigener PV-Hawk-Pilot.')
    info = subprocess.check_output([str(base_python),'-c','import sys,struct;print(sys.version_info.major,sys.version_info.minor,struct.calcsize("P")*8)'],text=True,timeout=20).strip()
    if info != '3 10 64': raise ValueError('Vorhandenes Python3.10-x64 als Basis benoetigt.')
    prefix.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps({'check':MARKER}))
    if shutil.disk_usage(prefix).free < 2*1024**3:
        raise ValueError('Mindestens2GiB freier Platz im Pilotlaufwerk erforderlich.')
    for directory in ('cache','tmp'): (prefix/directory).mkdir(exist_ok=True)
    environment = dict(os.environ,TMP=str(prefix/'tmp'),TEMP=str(prefix/'tmp'),
        PIP_CACHE_DIR=str(prefix/'cache'),PYTHONNOUSERSITE='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
    environment.pop('PYTHONPATH',None)
    python = prefix/('env/Scripts/python.exe' if os.name=='nt' else 'env/bin/python')
    print('1/4: Eigene Python-Umgebung einrichten.',flush=True)
    if not python.is_file():
        subprocess.run([str(base_python),'-m','venv',str(prefix/'env')],env=environment,check=True,timeout=120)
    print('2/4: CPU-Pakete aus PyPI installieren; kein Compiler-/CUDA-Setup.',flush=True)
    subprocess.run([str(python),'-m','pip','install','--only-binary=:all:','-r',str(REPO/'requirements-pv-hawk-cpu.txt')],env=environment,check=True,timeout=1200)
    spec=json.loads(SPEC.read_text())
    print('3/4: Originalcode und RGB-Modell laden und SHA-256 pruefen (Modell244MiB).',flush=True)
    for name,check in spec['sources'].items():
        download(spec['source_url']+spec['source_commit']+'/'+name,prefix/'vendor'/name,check)
    download(spec['weights_url'],prefix/spec['weights'],dict(bytes=spec['weights_bytes'],sha256=spec['weights_sha256']))
    manifest = prefix/'pv-hawk-rgb.LOCAL.json'
    record=dict(profile=spec['profile'],source_commit=spec['source_commit'],weights_sha256=spec['weights_sha256'],
        evaluation_allowed=True,production_approved=False,
        notice='Nur freigegebener technischer Pilot. Code MIT; separate Gewichts-/Datenrechte nicht fuer Produktion/Weitergabe geklaert.')
    manifest.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('4/4: Echte RGB-Gewichte laden und synthetische CPU-Probe rechnen.',flush=True)
    result=subprocess.run([str(python),str(Path(__file__).resolve()),'--probe','--prefix',str(prefix)],
        env=environment,capture_output=True,timeout=300)
    if result.returncode:
        raise RuntimeError('CPU-Modellprobe fehlgeschlagen; Kennzahlenprobe nicht bestanden. Keine Kundendaten verarbeitet.')
    (prefix/'runtime-packages.LOCAL.txt').write_bytes(subprocess.check_output([str(python),'-m','pip','freeze'],env=environment,timeout=30))
    print(result.stdout.decode('utf-8').strip(),flush=True)
    print('Fertig. Im gespeicherten PV-Ausschnitt KI-Modellvergleich starten und pv-hawk-rgb.LOCAL.json im Pilotordner waehlen.',flush=True)


def probe(prefix):
    sys.path.insert(0,str(REPO/'src'))
    from MCM_SolarCheck_PV_MODELLVERGLEICH import prepare_runtime
    prepare_runtime()
    import time
    import numpy as np
    from mcm_solarcheck.vision.pv_hawk_module_detector import PVHawkModuleDetector
    started=time.monotonic()
    detector=PVHawkModuleDetector(Path(prefix)/'pv-hawk-rgb.LOCAL.json')
    found=detector.detect_array(np.zeros((512,640,3),np.uint8))
    record=dict(status='passed',probe='synthetic-black-RGB-512x640',
        pretrained_rgb_weights_loaded=True,candidate_count=len(found),
        elapsed_seconds=round(time.monotonic()-started,3),
        production_approved=False,accuracy_verified=False,windows10_field_acceptance=False)
    (Path(prefix)/'cpu-probe.LOCAL.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',default=r'E:\SolarCheck-PV-KI-Pilot')
    parser.add_argument('--base-python',default=r'E:\SolarCheck-OpenSfM\env\python.exe')
    parser.add_argument('--probe',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.probe: probe(args.prefix)
        else: setup(args.prefix,args.base_python)
        return 0
    except KeyboardInterrupt:
        print('Einrichtung abgebrochen. Erneuter Start verwendet bereits gepruefte Downloads.',flush=True)
        return 130
    except Exception as error:
        # Setup handles public artifacts only; no source job or private imagery.
        print('PV-Hawk-Einrichtung/Probe nicht abgeschlossen: '+str(error) if not args.probe else 'CPU-Probe fehlgeschlagen.',flush=True)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
