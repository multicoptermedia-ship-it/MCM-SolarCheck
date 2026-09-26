"""Central visual tokens for the SolarCheck PySide6 application.

The palette follows the approved GUI contract: dark anthracite shell, light
work surface and a restrained green accent. Thermal colours remain reserved
for evidence visualisation and are intentionally absent here.
"""

APP_STYLE_SHEET = """
QMainWindow {
    background: #f4f5f3;
}
QMenuBar {
    background: #252a28;
    color: #f7f8f7;
    padding: 4px;
}
QMenuBar::item:selected,
QMenu {
    background: #343a37;
    color: #f7f8f7;
}
QMenu::item:selected {
    background: #3f4944;
}
QStackedWidget {
    background: #f4f5f3;
}
QLabel#page_heading {
    color: #252a28;
    font-size: 22px;
    font-weight: 600;
}
"""
