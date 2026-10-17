"""The project report adapter never manufactures a human review."""
import pytest

from mcm_solarcheck.services.orthophoto_project_report import (
    export_reviewed_project_orthophoto_pdf,
)


class FakeProjectService:
    def projects(self):
        from types import SimpleNamespace
        return (SimpleNamespace(project_id="p1"),)


def test_report_adapter_rejects_unknown_project(tmp_path):
    with pytest.raises(KeyError, match="Unknown project"):
        export_reviewed_project_orthophoto_pdf(
            FakeProjectService(), "other", object(), tmp_path / "rgb.tif",
            tmp_path / "report.pdf",
        )
    assert not (tmp_path / "report.pdf").exists()


def test_report_adapter_rejects_unreviewed_object(tmp_path):
    with pytest.raises(TypeError, match="PilotReport"):
        export_reviewed_project_orthophoto_pdf(
            FakeProjectService(), "p1", object(), tmp_path / "rgb.tif",
            tmp_path / "report.pdf",
        )
    assert not (tmp_path / "report.pdf").exists()
