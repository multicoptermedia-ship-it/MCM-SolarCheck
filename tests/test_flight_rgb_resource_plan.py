"""Resource estimates are intentionally conservative, never claimed as RSS."""
import pytest

from mcm_solarcheck.services.flight_rgb_resource_plan import (
    estimate_rgb_conversion_resources,
)


def test_sequential_flight_resource_estimate():
    result = estimate_rgb_conversion_resources([(4000, 3000)] * 1000)
    assert result["frame_count"] == 1000
    assert result["estimated_working_disk_bytes"] == 1000 * (36_000_000 + 4096)
    assert result["estimated_peak_ram_bytes"] == 36_000_000 * 5
    assert result["peak_rss_measured"] is False
    assert result["estimate_only"] is True


def test_parallelism_increases_estimated_ram_not_disk():
    serial = estimate_rgb_conversion_resources([(10, 20), (20, 30)])
    parallel = estimate_rgb_conversion_resources(
        [(10, 20), (20, 30)], concurrent_decodes=2
    )
    assert parallel["estimated_peak_ram_bytes"] == 2 * serial["estimated_peak_ram_bytes"]
    assert parallel["estimated_working_disk_bytes"] == serial["estimated_working_disk_bytes"]


@pytest.mark.parametrize("dimensions", [[(0, 5)], [(True, 5)], [(-1, 2)]])
def test_invalid_dimensions_rejected(dimensions):
    with pytest.raises(ValueError):
        estimate_rgb_conversion_resources(dimensions)
