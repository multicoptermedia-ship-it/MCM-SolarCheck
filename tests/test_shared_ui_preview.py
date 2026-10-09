"""Unit checks for shared preview routing (not production API tests)."""
from pathlib import Path

import pytest

from shared_ui.server import UI_FILE, make_handler


def test_single_shared_ui_file():
    assert UI_FILE.is_file()
    assert UI_FILE.name == "index.html"
    assert UI_FILE.parent.name == "frontend"


@pytest.mark.parametrize("mode", ["online", "offline"])
def test_preview_mode(mode):
    assert make_handler(mode).__name__ == "Handler"


def test_reject_unknown_mode():
    with pytest.raises(ValueError):
        make_handler("demo")
