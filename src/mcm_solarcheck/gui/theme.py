"""Central visual tokens for the SolarCheck PySide6 application.

These documented UI tokens implement the approved visual roles without sampling
generated mockups. Thermal colours remain reserved for evidence visualisation.
Approved corporate-design assets may replace token values centrally later.
"""

ANTHRACITE = "#252a28"
ANTHRACITE_RAISED = "#343a37"
ANTHRACITE_HOVER = "#3f4944"
WORK_SURFACE = "#f4f5f3"
TEXT_ON_DARK = "#f7f8f7"
TEXT_PRIMARY = "#252a28"
ACCENT_GREEN = "#3f8f5b"

APP_STYLE_SHEET = f"""
/* Shared readable baseline. Native Qt scales pixels by the OS DPI factor. */
QWidget {{
    font-size: 18px;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {{
    min-height: 27px;
}}
QMainWindow {{
    background: {WORK_SURFACE};
}}
QMenuBar {{
    font-size: 17px;
    background: {ANTHRACITE};
    color: {TEXT_ON_DARK};
    padding: 4px;
}}
QMenuBar::item:selected,
QMenu {{
    background: {ANTHRACITE_RAISED};
    color: {TEXT_ON_DARK};
}}
QMenu::item:selected {{
    background: {ANTHRACITE_HOVER};
}}
QStackedWidget {{
    background: {WORK_SURFACE};
}}
QLabel#page_heading {{
    color: {TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 600;
}}
QLabel#provider_attribution {{
    color: {ANTHRACITE_HOVER};
    font-size: 11px;
}}
/* Keep every normal button legible without mouse hover on Windows 10.
   The disabled state is visible but cannot be mistaken for an active action. */
QPushButton {{
    background: #e2e8e3;
    color: {TEXT_PRIMARY};
    border: 1px solid #87968c;
    border-radius: 4px;
    padding: 7px 11px;
}}
QPushButton:hover, QPushButton:focus {{
    background: #d1dfd5;
    color: {TEXT_PRIMARY};
}}
QPushButton:disabled {{
    background: #e7eae7;
    color: #565f59;
    border: 1px solid #a5afa8;
}}
QWidget#workflow_navigation {{
    background-color: {ANTHRACITE};
}}
QWidget#workflow_navigation QPushButton {{
    background-color: #39423d;
    color: {TEXT_ON_DARK};
    border: 0;
    border-radius: 4px;
    padding: 10px 12px;
    min-height: 32px;
    text-align: left;
}}
QWidget#workflow_navigation QPushButton:disabled {{
    background: {ANTHRACITE_RAISED};
    color: #d3dad5;
    border: 1px solid #77847b;
}}
QWidget#workflow_navigation QPushButton:hover,
QWidget#workflow_navigation QPushButton:focus {{
    background: {ANTHRACITE_RAISED};
}}
QWidget#workflow_navigation QPushButton[current="true"] {{
    background: {ACCENT_GREEN};
    font-weight: 600;
}}
QWidget#workflow_navigation QPushButton[blocked="true"] {{
    border-left: 4px solid #b7c5b9;
}}
QWidget#workflow_navigation QLabel[navigationStatus="true"] {{
    color: #e0e7e1;
    background: {ANTHRACITE};
    font-size: 13px;
    padding: 0 10px 6px 10px;
}}
QLabel#workflow_blocker_explanation {{
    background: {ANTHRACITE_RAISED};
    color: {TEXT_ON_DARK};
    border-radius: 4px;
    padding: 8px;
}}
"""
