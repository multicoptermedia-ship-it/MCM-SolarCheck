"""Explicit local evaluation worker. No install/download/training or stdout data."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def prepare_runtime():
    # Python 3.10 is needed only for the isolated TF pilot. Keep the existing
    # application/OpenSfM environments and shared services unchanged.
    import os
    import hashlib
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['TF_NUM_INTRAOP_THREADS'] = '2'
    os.environ['TF_NUM_INTEROP_THREADS'] = '2'
    if not hasattr(hashlib, 'file_digest'):
        def file_digest(stream, algorithm):
            digest = hashlib.new(algorithm)
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
            return digest
        hashlib.file_digest = file_digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--run-token')
    args = parser.parse_args(argv)
    try:
        prepare_runtime()
        from mcm_solarcheck.services.thermal_partial_model_comparison import compare_saved_region
        compare_saved_region(args.source, args.manifest, args.region, run_token=args.run_token)
        return 0
    except Exception:
        # Local paths, model parser diagnostics and private notes stay private.
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
