"""The stable -m offline launcher must resolve to offline, never online."""
from __future__ import annotations

import runpy

import pytest


def test_offline_module_main_resolves_to_offline_product(monkeypatch):
    from mcm_solarcheck.offline import entrypoint

    calls = []
    def fake_main():
        calls.append("offline")
        return 43
    monkeypatch.setattr(entrypoint, "main", fake_main)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("mcm_solarcheck.offline", run_name="__main__")
    assert exc.value.code == 43
    assert calls == ["offline"]
