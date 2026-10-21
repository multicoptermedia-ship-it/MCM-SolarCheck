"""Run the existing offline desktop product, never the online customer shell."""
from __future__ import annotations

from mcm_solarcheck.offline.entrypoint import main


if __name__ == "__main__":
    raise SystemExit(main())
