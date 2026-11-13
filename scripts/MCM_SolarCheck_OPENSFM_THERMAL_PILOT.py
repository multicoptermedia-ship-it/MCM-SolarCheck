"""Separate Thermal entry point, sharing the qualified OpenSfM launcher/core."""
from MCM_SolarCheck_OPENSFM_RGB_PILOT import main

if __name__ == '__main__':
    raise SystemExit(main(modality='thermal'))
