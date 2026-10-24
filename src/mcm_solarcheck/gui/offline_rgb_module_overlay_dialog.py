"""Memory-only RGB overlay dialog with clear unverified-proposal legend."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from mcm_solarcheck.gui.offline_cadence_diagnostic_text import CADENCE_REASON_DE


class RgbModuleOverlayDialog(QDialog):
    def __init__(self, overlay, parent=None):
        super().__init__(parent)
        if (
            type(overlay.png) is not bytes
            or not overlay.png.startswith(b"\x89PNG\r\n\x1a\n")
            or not 0 < len(overlay.png) <= 8_000_000
        ):
            raise ValueError("bounded in-memory PNG required")
        self.setObjectName("rgb_module_overlay_dialog")
        self.setWindowTitle("RGB-Modulraster – technische Vorschau")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(1020, 760)

        layout = QVBoxLayout(self)
        heading = QLabel(
            f"RGB-Testbild {overlay.sample_index + 1} von {overlay.total} "
            "– unverbindliche Modulvorschläge (nur lesend)",
            self,
        )
        heading.setObjectName("rgb_module_overlay_heading")
        heading.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(heading)

        guide = QLabel(
            "Gelb: Strukturvorschläge · Magenta: Bildinhalt-Vorschläge · "
            "Türkis: räumlich gestützte Vorschläge · "
            "Grün: Cadence-Rastervorschläge. "
            "Farben bedeuten keine Bestätigung eines PV-Moduls.",
            self,
        )
        guide.setObjectName("rgb_module_overlay_legend")
        guide.setWordWrap(True)
        guide.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(guide)

        preview = QScrollArea(self)
        preview.setObjectName("rgb_module_overlay_scroll")
        preview.setWidgetResizable(False)
        preview.setFrameShape(QFrame.Shape.NoFrame)
        self.image_label = QLabel(preview)
        self.image_label.setObjectName("rgb_module_overlay_image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap()
        if not pixmap.loadFromData(overlay.png, "PNG"):
            raise ValueError("could not decode RGB overlay PNG")
        if max(pixmap.width(), pixmap.height()) > 960:
            raise ValueError("preview exceeds size bound")
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        preview.setWidget(self.image_label)
        layout.addWidget(preview, 1)

        reason = CADENCE_REASON_DE.get(
            overlay.cadence_reason, "weitere, nicht näher klassifizierte Qualitätsprüfung",
        ) if overlay.cadence == 0 else "nicht als bestätigte PV-Module bewertbar"
        result = QLabel(
            f"{overlay.structural} Strukturvorschläge, "
            f"{overlay.visual} Bildinhalt-Vorschläge, "
            f"{overlay.overlapping} räumlich gestützte Vorschläge, "
            f"{overlay.cadence} Cadence-Vorschläge. "
            f"Cadence-Diagnose: {reason}.",
            self,
        )
        result.setObjectName("rgb_module_overlay_counts")
        result.setWordWrap(True)
        result.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(result)

        warning = QLabel(
            "Reine lokale Diagnose auf Basis einer geprüften Bilddatei. "
            "Keine bestätigte Modulgeometrie, keine Temperaturbewertung, "
            "keine Fachfreigabe, kein Speichern oder Exportieren.",
            self,
        )
        warning.setObjectName("rgb_module_overlay_warning")
        warning.setTextFormat(Qt.TextFormat.PlainText)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        close = QPushButton("Vorschau schließen", self)
        close.setObjectName("rgb_module_overlay_close")
        close.clicked.connect(self.close)
        layout.addWidget(close)
