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
QMainWindow {{
    background: {WORK_SURFACE};
}}
QMenuBar {{
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
QWidget#workflow_navigation {{
    background: {ANTHRACITE};
}}
QWidget#workflow_navigation QPushButton {{
    background: transparent;
    color: {TEXT_ON_DARK};
    border: 0;
    border-radius: 4px;
    padding: 9px 12px;
    text-align: left;
}}
QWidget#workflow_navigation QPushButton:hover,
QWidget#workflow_navigation QPushButton:focus {{
    background: {ANTHRACITE_RAISED};
}}
QWidget#workflow_navigation QPushButton[current="true"] {{
    background: {ACCENT_GREEN};
    font-weight: 600;
}}
"""
