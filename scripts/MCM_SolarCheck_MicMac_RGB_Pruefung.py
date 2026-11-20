"""Read existing MicMac RGB result summaries; no images, processing or writes.

Run with the existing offline Python. Choose the completed rgb_ortho.tif to
identify its job, or pass that path as the sole argument. Only fixed labels,
counts and finite numbers are printed, never paths, image names or coordinates.
This reports MicMac's own statistics; it makes no quality/release decision.
"""
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def _xml(path, expected_root):
    if not path.exists():
        return None, "fehlt"
    try:
        if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
            return None, "nicht_lesbar"
        data = path.read_bytes()
        # No DTD/entities, including UTF-16/32 encodings, are needed here.
        check = data.replace(b"\0", b"").upper()
        if b"<!DOCTYPE" in check or b"<!ENTITY" in check:
            return None, "nicht_lesbar"
        root = ET.fromstring(data)
        if root.tag != expected_root:
            return None, "unbekanntes_format"
        return root, "gelesen"
    except (OSError, ET.ParseError, ValueError):
        return None, "nicht_lesbar"


def _number(node, tag):
    value = float(node.findtext(tag))
    if not math.isfinite(value) or value < 0:
        raise ValueError("invalid statistic")
    return round(value, 6)


def _statistics(path, kind):
    expected = "XmlSauvExportAperoGlob" if kind == "tapas" else "Xml_SolBascRigide"
    root, status = _xml(path, expected)
    result = {"status": status}
    if root is None:
        return result
    try:
        if kind == "tapas":
            iterations = root.findall("Iters")
            if not iterations:
                return {"status": "keine_iteration"}
            last = iterations[-1]
            result.update(iterationen=len(iterations),
                          bilder_letzte_iteration=len(last.findall("OneIm")),
                          AverageResidual=_number(last, "AverageResidual"))
            if last.find("WorstRes") is not None:
                result["WorstRes"] = _number(last, "WorstRes")
        else:
            result.update(kamerazentren=len(root.findall("Residus")),
                          MoyenneDist=_number(root, "MoyenneDist"),
                          groesste_Dist=_number(root, "Worst/Dist"))
    except (TypeError, ValueError, OverflowError):
        return {"status": "ungueltige_kennzahlen"}
    return result


def summarize(rgb_ortho):
    result = Path(rgb_ortho)
    if result.name.lower() != "rgb_ortho.tif" or not result.is_file():
        raise ValueError("select the RGB result")
    folder = result.parent / "rgb"
    if not folder.is_dir():
        raise ValueError("missing RGB workspace")
    copies = {p.name for p in folder.iterdir()
              if re.fullmatch(r"[0-9]{6}[.]JPG", p.name) and p.is_file()}
    report = {"rgb_arbeitskopien": len(copies)}
    for orientation in ("Rel", "Ground"):
        path = folder / ("Ori-" + orientation)
        names = {p.name[len("Orientation-"):-len(".xml")]
                 for p in path.glob("Orientation-*.xml")
                 if re.fullmatch(r"Orientation-[0-9]{6}[.]JPG[.]xml", p.name)
                 and p.is_file()}
        report[orientation] = {"orientierungsdateien": len(names),
                               "fehlend": len(copies - names),
                               "ohne_arbeitskopie": len(names - copies)}
    report["Tapas"] = _statistics(folder / "Ori-Rel" / "Residus.xml", "tapas")
    report["GPS_Abgleich"] = _statistics(
        folder / "Ori-Ground" / "Result-Center-Bascule.xml", "gps")
    return report


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) > 1:
            raise ValueError("one file only")
        if args:
            selected = args[0]
        else:
            from tkinter import Tk, filedialog
            window = Tk()
            window.withdraw()
            try:
                selected = filedialog.askopenfilename(
                    title="Vorhandenes MicMac-Ergebnis rgb_ortho.tif auswaehlen",
                    filetypes=[("MicMac RGB-GeoTIFF", "rgb_ortho.tif")])
            finally:
                window.destroy()
        if not selected:
            print("Auswahl abgebrochen; nichts geaendert.")
            return 0
        report = summarize(selected)
    except Exception:
        # Even file-dialog/OS/XML errors must not expose private values.
        print("Pruefung nicht moeglich. Vorhandenes rgb_ortho.tif im MicMac-Laufordner waehlen.")
        return 1
    print("Nur bestehende MicMac-Kennzahlen; keine Qualitaetsfreigabe.")
    print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
