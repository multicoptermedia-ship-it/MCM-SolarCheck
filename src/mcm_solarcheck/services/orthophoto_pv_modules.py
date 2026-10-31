"""Existing PV detector on bounded RGB windows, mapped to a thermal GeoTIFF.

This adapter reads existing local orthophotos. It neither reconstructs images
nor interprets thermal pixel values as temperatures. GIS correspondence is a
proposal for human review, not proof of physical sensor registration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor

import numpy as np
import rasterio
from pyproj import Transformer
from pyproj.exceptions import ProjError
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.windows import Window

from mcm_solarcheck.services.orthophoto_layer_alignment import (
    inspect_orthophoto_layer_pair,
)
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_quality import filter_module_detections
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector


_THERMAL_PIXEL_BUDGET = 1_000_000


@dataclass(frozen=True)
class OrthophotoPVModuleProposal:
    """Private native pixel coordinates, without database or module approval."""

    rgb_polygon_px: tuple[tuple[float, float], ...] = field(repr=False)
    thermal_polygon_px: tuple[tuple[float, float], ...] = field(repr=False)
    confidence: float
    thermal_valid_coverage: float
    thermal_valid_pixel_count: int
    thermal_polygon_sample_count: int
    review_status: str = field(default="pending", init=False)
    module_analysis_verified: bool = field(default=False, init=False)
    geometric_registration_verified: bool = field(default=False, init=False)
    thermal_calibration_verified: bool = field(default=False, init=False)


@dataclass(frozen=True)
class OrthophotoPVWindowResult:
    proposals: tuple[OrthophotoPVModuleProposal, ...] = field(repr=False)
    rgb_window: tuple[int, int, int, int] = field(repr=False)
    detector_name: str = field(repr=False)
    rejected_rgb_nodata_count: int = 0

    def summary(self) -> dict:
        """Aggregate only: no paths, native coordinates or thermal values."""
        coverage = tuple(p.thermal_valid_coverage for p in self.proposals)
        return {
            "schema": "mcm.orthophoto_pv_window_proposals.v1",
            "status": "pending_module_review",
            "module_proposal_count": len(self.proposals),
            "proposals_with_thermal_coverage": sum(c > 0 for c in coverage),
            "proposals_without_thermal_coverage": sum(c == 0 for c in coverage),
            "proposals_with_partial_thermal_coverage": sum(0 < c < 1 for c in coverage),
            "minimum_thermal_valid_coverage": min(coverage, default=0.),
            "rejected_rgb_nodata_count": self.rejected_rgb_nodata_count,
            "module_analysis_verified": False,
            "geometric_registration_verified": False,
            "thermal_calibration_verified": False,
            "thermal_values_interpreted": False,
        }


def _cancel(should_cancel):
    if should_cancel is not None and should_cancel():
        raise RuntimeError("orthophoto PV detection cancelled")


def _polygon_mask(polygon, *, width, height, left=0, top=0):
    ring = [tuple(point) for point in polygon]
    return geometry_mask(
        [{"type": "Polygon", "coordinates": [ring + [ring[0]]]}],
        out_shape=(height, width), transform=Affine.translation(left, top),
        invert=True,
    )


def _map_polygon(polygon, rgb_transform, thermal_transform, transformer):
    # Densify straight RGB edges before a potentially nonlinear CRS transform;
    # keep a bounded number of points for local module footprints.
    samples = []
    for first, second in zip(polygon, polygon[1:] + polygon[:1]):
        a, b = np.asarray(first), np.asarray(second)
        steps = min(64, max(4, ceil(float(np.linalg.norm(b-a))/32.)))
        samples.extend(a + (b-a)*fraction for fraction in np.arange(steps)/steps)
    samples = np.asarray(samples)
    world = np.column_stack((
        rgb_transform.a*samples[:, 0] + rgb_transform.b*samples[:, 1] + rgb_transform.c,
        rgb_transform.d*samples[:, 0] + rgb_transform.e*samples[:, 1] + rgb_transform.f,
    ))
    try:
        x, y = transformer.transform(world[:, 0], world[:, 1], errcheck=True)
    except ProjError:
        raise ValueError("module polygon cannot be transformed between orthophoto CRS") from None
    inverse = ~thermal_transform
    mapped = tuple((float(inverse.a*xx + inverse.b*yy + inverse.c),
                    float(inverse.d*xx + inverse.e*yy + inverse.f)) for xx, yy in zip(x, y))
    if not np.isfinite(mapped).all():
        raise ValueError("finite transformed thermal module polygon required")
    return mapped


def _thermal_coverage(dataset, polygon, bands, should_cancel):
    xy = np.asarray(polygon)
    left, top = floor(float(xy[:, 0].min())), floor(float(xy[:, 1].min()))
    right, bottom = ceil(float(xy[:, 0].max())), ceil(float(xy[:, 1].max()))
    width, height = right-left, bottom-top
    if width < 1 or height < 1:
        return 0., 0, 0
    if width*height > _THERMAL_PIXEL_BUDGET:
        raise ValueError("thermal module footprint exceeds bounded pixel budget")
    footprint = _polygon_mask(polygon, width=width, height=height, left=left, top=top)
    total = int(np.count_nonzero(footprint))
    if not total:
        return 0., 0, 0
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(dataset.width, right), min(dataset.height, bottom)
    if x0 >= x1 or y0 >= y1:
        return 0., 0, total
    _cancel(should_cancel)
    native_window = Window(x0, y0, x1-x0, y1-y0)
    # Dataset masks include alpha and explicit GDAL masks. Finite-value checks
    # additionally exclude NaNs even when NoData metadata uses a finite sentinel.
    values = dataset.read(bands, window=native_window)
    valid = dataset.dataset_mask(window=native_window) > 0
    valid &= np.all(dataset.read_masks(bands, window=native_window) > 0, axis=0)
    valid &= np.isfinite(values).all(axis=0)
    for layer, band in zip(values, bands):
        nodata = dataset.nodatavals[band-1]
        if nodata is not None:
            # Explicit GDAL masks can override generated NoData masks.
            valid &= layer != nodata
    for index, color in enumerate(dataset.colorinterp, 1):
        if color == rasterio.enums.ColorInterp.alpha:
            valid &= dataset.read(index, window=native_window) > 0
    selected = footprint[y0-top:y1-top, x0-left:x1-left]
    covered = int(np.count_nonzero(valid & selected))
    return covered/total, covered, total


def detect_orthophoto_pv_window(
    rgb_path, thermal_path, *, window, detector=None, should_cancel=None,
) -> OrthophotoPVWindowResult:
    """Reuse the PV detector without resizing a bounded, original-resolution ROI.

    ``window`` is ``(column, row, width, height)`` in native RGB pixels. Native
    pixel coordinates use the continuous raster image plane, transformed by
    each GeoTIFF's declared affine and CRS. No temperature unit is inferred.
    Proposals overlapping RGB NoData are rejected; thermal gaps lower coverage.
    """
    _cancel(should_cancel)
    if (type(window) is not tuple or len(window) != 4
            or any(type(value) is not int for value in window)
            or min(window[:2]) < 0 or not all(1 <= value <= 2048 for value in window[2:])):
        raise ValueError("bounded integer RGB window (column, row, width, height) required")
    pair = inspect_orthophoto_layer_pair(rgb_path, thermal_path)
    col, row, width, height = window
    with rasterio.open(pair.rgb_path) as rgb, rasterio.open(pair.thermal_path) as thermal:
        if (rgb.count < 3 or any(rgb.dtypes[i-1] != "uint8" for i in pair.rgb_bands)
                or not 1 <= thermal.count <= 4):
            raise ValueError("uint8 RGB bands and one to four thermal raster bands required")
        if col+width > rgb.width or row+height > rgb.height:
            raise ValueError("RGB detection window must remain inside its native raster")
        region = Window(col, row, width, height)
        channels = rgb.read(pair.rgb_bands, window=region)
        valid = rgb.dataset_mask(window=region) > 0
        valid &= np.all(rgb.read_masks(pair.rgb_bands, window=region) > 0, axis=0)
        for layer, band in zip(channels, pair.rgb_bands):
            nodata = rgb.nodatavals[band-1]
            if nodata is not None:
                valid &= layer != nodata
        for index, color in enumerate(rgb.colorinterp, 1):
            if color == rasterio.enums.ColorInterp.alpha:
                valid &= rgb.read(index, window=region) > 0
        bgr = np.ascontiguousarray(np.moveaxis(channels, 0, -1)[:, :, ::-1])
        bgr[~valid] = 255
        _cancel(should_cancel)
        selected_detector = detector if detector is not None else OpenCVModuleDetector(
            max_dimension=max(width, height),
        )
        if not callable(getattr(selected_detector, "detect_array", None)):
            raise ValueError("an in-memory PV module detector is required")
        raw = selected_detector.detect_array(bgr)
        if (not isinstance(raw, (tuple, list)) or len(raw) > 2000
                or any(not isinstance(item, ModuleDetection) for item in raw)):
            raise ValueError("bounded typed PV module detections required")
        detections = filter_module_detections(tuple(raw), width, height)
        transformer = Transformer.from_crs(rgb.crs, thermal.crs, always_xy=True)
        proposals, rejected = [], 0
        for detection in detections:
            _cancel(should_cancel)
            local = detection.polygon_px
            xy = np.asarray(local)
            left, top = np.floor(xy.min(axis=0)).astype(int)
            right, bottom = np.ceil(xy.max(axis=0)).astype(int)
            # Rasterize only each module's bounding box, not a full 2048²
            # detection window for every proposal in a dense installation.
            mask = _polygon_mask(local, width=right-left, height=bottom-top,
                                 left=left, top=top)
            if not mask.any() or np.any(mask & ~valid[top:bottom, left:right]):
                rejected += 1
                continue
            global_polygon = tuple((float(x+col), float(y+row)) for x, y in local)
            thermal_polygon = _map_polygon(
                global_polygon, rgb.transform, thermal.transform, transformer,
            )
            coverage, count, total = _thermal_coverage(
                thermal, thermal_polygon, pair.thermal_bands, should_cancel,
            )
            proposals.append(OrthophotoPVModuleProposal(
                global_polygon, thermal_polygon, float(detection.confidence),
                coverage, count, total,
            ))
    _cancel(should_cancel)
    return OrthophotoPVWindowResult(
        tuple(proposals), window, str(getattr(selected_detector, "name", "external_detector")), rejected,
    )
