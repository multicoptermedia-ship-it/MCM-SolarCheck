"""Explicit generated-data training probe in the existing isolated Torch runtime."""
import argparse
import errno
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-CVUT-KI-Pilot')
    parser.add_argument('--show', action='store_true', help='Letzte abgeschlossene Probe nur lesen/pruefen')
    args = parser.parse_args(argv)
    try:
        from mcm_solarcheck.services.pv_synthetic_training import read_probe, run_probe
        report = read_probe(args.prefix) if args.show else run_probe(args.prefix)
        print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
        return 0
    except KeyboardInterrupt:
        print(json.dumps(dict(check='solarcheck-pv-synthetic-training-failure-1',
            status='cancelled', customer_training_started=False, production_approved=False)))
        return 130
    except Exception as error:
        # Never include raw exception strings/paths from the local runtime.
        if isinstance(error, ImportError):
            code, message = 'CPU_RUNTIME_MISSING', 'Vorhandenes Python der getrennten CVUT-Torch-CPU-Umgebung verwenden.'
        elif isinstance(error, FileNotFoundError):
            code, message = 'REFERENCE_OR_REPORT_MISSING', 'Referenzordner oder abgeschlossene Probe fehlt; vorhandenen CVUT-Pilotordner pruefen.'
        elif isinstance(error, OSError) and error.errno == errno.ENOSPC:
            code, message = 'OUTPUT_FULL', 'Die neue Probe konnte nicht vollstaendig geschrieben werden; bisherige Proben bleiben erhalten.'
        elif isinstance(error, ValueError):
            code, message = 'VERIFICATION_FAILED', 'Torch-Version, fest gepruefte Referenz oder synthetisches Artefakt stimmen nicht; keine Modellfreigabe.'
        else:
            code, message = 'RUNTIME_FAILURE', 'Synthetische Probe fehlgeschlagen; nur diesen Diagnoseblock mitteilen, keine lokalen Bilder oder Pfade.'
        print(json.dumps(dict(check='solarcheck-pv-synthetic-training-failure-1',
            status='failed', error_code=code, exception_type=type(error).__name__, customer_training_started=False,
            production_approved=False, message=message)))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
