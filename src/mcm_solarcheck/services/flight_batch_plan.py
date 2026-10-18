"""Independent RGB/Thermal capture grouping for bounded offline processing."""
from mcm_solarcheck.services.flight_inventory import scan_flight


def plan_flight_batches(folder, *, batch_size=80, overlap=10, max_captures=1000):
    """Plan overlapping capture groups; no images are decoded or resized."""
    if (type(batch_size) is not int or batch_size < 2 or
            type(overlap) is not int or overlap < 1 or overlap >= batch_size or
            type(max_captures) is not int or max_captures < 1):
        raise ValueError("invalid batch configuration")
    captures, ignored = scan_flight(folder)
    if len(captures) > max_captures:
        raise ValueError("flight exceeds configured capture limit")
    step = batch_size - overlap
    batches = []
    start = 0
    while start < len(captures):
        end = min(start + batch_size, len(captures))
        group = captures[start:end]
        batches.append({"index": len(batches), "start": start, "end": end,
                        "captures": group})
        if end == len(captures):
            break
        start += step
    return {"capture_count": len(captures), "batches": tuple(batches),
            "ignored": ignored, "batch_size": batch_size, "overlap": overlap}
