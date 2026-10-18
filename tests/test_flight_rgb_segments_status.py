"""Desktop result text must never hide incomplete nonmetric previews."""
import pytest

from mcm_solarcheck.gui.flight_rgb_segments_status import format_rgb_segments_result


def test_status_identifies_sampled_and_complete_previews():
    result = {"exported": 3, "failed": 1, "cancelled": False,
              "sampled_previews": 2}
    status = format_rgb_segments_result(result, "/tmp/segments_summary.json")
    assert "1 mit allen Segmentbildern" in status
    assert "2 unvollständig" in status
    assert "1 fehlgeschlagen" in status
    assert "kein verifiziertes Orthofoto" in status


def test_status_handles_older_summary_and_cancellation():
    result = {"exported": 1, "failed": 0, "cancelled": True,
              "segments": [{"status": "exported", "preview_incomplete": True}]}
    status = format_rgb_segments_result(result, "summary.json")
    assert "1 unvollständig" in status
    assert "Abbruch: ja" in status


@pytest.mark.parametrize("sampled", [-1, 3, 1.5, True])
def test_status_rejects_invalid_sampled_counts(sampled):
    with pytest.raises(ValueError, match="invalid count"):
        format_rgb_segments_result(
            {"exported": 2, "failed": 0, "cancelled": False,
             "sampled_previews": sampled}, "summary.json")
