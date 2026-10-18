"""Conservative resource estimates for sequential JPEG working-array conversion.

Estimates are planning hints, not measured peak resident memory.
"""


def estimate_rgb_conversion_resources(dimensions, *, concurrent_decodes=1,
                                      ram_multiplier=5, disk_overhead=4096):
    """Estimate RGB working disk and transient RAM budgets from (width, height)."""
    if (type(concurrent_decodes) is not int or concurrent_decodes < 1
            or type(ram_multiplier) is not int or ram_multiplier < 3
            or type(disk_overhead) is not int or disk_overhead < 0):
        raise ValueError("invalid RGB resource planning limits")
    counts = []
    for width, height in dimensions:
        if (type(width) is not int or type(height) is not int
                or width < 1 or height < 1):
            raise ValueError("invalid RGB frame dimensions")
        counts.append(width * height * 3)
    peak_frame = max(counts, default=0)
    return {
        "frame_count": len(counts),
        "estimated_working_disk_bytes": sum(size + disk_overhead for size in counts),
        "estimated_peak_ram_bytes": peak_frame * ram_multiplier * concurrent_decodes,
        "assumed_concurrent_decodes": concurrent_decodes,
        "estimate_only": True,
        "peak_rss_measured": False,
    }
