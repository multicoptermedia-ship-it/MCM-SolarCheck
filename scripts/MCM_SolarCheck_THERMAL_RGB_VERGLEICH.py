"""Local-only comparison of the saved incomplete Thermal preview and existing RGB."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--choose-rgb', action='store_true')
    args = parser.parse_args(argv)
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from mcm_solarcheck.services.opensfm_thermal_partial import read_partial_preview
    from mcm_solarcheck.services.thermal_partial_comparison import STATE, open_partial_comparison
    from mcm_solarcheck.gui.thermal_partial_comparison import PartialThermalComparisonWindow
    app = QApplication.instance() or QApplication([])
    try:
        loaded = read_partial_preview(args.source)
        if not loaded or loaded[1]['status'] != 'finished':
            raise ValueError('Fertige unvollstaendige Thermal-Teilvorschau laden.')
        rgb = None
        if args.choose_rgb or not (loaded[0] / STATE).exists():
            rgb, _ = QFileDialog.getOpenFileName(None, 'Fertiges RGB-GeoTIFF desselben Projekts wählen',
                                                '', 'GeoTIFF (*.tif *.tiff)')
            if not rgb:
                return 0
        comparison = open_partial_comparison(args.source, rgb)
    except Exception:
        QMessageBox.warning(None, 'Vergleich nicht geöffnet',
            'Keine fertige passende Teilvorschau oder RGB-Datei; gespeicherte Dateien können verändert sein. '
            'Vorhandenes RGB erneut bewusst auswählen. Keine Neuberechnung oder Freigabe erfolgt.')
        return 2
    window = PartialThermalComparisonWindow(comparison)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
