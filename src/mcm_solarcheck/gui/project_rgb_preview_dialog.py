"""Local, explicitly unverified RGB PNG preview; no sensitive file paths in UI."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QScrollArea, QVBoxLayout


class ProjectRGBPreviewDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent)
        if result.metric_orthophoto_verified is not False:
            raise ValueError("unverified preview required")
        image = QPixmap(str(result.png_path))
        if image.isNull():
            raise ValueError("preview PNG cannot be decoded")
        self.setWindowTitle("RGB-Projektvorschau – nicht metrisch")
        self.setObjectName("project_rgb_preview_dialog")
        self.resize(960, 700)
        layout = QVBoxLayout(self)
        info = QLabel(
            f"RGB {result.first_sequence} + {result.second_sequence} · "
            f"{result.inliers} RANSAC-Inlier · "
            f"{result.canvas_covered_fraction:.1%} Vorschaufläche belegt.\n"
            "Nichtmetrische Bildvorschau, keine Dachflächenvermessung, "
            "keine bestätigten Module oder Befunde. "
            "Gekippte Dachflächen nicht orthorektifiziert.",
            self,
        )
        info.setObjectName("project_rgb_preview_warning")
        info.setTextFormat(Qt.TextFormat.PlainText)
        info.setWordWrap(True)
        layout.addWidget(info)

        # A high RANSAC count and canvas coverage do not validate a hard
        # compositing seam. The warning is intentionally ALWAYS visible.
        if result.seam_p90_rgb_difference is None:
            seam_detail = (
                "Kein auswertbarer Naht-Pixelvergleich; die lokale "
                "Bildausrichtung bleibt ungeprüft."
            )
        else:
            seam_detail = (
                f"Nahtdiagnose: 90 %-Quantil der lokalen RGB-Abweichung "
                f"{result.seam_p90_rgb_difference:.1f}/255 "
                f"aus {result.seam_pixel_samples} Vergleichspixeln. "
                "Beleuchtung und Parallaxe beeinflussen diesen Wert."
            )
        seam_notice = QLabel(
            "ACHTUNG BILDNAHT: Das erste Bild überdeckt das zweite "
            "im Überlappungsbereich mit einer harten Kante. "
            "Sichtbare Versätze sind nicht korrigiert und erfordern Prüfung. "
            + seam_detail,
            self,
        )
        seam_notice.setObjectName("project_rgb_preview_seam_notice")
        seam_notice.setTextFormat(Qt.TextFormat.PlainText)
        seam_notice.setWordWrap(True)
        layout.addWidget(seam_notice)

        image_label = QLabel(self)
        image_label.setObjectName("project_rgb_preview_image")
        image_label.setPixmap(image)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea(self)
        scroll.setObjectName("project_rgb_preview_scroll")
        scroll.setWidget(image_label)
        scroll.setWidgetResizable(False)
        layout.addWidget(scroll)

        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
