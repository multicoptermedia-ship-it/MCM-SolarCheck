from mcm_solarcheck.thermal.analysis import hottest_raw_candidates, raw_statistics
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, assess_raw_thermal_quality


def raster(values, width=4, height=2):
    return RadiometricRaster(
        width=width,
        height=height,
        byte_order="little",
        samples=tuple(values),
        component_index=0,
    )


def test_raw_statistics():
    stats = raw_statistics(raster([10, 20, 30, 40, 50, 60, 70, 80]))
    assert stats.minimum == 10
    assert stats.maximum == 80
    assert stats.mean == 45
    assert stats.median == 45
    assert stats.p95 == 80
    assert stats.dynamic_range == 70


def test_hottest_candidates_keep_coordinates_and_rank():
    result = hottest_raw_candidates(
        raster([10, 11, 12, 13, 14, 100, 15, 90]),
        percentile=75,
        minimum_delta_from_median=20,
        limit=2,
    )
    assert [(item.x, item.y, item.raw_value) for item in result] == [
        (1, 1, 100),
        (3, 1, 90),
    ]


def test_quality_rejects_wrong_dimensions():
    result = assess_raw_thermal_quality(raster([1] * 8), minimum_dynamic_range=0)
    assert result.grade == ThermalQualityGrade.REJECT
    assert "unexpected raster dimensions" in result.reasons[0]


def test_quality_reviews_degenerate_frame():
    values = [20_000] * (640 * 512)
    result = assess_raw_thermal_quality(
        raster(values, width=640, height=512),
        minimum_dynamic_range=100,
    )
    assert result.grade == ThermalQualityGrade.REVIEW
    assert result.reasons == ("low raw dynamic range: 0",)


def test_quality_passes_plausible_structural_frame():
    values = [19_000 + (i % 1000) for i in range(640 * 512)]
    result = assess_raw_thermal_quality(raster(values, width=640, height=512))
    assert result.grade == ThermalQualityGrade.PASS
    assert result.reasons == ()
