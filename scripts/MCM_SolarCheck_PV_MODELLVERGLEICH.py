"""Explicit local evaluation worker. No install/download/training or stdout data."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--run-token')
    args = parser.parse_args(argv)
    try:
        from mcm_solarcheck.services.thermal_partial_model_comparison import compare_saved_region
        compare_saved_region(args.source, args.manifest, args.region, run_token=args.run_token)
        return 0
    except Exception:
        # Local paths, model parser diagnostics and private notes stay private.
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
