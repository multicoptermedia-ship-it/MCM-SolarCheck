"""First local PV infrared *research* evaluation, independent of report models.

A pure Python/Pillow supervised nearest-centroid baseline on upstream image
labels. Because Raptor Maps supplies no original physical site/group IDs, the
deterministic image-level split cannot demonstrate site-independent accuracy.
Results NEVER authorize report or model deployment and are not persisted in
any client training/consent database.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from PIL import Image

from mcm_solarcheck.services.pv_public_infrared_source import DATASET_ID, ORIGINAL_CLASSES

SPLIT_NOTICE = (
    "Exploratory image-ID split; original site/physical-module groups unavailable. "
    "Correlated images can leak between train/validation/test. No field-valid metrics."
)


def exploratory_split(source_id: str) -> str:
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("nonempty public image ID required")
    score = int.from_bytes(
        sha256(("public-infrared-experiment-v1:" + source_id).encode()).digest()[:4],
        "big",
    ) % 100
    return "train" if score < 70 else "validation" if score < 85 else "test"


def _pixels(image_path: Path, expected_sha256: str) -> tuple[float, ...]:
    if (image_path.is_symlink() or not image_path.is_file()
            or not 0 < image_path.stat().st_size <= 2_000_000):
        raise PermissionError("public image unavailable or linked")
    content = image_path.read_bytes()
    if sha256(content).hexdigest() != expected_sha256:
        raise PermissionError("public image hash differs from imported archive")
    with Image.open(BytesIO(content)) as image:
        if image.format != "JPEG" or sorted(image.size) != [24, 40]:
            raise PermissionError("unexpected 8-bit public infrared sample")
        pixels = image.convert("L").resize((24, 40)).getdata()
        return tuple(p / 255.0 for p in pixels)


def run_public_infrared_baseline(catalog: Path, result_file: Path) -> dict:
    if (not catalog.is_absolute() or catalog.is_symlink()
            or not catalog.is_file() or catalog.name != "public-infrared-index.json"
            or not 0 < catalog.stat().st_size <= 8_000_000):
        raise PermissionError("private imported public dataset catalog required")
    if (not result_file.is_absolute() or result_file.exists()
            or result_file.is_symlink() or not result_file.parent.is_dir()
            or result_file.parent.is_symlink()):
        raise PermissionError("fresh absolute research results file required")
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("corrupt public corpus catalog") from exc
    if (not isinstance(data, dict) or data.get("dataset_id") != DATASET_ID
            or data.get("status") != "exploratory_only_not_approved_for_reports"
            or data.get("site_grouping") != "not_available_no_site_disjoint_validation"
            or not isinstance(data.get("samples"), list)):
        raise PermissionError("only pinned exploratory imported data accepted")
    rows = data["samples"]
    if not 6 <= len(rows) <= 20_100:
        raise ValueError("at least six imported public samples required")
    centroids = {}
    sums = {}
    counts = Counter()
    by_split = {"train": [], "validation": [], "test": []}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "source_id", "image", "class", "sha256",
        }:
            raise ValueError("corrupt public label entry")
        source_id, label, filename = row["source_id"], row["class"], row["image"]
        if (not isinstance(source_id, str) or not source_id
                or source_id in seen
                or not isinstance(label, str) or label not in ORIGINAL_CLASSES
                or filename != "images/" + source_id + ".jpg"
                or "/" in source_id or "\\" in source_id
                or not isinstance(row["sha256"], str) or len(row["sha256"]) != 64):
            raise PermissionError("invalid public image identity or label")
        seen.add(source_id)
        pixels = _pixels(catalog.parent / filename, row["sha256"])
        split = exploratory_split(source_id)
        if split == "train":
            if label not in sums:
                sums[label] = [0.0] * len(pixels)
            counts[label] += 1
            for index, pixel in enumerate(pixels):
                sums[label][index] += pixel
        else:
            by_split[split].append((label, pixels))
        if split == "train":
            by_split["train"].append(label)
    if len(sums) < 2 or not by_split["validation"] or not by_split["test"]:
        raise ValueError("experimental baseline requires 2 train classes and both holdout sets")
    centroids = {
        label: tuple(v / counts[label] for v in vector)
        for label, vector in sums.items()
    }

    def measure(split):
        matrix = {}
        correct = 0
        for truth, pixels in by_split[split]:
            best = min(
                centroids, key=lambda label: sum(
                    (pixel - average) ** 2
                    for pixel, average in zip(pixels, centroids[label])
                ),
            )
            line = matrix.setdefault(truth, {})
            line[best] = line.get(best, 0) + 1
            correct += best == truth
        total = len(by_split[split])
        return {"samples": total, "correct": correct,
                "accuracy": round(correct / total, 6),
                "confusion": {key: dict(sorted(val.items())) for key, val in sorted(matrix.items())}}

    evaluation = {
        "status": "experimental_no_report_or_model_approval",
        "method": "grayscale_nearest_class_centroid_baseline",
        "dataset_id": DATASET_ID,
        "source_archive_sha256": data.get("archive_sha256"),
        "split_warning": SPLIT_NOTICE,
        "source_modality": "8-bit infrared JPEG visual values only",
        "train": {"samples": len(by_split["train"]),
                  "classes": dict(sorted(counts.items()))},
        "validation": measure("validation"),
        "test": measure("test"),
        "limitations": (
            "Simple descriptive research baseline, not TorchVision model, "
            "not physical-site-separated, not radiometric temperature "
            "measurement, not validated DJI-Mavic-3T PV fault diagnosis."
        ),
    }
    with result_file.open("x", encoding="utf-8") as stream:
        json.dump(evaluation, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return evaluation


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Exploratory local 8-bit PV infrared baseline; never deployed",
    )
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--acknowledge-no-site-groups", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_no_site_groups:
        parser.error("explicit exploratory image-level split acknowledgement required")
    try:
        results = run_public_infrared_baseline(args.catalog, args.results)
    except (ValueError, PermissionError, OSError, KeyError) as exc:
        parser.exit(2, f"Public baseline rejected: {exc}\n")
    print("Exploratory infrared baseline completed; "
          f"validation={results['validation']['accuracy']:.4f} "
          f"test={results['test']['accuracy']:.4f}; "
          "NO independent site validation, NO model approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
