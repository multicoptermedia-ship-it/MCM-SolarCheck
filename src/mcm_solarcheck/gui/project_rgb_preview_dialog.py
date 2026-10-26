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
