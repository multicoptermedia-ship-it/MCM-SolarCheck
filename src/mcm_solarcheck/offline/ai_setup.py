"""Explicit offline-only configuration for self-initialized OSS classification.

`init` is an administrator/operator step, NOT an app startup side effect.
Only the exact per-database-parent policy file can enable the optional trainer;
no environment URL, download, hub or third-party pretrained weight source.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from mcm_solarcheck.services.offline_ai_open_source import (
    LOCAL_BACKEND, verify_local_checkpoint,
)
from mcm_solarcheck.services.offline_training_preflight import OfflineTrainerConfiguration

CONFIG_NAME = "offline-ai-config.json"
SCHEMA = 1
RIGHTS_NOTE = "local-init-no-external-pretrained-weights"


def config_path_for_database(database_path: str | Path) -> Path:
    database = Path(database_path).absolute()
    return database.parent / CONFIG_NAME


def load_local_torchvision_training(database_path: str | Path):
    """Return an explicitly enabled (configuration, launcher) or None.

    An invalid existing configuration fails closed, instead of silently
    falling back to downloads or substituting an unreviewed model.
    """
    config_path = config_path_for_database(database_path)
    if not config_path.exists() and not config_path.is_symlink():
        return None
    if config_path.is_symlink() or not config_path.is_file() or (
        not 0 < config_path.stat().st_size <= 4096
    ):
        raise PermissionError("invalid offline AI policy file")
    try:
        record = json.loads(config_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid offline AI configuration") from exc
    if not isinstance(record, dict) or set(record) != {
        "schema", "backend", "weights_file", "sha256", "classes",
        "seed", "epochs", "torchvision_version", "license_review", "enabled",
    }:
        raise PermissionError("unrecognized offline AI configuration format")
    if (record["schema"] != SCHEMA or record["backend"] != LOCAL_BACKEND
            or record["enabled"] is not True or record["license_review"] != RIGHTS_NOTE):
        raise PermissionError("only explicitly enabled local OSS model permitted")
    weights = config_path.parent / record["weights_file"]
    if (not isinstance(record["weights_file"], str)
            or record["weights_file"] != "local-resnet18-init.pt"
            or weights.is_symlink()):
        raise PermissionError("only local, nonlinked model file permitted")
    evidence = verify_local_checkpoint(
        weights, expected_sha256=record["sha256"],
        class_count=record["classes"],
    )
    if (evidence.seed != record["seed"]
            or evidence.torchvision_version != record["torchvision_version"]):
        raise PermissionError("checkpoint provenance differs from activation policy")
    config = OfflineTrainerConfiguration(
        backend=LOCAL_BACKEND,
        backend_version=evidence.torchvision_version,
        model_weights=weights,
        model_sha256=evidence.weights_sha256,
        weights_license_review=RIGHTS_NOTE,
        epochs=record["epochs"],
        seed=evidence.seed,
    )
    # Lazy import only when an existing explicit local policy enables trainer.
    from mcm_solarcheck.services.offline_torchvision_classifier import local_resnet18_trainer
    return config, local_resnet18_trainer


def initialize_local_policy(
    database_path: str | Path, *, classes: int,
    seed: int, epochs: int,
) -> Path:
    """Create local seed checkpoint and opt-in policy, refusing any overwrite."""
    from mcm_solarcheck.services.offline_torchvision_classifier import initialize_local_resnet18
    config_path = config_path_for_database(database_path)
    root = config_path.parent
    if root.is_symlink() or not root.is_dir():
        raise ValueError("existing real SolarCheck database folder required")
    weights = root / "local-resnet18-init.pt"
    if (config_path.exists() or config_path.is_symlink()
            or weights.exists() or weights.is_symlink()
            or weights.with_suffix(".provenance.json").exists()):
        raise FileExistsError("offline AI model policy or weights already exists")
    if type(epochs) is not int or not 1 <= epochs <= 30:
        raise ValueError("bounded training epochs required (1-30)")
    provenance = initialize_local_resnet18(weights, classes=classes, seed=seed)
    record = {
        "schema": SCHEMA,
        "backend": LOCAL_BACKEND,
        "enabled": True,
        "weights_file": weights.name,
        "sha256": provenance.weights_sha256,
        "classes": provenance.class_count,
        "seed": provenance.seed,
        "epochs": epochs,
        "torchvision_version": provenance.torchvision_version,
        "license_review": RIGHTS_NOTE,
    }
    with config_path.open("x", encoding="utf-8") as file:
        json.dump(record, file, sort_keys=True, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    return config_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Operator-initiated, offline local OSS classification setup",
    )
    parser.add_argument("command", choices=("initialize", "verify"))
    parser.add_argument("--database", type=Path, required=True,
                        help="Absolute path to existing offline SQLite database")
    parser.add_argument("--classes", type=int)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args(argv)
    if not args.database.is_absolute() or not args.database.is_file():
        parser.error("absolute existing offline database path required")
    try:
        if args.command == "initialize":
            if args.classes is None:
                parser.error("--classes required for initial model configuration")
            path = initialize_local_policy(
                args.database, classes=args.classes,
                seed=args.seed, epochs=args.epochs,
            )
            print("Local OSS model policy initialized; no downloaded weights. " +
                  path.name)
        else:
            if load_local_torchvision_training(args.database) is None:
                raise PermissionError("no local trainer policy installed")
            print("Local OSS model policy verified; actual data rights still required.")
    except (ValueError, TypeError, OSError, PermissionError) as exc:
        parser.exit(2, f"Offline AI configuration unavailable: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
