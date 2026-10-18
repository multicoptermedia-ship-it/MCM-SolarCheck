"""Plain-language Qt status for bounded nonmetric flight segment previews."""


def format_rgb_segments_result(result, summary_path):
    """Distinguish exported previews from complete or georeferenced products."""
    exported = result["exported"]
    failed = result["failed"]
    sampled = result.get("sampled_previews", sum(
        bool(record.get("preview_incomplete", False))
        for record in result.get("segments", [])
    ))
    if type(sampled) is not int or sampled < 0 or sampled > exported:
        raise ValueError("invalid count of incomplete RGB previews")
    complete = exported - sampled
    return (
        f"RGB-Segmentexport: {exported} Vorschauen exportiert "
        f"({complete} mit allen Segmentbildern, {sampled} unvollständig), "
        f"{failed} fehlgeschlagen, "
        f"Abbruch: {'ja' if result['cancelled'] else 'nein'}. "
        f"Zusammenfassung: {summary_path}. "
        "Nur nichtmetrische Vorschauen; kein verifiziertes Orthofoto."
    )
