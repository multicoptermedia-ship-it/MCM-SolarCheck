"""Independent nonmetric geometry chaining for adjacent RGB registration links."""
import numpy as np


def chain_rgb_links(links):
    """Build one local transform chain per uninterrupted registered segment."""
    segments = []
    current = None
    for link in links:
        if current is None or current["last"] != link["first"]:
            current = {"first": link["first"], "last": link["first"],
                       "frames": {link["first"]: np.eye(3).tolist()}}
            segments.append(current)
        if link["status"] != "registered" or "homography" not in link:
            current = None
            continue
        matrix = np.asarray(link["homography"], dtype=np.float64)
        if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
            raise ValueError("invalid homography in RGB link")
        previous = np.asarray(current["frames"][link["last"]])
        combined = matrix @ previous
        if not np.isfinite(combined).all() or abs(combined[2, 2]) < 1e-12:
            raise ValueError("unstable RGB transform chain")
        combined /= combined[2, 2]
        current["frames"][link["second"]] = combined.tolist()
        current["last"] = link["second"]
    return {"segments": segments, "metric_orthophoto_verified": False}
