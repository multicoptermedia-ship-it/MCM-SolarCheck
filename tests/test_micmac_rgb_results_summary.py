"""Only synthetic existing outputs; protect private data and select the right job."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/MCM_SolarCheck_MicMac_RGB_Pruefung.py"
spec = importlib.util.spec_from_file_location("micmac_rgb_summary", SCRIPT)
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


@pytest.fixture
def job(tmp_path):
    root = tmp_path / "PRIVATE customer [job]"
    rgb = root / "rgb"
    (rgb / "Ori-Rel").mkdir(parents=True)
    (rgb / "Ori-Ground").mkdir()
    (root / "rgb_ortho.tif").write_bytes(b"not an image; must never be decoded")
    for index in (1, 2):
        name = f"{index:06d}.JPG"
        (rgb / name).write_bytes(b"PRIVATE original pixels")
        for orientation in ("Rel", "Ground"):
            (rgb / f"Ori-{orientation}" / f"Orientation-{name}.xml").write_text(
                "PRIVATE camera coordinates: must not be read")
    (rgb / "Ori-Rel" / "Residus.xml").write_text(
        '<XmlSauvExportAperoGlob>'
        '<Iters><AverageResidual>99</AverageResidual><WorstRes>100</WorstRes></Iters>'
        '<Iters><AverageResidual>0.75</AverageResidual><WorstRes>2.5</WorstRes>'
        '<OneIm><Name>PRIVATE 000001.JPG</Name></OneIm>'
        '<OneIm><Name>PRIVATE 000002.JPG</Name></OneIm></Iters>'
        '</XmlSauvExportAperoGlob>')
    (rgb / "Ori-Ground" / "Result-Center-Bascule.xml").write_text(
        '<Xml_SolBascRigide><Param><Trans>PRIVATE GPS</Trans></Param>'
        '<MoyenneDist>1.25</MoyenneDist>'
        '<Worst><Name>PRIVATE image</Name><Dist>2.75</Dist></Worst>'
        '<Residus><Offset>PRIVATE GPS</Offset></Residus><Residus/>'
        '</Xml_SolBascRigide>')
    return root


def test_existing_job_is_read_only_and_summary_does_not_read_images_or_pose_xml(job, monkeypatch):
    before = {p: p.read_bytes() for p in job.rglob("*") if p.is_file()}
    read = Path.read_bytes
    accessed = []

    def guarded_read(path):
        assert path.name in {"Residus.xml", "Result-Center-Bascule.xml"}
        accessed.append(path.name)
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    result = summary.summarize(job / "rgb_ortho.tif")
    assert result["rgb_arbeitskopien"] == 2
    assert result["Rel"] == {"orientierungsdateien": 2, "fehlend": 0, "ohne_arbeitskopie": 0}
    assert result["Ground"] == result["Rel"]
    assert result["Tapas"] == {"status": "gelesen", "iterationen": 2,
                               "bilder_letzte_iteration": 2,
                               "AverageResidual": 0.75, "WorstRes": 2.5}
    assert result["GPS_Abgleich"] == {"status": "gelesen", "kamerazentren": 2,
                                     "MoyenneDist": 1.25, "groesste_Dist": 2.75}
    assert len(accessed) == 2
    assert "PRIVATE" not in json.dumps(result)
    assert {p: read(p) for p in job.rglob("*") if p.is_file()} == before


def test_equal_counts_cannot_hide_wrong_camera_set(job):
    rel = job / "rgb" / "Ori-Rel"
    (rel / "Orientation-000002.JPG.xml").rename(rel / "Orientation-000003.JPG.xml")
    (rel / "Orientation-unrelated.JPG.xml").write_text("not a job image")
    result = summary.summarize(job / "rgb_ortho.tif")
    assert result["Rel"] == {"orientierungsdateien": 2, "fehlend": 1, "ohne_arbeitskopie": 1}
    assert result["Ground"]["fehlend"] == 0


@pytest.mark.parametrize("content,status", [
    (None, "fehlt"),
    (b"<invalid PRIVATE", "nicht_lesbar"),
    (b"<Other>PRIVATE</Other>", "unbekanntes_format"),
    (b'<XmlSauvExportAperoGlob/>', "keine_iteration"),
    (b'<XmlSauvExportAperoGlob><Iters><AverageResidual>NaN</AverageResidual>'
     b'</Iters></XmlSauvExportAperoGlob>', "ungueltige_kennzahlen"),
    ('<!DOCTYPE x [<!ENTITY x "PRIVATE">]><XmlSauvExportAperoGlob/>'
     .encode('utf-16'), "nicht_lesbar"),
])
def test_missing_and_invalid_results_are_not_reported_as_success(job, content, status):
    path = job / "rgb" / "Ori-Rel" / "Residus.xml"
    if content is None:
        path.unlink()
    else:
        path.write_bytes(content)
    result = summary.summarize(job / "rgb_ortho.tif")
    assert result["Tapas"] == {"status": status}
    assert result["GPS_Abgleich"]["status"] == "gelesen"


def test_actual_download_script_runs_without_app_imports_and_leaks_no_private_values(job):
    run = subprocess.run([sys.executable, str(SCRIPT), str(job / "rgb_ortho.tif")],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 0
    assert not run.stderr
    assert "PRIVATE" not in run.stdout
    assert "000001.JPG" not in run.stdout
    assert str(job) not in run.stdout
    assert json.loads(run.stdout.split("\n", 1)[1])["Tapas"]["AverageResidual"] == 0.75


def test_bad_selection_produces_only_fixed_error_not_traceback_or_path(job, capsys):
    assert summary.main([str(job / "PRIVATE missing.tif")]) == 1
    output = capsys.readouterr()
    assert "Pruefung nicht moeglich" in output.out
    assert "PRIVATE" not in output.out
    assert not output.err
