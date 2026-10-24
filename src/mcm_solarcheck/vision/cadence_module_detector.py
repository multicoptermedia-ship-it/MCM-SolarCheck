"""Cadence-aware PV module detector with fail-closed independent image support.

Both path-backed legacy callers and SHA-verified in-memory RGB callers share
the same geometry, cadence, phase and IoU gates. Rejection reasons are technical
diagnostics, NOT confirmation that a module exists or is absent.
"""
from __future__ import annotations

from pathlib import Path
from math import isfinite

import cv2
import numpy as np

from mcm_solarcheck.pairing.structural_features import detect_structural_lines
from mcm_solarcheck.pairing.grid_lines import extract_grid_line_families
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector
from mcm_solarcheck.vision.cadence_gate import assess_ambiguous_module_cadence
from mcm_solarcheck.vision.cadence_phase_selection import select_cadence_phase
from mcm_solarcheck.vision.grid_module_detector import grid_module_detections
from mcm_solarcheck.vision.grid_cadence import cadence_line_subsets
from mcm_solarcheck.vision.grid_cell_support import filter_cells_by_finite_support
from mcm_solarcheck.vision.module_fusion import fuse_module_detections
from mcm_solarcheck.vision.detection import ModuleDetection


class CadenceConfirmedModuleDetector:
    name = "cadence_confirmed_pv_module_v1"

    def __init__(self, *, max_dimension: int = 900, minimum_iou: float = .20):
        self.max_dimension = max_dimension
        self.minimum_iou = minimum_iou
        self.image_detector = OpenCVModuleDetector()

    def _configured(self) -> bool:
        return (
            type(self.max_dimension) is int and self.max_dimension > 0
            and isfinite(float(self.minimum_iou))
            and 0.0 <= self.minimum_iou <= 1.0
        )

    @staticmethod
    def _pixels_valid(image) -> bool:
        return (
            isinstance(image, np.ndarray)
            and image.dtype == np.uint8
            and image.ndim == 3 and image.shape[2] == 3
            and image.shape[0] > 0 and image.shape[1] > 0
            and image.shape[0] * image.shape[1] <= 64_000_000
        )

    def detect(self, source_file: Path) -> tuple[ModuleDetection, ...]:
        """Compatibility with existing path-backed, unverified detector users."""
        if not self._configured():
            return ()
        image = cv2.imread(str(source_file), cv2.IMREAD_COLOR)
        if image is None:
            return ()
        support = self.image_detector.detect(source_file)
        results, _ = self._detect_on_pixels(image, support)
        return results

    def detect_array(self, image: np.ndarray) -> tuple[ModuleDetection, ...]:
        """Detect on SHA-authenticated BGR pixels, never reopen source files."""
        results, _ = self.detect_array_with_status(image)
        return results

    def detect_array_with_status(
        self, image: np.ndarray,
    ) -> tuple[tuple[ModuleDetection, ...], str]:
        """Return candidates and a bounded technical rejection reason."""
        if not self._configured():
            return (), "invalid_detector_configuration"
        if not self._pixels_valid(image):
            return (), "invalid_bgr_image"
        independent_support = self.image_detector.detect_array(image)
        return self._detect_on_pixels(image, independent_support)

    def _detect_on_pixels(self, image, support_full):
        if not self._pixels_valid(image):
            return (), "invalid_bgr_image"
        h, w = image.shape[:2]
        scale = min(1.0, self.max_dimension / max(h, w))
        small = (
            cv2.resize(image, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_AREA)
            if scale < 1 else image
        )
        lines = detect_structural_lines(
            small, max_dimension=self.max_dimension,
            min_length_fraction=.08,
        )
        families = extract_grid_line_families(lines)
        support = tuple(
            ModuleDetection(
                tuple((x * scale, y * scale) for x, y in d.polygon_px),
                d.confidence, d.class_name,
            )
            for d in support_full
        )
        gate = assess_ambiguous_module_cadence(
            families, support, lines, small.shape[1], small.shape[0],
            minimum_iou=self.minimum_iou,
        )
        if not gate.accepted:
            return (), gate.reason
        if len(gate.axes) != 2:
            return (), "invalid_cadence_axes"
        if any(
            type(axis.dominant_multiple) is not int
            or axis.dominant_multiple < 2
            for axis in gate.axes
        ):
            return (), "invalid_cadence_multiple"
        if any(
            axis.median_gap_px is None
            or not isfinite(float(axis.median_gap_px))
            or axis.median_gap_px <= 0
            for axis in gate.axes
        ):
            return (), "invalid_cadence_spacing"

        multiples = tuple(axis.dominant_multiple for axis in gate.axes)
        if gate.phases is None:
            phase = select_cadence_phase(
                families, multiples, support,
                small.shape[1], small.shape[0],
                minimum_iou=self.minimum_iou,
            )
            if not phase.accepted or len(phase.families) != 2:
                return (), "unresolved_cadence_phase"
            selected_families = phase.families
        else:
            subsets = tuple(
                cadence_line_subsets(family, multiple)
                for family, multiple in zip(families, multiples)
            )
            if (
                type(gate.phases) is not tuple or len(gate.phases) != 2
                or len(subsets) != 2
            ):
                return (), "invalid_resolved_phase"
            if any(
                type(phase) is not int or phase < 0 or phase >= len(options)
                for options, phase in zip(subsets, gate.phases)
            ):
                return (), "invalid_resolved_phase"
            selected_families = tuple(
                options[phase]
                for options, phase in zip(subsets, gate.phases)
            )
        expected = tuple(
            float(axis.median_gap_px) * axis.dominant_multiple
            for axis in gate.axes
        )
        cells = grid_module_detections(
            selected_families, small.shape[1], small.shape[0],
            margin_px=2, expected_gaps_px=expected,
        )
        cells = filter_cells_by_finite_support(
            cells, selected_families, lines,
        )
        if not cells:
            return (), "no_finitely_supported_cells"
        if scale < 1:
            cells = tuple(
                ModuleDetection(
                    tuple((x / scale, y / scale) for x, y in d.polygon_px),
                    d.confidence, d.class_name,
                )
                for d in cells
            )
        accepted = fuse_module_detections(
            cells, support_full, minimum_iou=self.minimum_iou,
        )
        return accepted, ("spatially_supported" if accepted else "no_spatial_overlap")
