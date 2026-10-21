"""Credential-gated, read-only local administrator audit dialog.

The audit never enters ordinary report/review pages or customer-facing output.
Authentication and database permissions are validated by the service, not Qt.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from mcm_solarcheck.services.offline_admin_audit_sessions import OfflineAdminAuditSessions


class OfflineAdminAuditDialog(QDialog):
    PAGE_SIZE = 25

    def __init__(
        self, sessions: OfflineAdminAuditSessions, project_id: str,
        *, active_project: Callable[[], str | None], parent=None,
    ) -> None:
        super().__init__(parent)
        if not isinstance(sessions, OfflineAdminAuditSessions):
            raise TypeError("offline admin session controller required")
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("selected inspection project required")
        if not callable(active_project):
            raise TypeError("active project provider required")
        self._sessions = sessions
        self._project_id = project_id
        self._active_project = active_project
        self._token: str | None = None
        self._offset = 0
        self.setObjectName("offline_admin_audit_dialog")
        self.setWindowTitle("Administration – vertrauliches Berichtsprotokoll")
        self.resize(820, 525)
        layout = QVBoxLayout(self)
        self.status = QLabel(
            "Separate lokale Administratoranmeldung erforderlich. "
            "Ohne eingerichtete Zugangsdaten kein Zugriff.",
            self,
        )
        self.status.setObjectName("admin_audit_status")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)
        login_page = QWidget(self)
        login_layout = QVBoxLayout(login_page)
        form = QFormLayout()
        self.user = QLineEdit(login_page)
        self.user.setObjectName("admin_audit_user")
        self.password = QLineEdit(login_page)
        self.password.setObjectName("admin_audit_password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Administrator-ID", self.user)
        form.addRow("Passwort", self.password)
        login_layout.addLayout(form)
        self.login_button = QPushButton("Administrator anmelden", login_page)
        self.login_button.setObjectName("admin_audit_login")
        self.login_button.clicked.connect(self._login)
        login_layout.addWidget(self.login_button)
        login_layout.addStretch()
        self.stack.addWidget(login_page)

        history = QWidget(self)
        history_layout = QVBoxLayout(history)
        explanation = QLabel(
            "Nur internes Administratorprotokoll. „Ende erreicht“ beschreibt "
            "ein Scroll-Ereignis – kein nachgewiesenes Lesen. "
            "Alte Freigaben ohne Ereignisdatensatz: unbekannt.",
            history,
        )
        explanation.setTextFormat(Qt.TextFormat.PlainText)
        explanation.setWordWrap(True)
        history_layout.addWidget(explanation)
        self.table = QTableWidget(0, 5, history)
        self.table.setObjectName("admin_report_audit_table")
        self.table.setHorizontalHeaderLabels(
            ["Freigabe-ID", "Bericht-ID", "Freigegeben von", "Zeitpunkt (UTC)", "PDF-Ende"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        history_layout.addWidget(self.table)
        navigation = QHBoxLayout()
        self.previous = QPushButton("Zurück", history)
        self.previous.setObjectName("admin_audit_previous")
        self.next = QPushButton("Weitere", history)
        self.next.setObjectName("admin_audit_next")
        self.reload = QPushButton("Aktualisieren", history)
        self.reload.setObjectName("admin_audit_refresh")
        self.logout_button = QPushButton("Abmelden", history)
        self.logout_button.setObjectName("admin_audit_logout")
        self.previous.clicked.connect(lambda: self._load(max(0, self._offset-self.PAGE_SIZE)))
        self.next.clicked.connect(lambda: self._load(self._offset+self.PAGE_SIZE))
        self.reload.clicked.connect(lambda: self._load(self._offset))
        self.logout_button.clicked.connect(self._logout)
        for button in (self.previous, self.next, self.reload, self.logout_button):
            navigation.addWidget(button)
        history_layout.addLayout(navigation)
        self.stack.addWidget(history)

    def _project_current(self) -> bool:
        return self._active_project() == self._project_id

    def _login(self) -> None:
        if not self._project_current():
            self.status.setText("Projekt gewechselt: Administrationsdialog schließen.")
            self.reject()
            return
        try:
            token = self._sessions.login(self.user.text(), self.password.text())
        except (PermissionError, ValueError, OSError):
            self.status.setText("Anmeldung nicht möglich. Berechtigung prüfen.")
            self.password.clear()
            return
        self._token = token
        self.password.clear()
        self.user.clear()
        self.stack.setCurrentIndex(1)
        self._load(0)

    def _load(self, offset: int) -> None:
        if not self._project_current():
            self._logout()
            self.reject()
            return
        if self._token is None:
            self._logout()
            return
        try:
            data = self._sessions.inspect(
                self._token, self._project_id, limit=self.PAGE_SIZE, offset=offset,
            )
        except (PermissionError, ValueError, KeyError, OSError):
            self._logout()
            self.status.setText("Administratorsitzung ungültig oder Protokoll nicht verfügbar.")
            return
        self._offset = offset
        self.table.setRowCount(len(data))
        for row_index, item in enumerate(data):
            values = (
                str(item.approval_id),
                item.report_id,
                item.approved_by,
                item.approved_at_utc,
                "Ja" if item.reached_preview_end is True else (
                    "Nein" if item.reached_preview_end is False else "Unbekannt"
                ),
            )
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
        self.previous.setEnabled(offset > 0)
        self.next.setEnabled(len(data) == self.PAGE_SIZE and offset+self.PAGE_SIZE <= 10000)
        self.status.setText(
            f"Vertrauliche Auditansicht für Projekt {self._project_id} – "
            f"Einträge {offset+1} bis {offset+len(data)}"
            if data else "Für dieses Projekt sind auf dieser Seite keine Freigaben gespeichert."
        )

    def _logout(self) -> None:
        if self._token is not None:
            self._sessions.logout(self._token)
        self._token = None
        self.table.setRowCount(0)
        self._offset = 0
        self.password.clear()
        self.user.clear()
        self.stack.setCurrentIndex(0)
        self.status.setText("Administrator abgemeldet. Für erneuten Zugriff anmelden.")

    def closeEvent(self, event):
        self._logout()
        super().closeEvent(event)
