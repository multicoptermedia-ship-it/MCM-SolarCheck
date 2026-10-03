"""Compatibility entry point for the SolarCheck Offline Desktop product.

The executable composition lives in :mod:`mcm_solarcheck.offline.entrypoint`.
Keeping this root module thin prevents a second, divergent project/import/report
workflow from bypassing the persisted application services.
"""

from mcm_solarcheck.offline.entrypoint import main


if __name__ == "__main__":
    raise SystemExit(main())
