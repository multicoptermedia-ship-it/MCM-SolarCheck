"""Bounded, read-only Qt PDF preview with conservative end-of-scroll detection.

Only an actual open, loaded multi-page document with a scrollable viewport can
produce the end event; no inference is made about understanding or reading.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QTimer, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class ReportPdfPreviewDialog(QDialog):
    def __init__(self, document_bytes: bytes, parent=None):
        super().__init__(parent)
        if not isinstance(document_bytes, bytes) or not document_bytes.startswith(b"%PDF"):
            raise ValueError("a rendered report PDF is required")
        if len(document_bytes) > 32 * 1024 * 1024:
            raise ValueError("report preview exceeds memory limit")
        self.setWindowTitle("Berichtsentwurf ansehen")
        self.resize(900, 760)
        self.reached_end = False
        self._armed = False
        layout = QVBoxLayout(self)
        notice = QLabel(
            "Lokale Vorschau des vorbereiteten Berichtsentwurfs. "
            "Das Erreichen des unteren Scrollbereichs wird für das "
            "interne Freigabeprotokoll erfasst; es beweist kein tatsächliches Lesen. "
            "Sie können den Dialog jederzeit schließen.",
            self,
        )
        notice.setTextFormat(Qt.TextFormat.PlainText)
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setObjectName("report_pdf_view")
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(self.pdf_view)
        close = QPushButton("Vorschau schließen", self)
        close.clicked.connect(self.accept)
        layout.addWidget(close)

        self._pdf_buffer = QBuffer(self)
        self._pdf_buffer.setData(QByteArray(document_bytes))
        if not self._pdf_buffer.open(QIODevice.OpenModeFlag.ReadOnly):
            raise ValueError("cannot load preview bytes")
        self._document = QPdfDocument(self)
        self._document.load(self._pdf_buffer)
        self._document.statusChanged.connect(
            lambda *_: QTimer.singleShot(0, self._arm_after_layout)
        )
        self.pdf_view.setDocument(self._document)
        self.pdf_view.verticalScrollBar().valueChanged.connect(self._track_end)
        QTimer.singleShot(0, self._arm_after_layout)

    def _arm_after_layout(self):
        self._armed = self.isVisible() and self._document.pageCount() > 0

    def _track_end(self, value: int):
        bar = self.pdf_view.verticalScrollBar()
        if (
            self._armed and self.isVisible() and self._document.pageCount() > 0
            and bar.maximum() > 0 and value == bar.maximum()
        ):
            self.reached_end = True
