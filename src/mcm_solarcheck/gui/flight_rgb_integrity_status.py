"""German presentation contract for read-only RGB provenance checks."""


def format_rgb_integrity_summary(result):
    """Render service statuses without implying expert approval or authenticity."""
    labels = {
        "missing": "Arbeitsdatei fehlt",
        "existing_shape_valid": "Format plausibel; Herkunft ungeprüft",
        "verified_provenance": "Prüfsummen stimmen mit lokalem Manifest überein",
        "invalid": "Arbeitsdatei beschädigt oder unpassend",
        "unsafe": "Unsicherer Dateiverweis",
    }
    entries = result["entries"]
    lines = ["RGB-Arbeitsdateien – schreibgeschützte Integritätsprüfung"]
    for item in entries:
        status = item["status"]
        if status not in labels:
            raise ValueError("unknown RGB integrity status")
        lines.append(f"{item['source_name']}: {labels[status]}")
    lines.append("Keine automatische Wiederaufnahme oder fachliche Freigabe.")
    lines.append("Lokale Prüfsummen belegen keine authentische Herkunft.")
    return "\n".join(lines)
