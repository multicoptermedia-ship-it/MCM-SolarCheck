from mcm_solarcheck.review.defect_classes import (
    DEFAULT_THERMAL_CLASS_MAP,
    DatasetClassMap,
    DefectClass,
)


def test_external_thermal_labels_map_to_canonical_candidates():
    assert DEFAULT_THERMAL_CLASS_MAP.normalize("Hot Spot") == DefectClass.THERMAL_HOTSPOT_CANDIDATE
    assert DEFAULT_THERMAL_CLASS_MAP.normalize("CELL HOTSPOT") == DefectClass.CELL_HOTSPOT_CANDIDATE
    assert DEFAULT_THERMAL_CLASS_MAP.normalize("open circuit") == DefectClass.OPEN_CIRCUIT_CANDIDATE


def test_unknown_external_label_is_not_guessed():
    assert DEFAULT_THERMAL_CLASS_MAP.normalize("mystery defect") == DefectClass.UNKNOWN
    assert DEFAULT_THERMAL_CLASS_MAP.normalize(" ") == DefectClass.UNKNOWN


def test_dataset_mapping_requires_source_identity():
    try:
        DatasetClassMap(" ", {"hotspot": DefectClass.THERMAL_HOTSPOT_CANDIDATE})
    except ValueError:
        pass
    else:
        raise AssertionError("anonymous dataset mapping must fail")


def test_mapping_does_not_turn_candidate_into_confirmed_diagnosis():
    mapped=DEFAULT_THERMAL_CLASS_MAP.normalize("short circuit")
    assert mapped == DefectClass.SHORT_CIRCUIT_CANDIDATE
    assert mapped.value.endswith("_candidate")
