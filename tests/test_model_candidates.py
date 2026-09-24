from mcm_solarcheck.review.model_candidates import (
    PV_HSD_2025_COMMERCIAL_USE_APPROVED,
    PV_HSD_2025_YOLOV8S_P1,
)


def test_pv_hsd_candidate_is_explicitly_validation_only():
    assert PV_HSD_2025_YOLOV8S_P1.modality == "thermal"
    assert PV_HSD_2025_YOLOV8S_P1.weights_sha256 == (
        "f466bcc39afeed1389df40a487398bd6ca9137dbf649642f9a557ef63ec98bca"
    )
    assert "commercial permission required" in PV_HSD_2025_YOLOV8S_P1.license_id
    assert PV_HSD_2025_COMMERCIAL_USE_APPROVED is False
