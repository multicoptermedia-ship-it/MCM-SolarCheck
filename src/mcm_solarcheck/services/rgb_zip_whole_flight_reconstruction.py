"""Private complete RGB ZIP flight -> ORB tracks -> SfM -> RTK-weighted windowed BA.

No import database, ZIP extraction, customer image copies, external executable,
ODM, GPS export or roof/orthophoto certification. A real reconstruction MUST
use all supplied source cameras or fail closed. All geometry stays in RAM.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile
import cv2
import numpy as np

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_flight_zip_series import (
    PrivateRGBFlightSeries, read_private_rgb_zip_series,
)
from mcm_solarcheck.services.rgb_rtk_camera_priors import (
    build_private_rtk_camera_priors,
)
from mcm_solarcheck.services.orthomosaic_overlap_candidates import (
    select_overlap_candidates,
)
from mcm_solarcheck.services.rgb_global_camera_network import (
    RGBNetworkFrame, RGBNetworkLink, solve_global_rgb_camera_network,
)
from mcm_solarcheck.services.rgb_sfm_link_graph_gate import (
    audit_complete_rgb_sfm_link_graph,
)
from mcm_solarcheck.services.rgb_sfm_track_support_gate import (
    audit_complete_rgb_sfm_track_support,
)
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import (
    adjust_windowed_unscaled_rgb_network,
)
from mcm_solarcheck.services.rgb_rtk_joint_bundle_adjustment import (
    PrivateRGBRTKWindowedBA, adjust_rgb_windowed_bundle_with_private_rtk,
)
from mcm_solarcheck.services.rgb_per_camera_reprojection_gate import (
    RGBPerCameraReprojectionAudit, RGBPerCameraReprojectionQualityError,
)
from mcm_solarcheck.services.rgb_multiview_parallax_gate import (
    RGBMultiviewParallaxAudit, RGBMultiviewParallaxQualityError,
)


class PrivateRGBFlightStageError(ValueError):
    """A public-safe processing stage; never embed source paths or GPS values."""

    def __init__(
        self, stage: str,
        camera_reprojection_audit: RGBPerCameraReprojectionAudit | None = None,
        multiview_parallax_audit: RGBMultiviewParallaxAudit | None = None,
    ):
        if stage not in ("intake", "calibration", "feature_extraction",
                         "overlap_matching", "global_sfm", "unscaled_ba",
                         "rtk_weighted_ba"):
            raise ValueError("unrecognized private RGB processing stage")
        if camera_reprojection_audit is not None and (
            stage != "rtk_weighted_ba" or
            not isinstance(camera_reprojection_audit, RGBPerCameraReprojectionAudit) or
            camera_reprojection_audit.cameras_above_p95_limit < 1
        ):
            raise ValueError("only failed final camera pixel audit may be attached")
        if multiview_parallax_audit is not None and (
            stage != "rtk_weighted_ba" or
            not isinstance(multiview_parallax_audit, RGBMultiviewParallaxAudit) or
            multiview_parallax_audit.privacy_safe_summary()["parallax_quality_passed"]
        ):
            raise ValueError("only failed final multiview parallax audit may be attached")
        if camera_reprojection_audit is not None and multiview_parallax_audit is not None:
            raise ValueError("only one final RGB quality failure may be reported")
        self.stage = stage
        self.camera_reprojection_audit = camera_reprojection_audit
        self.multiview_parallax_audit = multiview_parallax_audit
        super().__init__(f"whole-flight RGB {stage} gate not passed")


@dataclass(frozen=True)
class PrivateRGBFlightReconstruction:
    """Diagnostic aggregate only, no private camera/world geometry persists."""
    frame_count: int
    candidate_pair_count: int
    feature_matched_pair_count: int
    cross_strip_matched_pair_count: int
    sfm_accepted_nonadjacent_pair_count: int
    network_landmark_count: int
    sfm_reprojection_p95_px: float
    unscaled_ba_reprojection_rmse_px: float
    rtk_windowed_ba: object
    geometric_link_graph_audit: object
    required_flight_coverage_verified: bool = False
    expected_flight_frame_count: int | None = None
    sfm_rejected_conflicting_track_merges: int = 0
    sfm_accepted_geometric_feature_correspondences: int = 0
    sfm_3d_track_support_audit: object = None

    def privacy_safe_summary(self) -> dict:
        ba = self.rtk_windowed_ba.privacy_safe_summary()
        return {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_rgb_rtk_windowed_ba_candidate_not_an_orthophoto",
            "frame_count": self.frame_count,
            "candidate_pairs": self.candidate_pair_count,
            "feature_matched_pairs": self.feature_matched_pair_count,
            "cross_strip_matched_pairs": self.cross_strip_matched_pair_count,
            "cross_strip_matches_are_descriptor_only": True,
            "sfm_accepted_spatial_nonadjacent_pairs": (
                self.sfm_accepted_nonadjacent_pair_count
            ),
            "physical_cross_strip_identity_verified": False,
            **self.geometric_link_graph_audit.privacy_safe_summary(),
            **(self.sfm_3d_track_support_audit.privacy_safe_summary()
               if self.sfm_3d_track_support_audit is not None else {}),
            "sfm_track_conflicting_merges_rejected": (
                self.sfm_rejected_conflicting_track_merges
            ),
            "sfm_accepted_geometric_feature_correspondences": (
                self.sfm_accepted_geometric_feature_correspondences
            ),
            "sfm_landmarks": self.network_landmark_count,
            "sfm_reprojection_p95_px": self.sfm_reprojection_p95_px,
            "unscaled_ba_reprojection_rmse_px": self.unscaled_ba_reprojection_rmse_px,
            "rtk_windowed_ba": ba,
            "all_input_rgb_frames_processed": True,
            "required_flight_coverage_verified": (
                self.required_flight_coverage_verified
            ),
            "expected_flight_frame_count": self.expected_flight_frame_count,
            "independent_survey_verified": False,
            "roof_geometry_verified": False,
            "rgb_orthophoto_verified": False,
            "module_analysis_verified": False,
            "thermal_registration_verified": False,
        }


def _calibrated_camera(calibration: dict, series: PrivateRGBFlightSeries):
    """Same external calibration contract as existing project RGB SfM."""
    if (not isinstance(calibration, dict)
            or calibration.get("schema") != "mcm.rgb_camera_intrinsics_external.v1"
            or calibration.get("lens_calibration_verified") is not True
            or not isinstance(calibration.get("calibration_provenance"), str)
            or not calibration["calibration_provenance"].strip()):
        raise ValueError("independent calibrated lens and provenance required")
    try:
        values = calibration["intrinsics"]
        intrinsics = PinholeIntrinsics(
            *[float(values[name]) for name in ("fx", "fy", "cx", "cy")]
        )
        distortion = np.asarray(
            calibration["distortion_coefficients"], dtype=np.float64
        )
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        raise ValueError("complete external camera calibration required") from exc
    dimensions = {(f.width, f.height) for f in series.frames}
    if (len(dimensions) != 1
            or distortion.shape not in ((4,), (5,), (8,), (12,), (14,))
            or not np.isfinite(distortion).all()
            or not np.isfinite((
                intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy
            )).all()
            or min(intrinsics.fx, intrinsics.fy) <= 0):
        raise ValueError("single consistent RGB sensor calibration required")
    width, height = next(iter(dimensions))
    if not 0 <= intrinsics.cx < width or not 0 <= intrinsics.cy < height:
        raise ValueError("calibrated RGB principal point outside sensor")
    return intrinsics, distortion


def _private_rgb_overlap_pairs(frame_ids, camera_enu, *,
                               max_neighbours=10, radius_m=18.):
    """Consecutive flight pairs plus metric-nearest, nonadjacent cross-strip.

    GPS is only a candidate search heuristic, NEVER accepted match geometry.
    Avoid all-to-all 160-frame matching; every image participates in the
    consecutive graph, and spatial cross-strip connections are attempted.
    """
    count = len(frame_ids)
    if (not 12 <= count <= 1000
            or type(max_neighbours) is not int
            or not 2 <= max_neighbours <= 16
            or not np.isfinite(radius_m) or not 2 <= radius_m <= 100):
        raise ValueError("bounded complete RGB spatial-pair search required")
    xyz = np.asarray(camera_enu, dtype=np.float64)
    if xyz.shape != (count, 3) or not np.isfinite(xyz).all():
        raise ValueError("finite private camera positions required")
    cross = set()
    for i in range(count):
        d = np.linalg.norm(xyz[:, :2] - xyz[i, :2], axis=1)
        nearest = sorted(
            (j for j in range(count)
             if abs(i-j) >= 3 and .25 <= d[j] <= radius_m),
            key=lambda j: (float(d[j]), j),
        )
        for j in nearest[:max_neighbours]:
            cross.add((min(i, j), max(i, j)))
    pair_ids = tuple((frame_ids[i], frame_ids[j]) for i, j in sorted(cross))
    return select_overlap_candidates(
        frame_ids, cross_strip_pairs=pair_ids,
        max_candidates=(count-1) + count * max_neighbours,
    )


def _orb_from_private_zip(series, intrinsics, distortion, *,
                          max_side, max_features, should_cancel, on_progress):
    """Decode one JPEG at a time directly from ZIP; discard each image buffer."""
    width, height = series.frames[0].width, series.frames[0].height
    matrix = np.array((
        (intrinsics.fx, 0., intrinsics.cx),
        (0., intrinsics.fy, intrinsics.cy), (0., 0., 1.),
    ), dtype=np.float64)
    orb = cv2.ORB_create(nfeatures=max_features)
    observations, descriptors = [], []
    # Open each original ZIP/.tip once per complete feature pass, regardless
    # of frame order. ExitStack closes all read-only handles on success,
    # cancellation and failure; RGB buffers are still decoded and discarded
    # one at a time. No extraction or cross-run archive state.
    with ExitStack() as stack:
        opened: dict[Path, ZipFile] = {}
        for i, frame in enumerate(series.frames):
            if should_cancel is not None and should_cancel():
                raise RuntimeError("whole-flight RGB processing cancelled")
            archive = opened.get(frame.source_archive)
            if archive is None:
                archive = stack.enter_context(ZipFile(frame.source_archive))
                opened[frame.source_archive] = archive
            entry = archive.getinfo(frame.member_name)
            if not 128 <= entry.file_size <= 40_000_000:
                raise ValueError("original RGB member exceeds image budget")
            with archive.open(entry) as src:
                data = src.read(40_000_001)
            if len(data) != entry.file_size:
                raise ValueError("original RGB member changed since validated intake")
            image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
            del data
            if image is None or image.shape != (height, width):
                raise ValueError("unreadable primary JPEG in RGB flight")
            factor = min(1., max_side / max(width, height))
            if factor < 1.:
                image = cv2.resize(image, (
                    max(32, round(width * factor)), max(32, round(height * factor))
                ), interpolation=cv2.INTER_AREA)
            sx, sy = image.shape[1] / width, image.shape[0] / height
            scaled = matrix.copy()
            scaled[0, :] *= sx
            scaled[1, :] *= sy
            image = cv2.undistort(image, scaled, distortion, None, scaled)
            points, desc = orb.detectAndCompute(image, None)
            del image
            if desc is None or len(points) < 16:
                raise ValueError("insufficient RGB feature evidence in whole flight")
            xy = np.asarray([(p.pt[0]/sx, p.pt[1]/sy) for p in points],
                            dtype=np.float64)
            observations.append(RGBNetworkFrame(frame.frame_id, xy))
            descriptors.append(desc)
            if on_progress is not None:
                on_progress("features", i+1, len(series.frames))
    return tuple(observations), descriptors


def _check_expected_rgb_flight(
    series: PrivateRGBFlightSeries, *,
    expected_frame_count: int | None,
    expected_archive_count: int | None,
    first_counter: int,
) -> bool:
    """Compare already-indexed camera identities to exact user-expected flight.

    No additional archive or image read. Refuse incomplete ZIP sets, gaps,
    substitutions or reordered/duplicate IDs before expensive ORB/SfM.
    """
    if (type(first_counter) is not int or not 0 <= first_counter <= 9999):
        raise ValueError("bounded RGB counter start required")
    if (expected_frame_count is None) != (expected_archive_count is None):
        raise ValueError("whole-flight frame and archive counts required together")
    if expected_frame_count is None:
        return False
    if (type(expected_frame_count) is not int or
            not 12 <= expected_frame_count <= 1000 or
            first_counter + expected_frame_count > 10000 or
            type(expected_archive_count) is not int or
            not 1 <= expected_archive_count <= 32):
        raise ValueError("bounded explicit complete RGB flight expectation required")
    expected_ids = tuple(
        f"V-{number:04d}"
        for number in range(first_counter, first_counter + expected_frame_count)
    )
    if (len(series.frames) != expected_frame_count or
            series.archives_read != expected_archive_count or
            tuple(f.frame_id for f in series.frames) != expected_ids or
            len({f.source_archive for f in series.frames}) != expected_archive_count):
        raise ValueError("complete RGB flight archive/count/counter gate failed")
    return True


def reconstruct_private_complete_rgb_zip_flight(
    archives: tuple[str | Path, ...],
    calibration: dict,
    *,
    max_side: int = 1200,
    max_features: int = 1600,
    max_neighbours: int = 10,
    expected_frame_count: int | None = None,
    expected_archive_count: int | None = None,
    first_counter: int = 1,
    should_cancel=None,
    on_progress=None,
) -> PrivateRGBFlightReconstruction:
    """Complete ZIP->SfM->window BA->GNSS BA, no file writes at any stage.

    Failed geometry is reported as a stage failure; never silently select a
    'good' flight strip or export an optical 2D stitch as an orthophoto.
    """
    stage = "intake"
    try:
        series = read_private_rgb_zip_series(
            archives, should_cancel=should_cancel,
        )
        exact_coverage = _check_expected_rgb_flight(
            series,
            expected_frame_count=expected_frame_count,
            expected_archive_count=expected_archive_count,
            first_counter=first_counter,
        )
        ids = tuple(frame.frame_id for frame in series.frames)
        if len(ids) < 12:
            raise ValueError("12+ cameras required for whole-flight RTK BA")
        stage = "calibration"
        intrinsics, distortion = _calibrated_camera(calibration, series)
        priors = build_private_rtk_camera_priors(
            series, ids, should_cancel=should_cancel,
        )
        if (type(max_side) is not int or not 256 <= max_side <= 2400
                or type(max_features) is not int or not 300 <= max_features <= 4000):
            raise ValueError("bounded RGB feature budgets required")
        stage = "feature_extraction"
        observations, descriptors = _orb_from_private_zip(
            series, intrinsics, distortion,
            max_side=max_side, max_features=max_features,
            should_cancel=should_cancel, on_progress=on_progress,
        )
        stage = "overlap_matching"
        candidates = _private_rgb_overlap_pairs(
            ids, priors.camera_enu_m, max_neighbours=max_neighbours,
        )
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        links, across = [], 0
        ids_to_indices = {fid: i for i, fid in enumerate(ids)}
        for pair_index, pair in enumerate(candidates):
            if should_cancel is not None and should_cancel():
                raise RuntimeError("whole-flight RGB processing cancelled")
            a = ids_to_indices[pair.first_id]
            b = ids_to_indices[pair.second_id]
            raw = matcher.match(descriptors[a], descriptors[b])
            chosen = sorted((m for m in raw if m.distance <= 64),
                            key=lambda m: m.distance)
            if len(chosen) >= 12:
                links.append(RGBNetworkLink(
                    pair.first_id, pair.second_id,
                    np.asarray([(m.queryIdx, m.trainIdx) for m in chosen],
                               dtype=np.int32),
                ))
                if pair.reason == "cross_strip":
                    across += 1
            if on_progress is not None:
                on_progress("matches", pair_index+1, len(candidates))
        if across == 0:
            raise ValueError("no cross-strip matching evidence for RGB flight")
        stage = "global_sfm"
        network = solve_global_rgb_camera_network(
            observations, tuple(links), intrinsics,
            max_track_count=60000, should_cancel=should_cancel,
        )
        if network.frame_ids != ids or len(network.world_to_camera) != len(ids):
            raise ValueError("SfM did not reconstruct every RGB image")
        # Audit ALL calibrated RANSAC/pose links, not only descriptor matches.
        # GNSS-near nonadjacent pairs remain flight-strip CANDIDATES.
        audit = audit_complete_rgb_sfm_link_graph(
            ids,
            tuple((p.first_id, p.second_id) for p in links),
            tuple(network.accepted_link_pairs),
            tuple((p.first_id, p.second_id) for p in candidates
                  if p.reason == "cross_strip"),
        )
        actual_count = audit.spatial_nonadjacent_geometric_pairs
        # Essential-matrix pair links do not themselves prove that global
        # triangulation kept genuine shared 3D points on those same edges.
        track_audit = audit_complete_rgb_sfm_track_support(
            ids, tuple(network.accepted_link_pairs),
            tuple((p.first_id, p.second_id) for p in candidates
                  if p.reason == "cross_strip"),
            network.observation_frame_indices,
            network.observation_landmark_indices,
            landmark_count=len(network.landmark_xyz_unit_baseline),
            should_cancel=should_cancel,
        )
        stage = "unscaled_ba"
        unscaled = adjust_windowed_unscaled_rgb_network(
            network, intrinsics, max_landmarks_total=200000,
            max_observations_total=800000, should_cancel=should_cancel,
        )
        stage = "rtk_weighted_ba"
        metric = adjust_rgb_windowed_bundle_with_private_rtk(
            network, unscaled, priors, intrinsics,
            enforce_camera_p95=True, enforce_parallax=True,
            windowed_options={
                "max_landmarks_total": 200000,
                "max_observations_total": 800000,
            }, should_cancel=should_cancel,
        )
        if metric.total_cameras != len(ids):
            raise ValueError("RTK BA omitted at least one flight image")
        return PrivateRGBFlightReconstruction(
            len(ids), len(candidates), len(links), across, actual_count,
            network.reconstructed_landmarks, network.reprojection_p95_px,
            unscaled.after_rmse_px, metric, audit,
            exact_coverage, expected_frame_count,
            network.rejected_conflicting_track_merges,
            network.accepted_geometric_feature_correspondences,
            track_audit,
        )
    except RGBPerCameraReprojectionQualityError as exc:
        raise PrivateRGBFlightStageError(
            stage, camera_reprojection_audit=exc.audit,
        ) from None
    except RGBMultiviewParallaxQualityError as exc:
        raise PrivateRGBFlightStageError(
            stage, multiview_parallax_audit=exc.audit,
        ) from None
    except (ValueError, TypeError, KeyError, IndexError, cv2.error):
        raise PrivateRGBFlightStageError(stage) from None


def render_private_pitched_preview_from_original_rgb_archives(
    archives: tuple[str | Path, ...],
    calibration: dict,
    metric_candidate: PrivateRGBRTKWindowedBA,
    candidate_index: int,
    camera_indices: tuple[int, ...],
    *,
    meters_per_pixel: float = .05,
    max_side: int = 1024,
    occluder_planes=None,
    source_fusion: str = "mean",
    should_cancel=None,
    _series: PrivateRGBFlightSeries | None = None,
    _source_cache: OrderedDict[int, np.ndarray] | None = None,
):
    """Private *opt-in* ZIP JPEG -> undistort -> pitched 3D RGB raster preview.

    Caller reuses the completed private RTK BA object (with its private plane
    hypotheses), never infers poses from DJI EXIF/Gimbal. Source ZIP/.tip
    archives and JPEG members are READ ONLY. No output/image serialization.
    Only selected cameras are decoded, bounded to 2..8 private images.
    During ONE multi-facet render a bounded RAM-only LRU can reuse at most
    four undistorted source JPEGs; it never persists private images.
    """
    if (not isinstance(metric_candidate, PrivateRGBRTKWindowedBA)
            or type(camera_indices) is not tuple
            or not 2 <= len(camera_indices) <= 8
            or len(set(camera_indices)) != len(camera_indices)
            or any(type(i) is not int or i < 0
                   or i >= metric_candidate.total_cameras for i in camera_indices)):
        raise ValueError("complete RTK BA and unique private preview cameras required")
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private RGB orthopatch ZIP decoding cancelled")
    if (_series is not None and not isinstance(_series, PrivateRGBFlightSeries)
            or _source_cache is not None
            and (_series is None or not isinstance(_source_cache, OrderedDict))):
        raise ValueError("private RGB source reuse requires matching in-memory series")
    flight = (_series if _series is not None else read_private_rgb_zip_series(
        archives, should_cancel=should_cancel,
    ))
    ids = tuple(frame.frame_id for frame in flight.frames)
    if (ids != metric_candidate.frame_ids
            or len(ids) != metric_candidate.total_cameras):
        raise ValueError("private RGB source identities differ from fitted 3D cameras")
    k, distortion = _calibrated_camera(calibration, flight)
    matrix = np.array((
        (k.fx, 0., k.cx),
        (0., k.fy, k.cy),
        (0., 0., 1.),
    ), dtype=np.float64)
    images = []
    for i in camera_indices:
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private RGB orthopatch ZIP decoding cancelled")
        if _source_cache is not None and i in _source_cache:
            # Reuse only in the SAME validated whole-flight composition.
            # LRU eviction never mutates an image already used by a facet.
            image = _source_cache.pop(i)
            _source_cache[i] = image
            images.append(image)
            continue
        frame = flight.frames[i]
        with ZipFile(frame.source_archive) as archive:
            entry = archive.getinfo(frame.member_name)
            if not 128 <= entry.file_size <= 40_000_000:
                raise ValueError("original RGB member exceeds preview budget")
            with archive.open(entry) as source:
                encoded = source.read(40_000_001)
            if len(encoded) != entry.file_size:
                raise ValueError("original RGB JPEG changed since flight intake")
        bgr = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
        del encoded
        if bgr is None or bgr.shape != (frame.height, frame.width, 3):
            raise ValueError("unreadable original calibrated RGB JPEG")
        # Feature SfM pixels are in UNDISTORTED full-resolution sensor K.
        # Apply the exact same K/distortion convention on the RGB preview.
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        del bgr
        undistorted = cv2.undistort(rgb, matrix, distortion, None, matrix)
        del rgb
        undistorted.setflags(write=False)
        images.append(undistorted)
        if _source_cache is not None:
            _source_cache[i] = undistorted
            # Four full-resolution DJI RGB images are already ~144 MiB.
            # Do not retain all 160 sources or even all 8 from every facet.
            while len(_source_cache) > 4:
                _source_cache.popitem(last=False)
    return metric_candidate.render_private_pitched_plane_preview(
        candidate_index, tuple(images), camera_indices, k,
        meters_per_pixel=meters_per_pixel, max_side=max_side,
        occluder_planes=occluder_planes,
        source_fusion=source_fusion,
        should_cancel=should_cancel,
    )


def render_private_multiplane_preview_from_original_rgb_archives(
    archives: tuple[str | Path, ...],
    calibration: dict,
    metric_candidate: PrivateRGBRTKWindowedBA,
    *,
    meters_per_pixel: float = .05,
    max_side: int = 1024,
    max_cameras_per_plane: int = 8,
    should_cancel=None,
):
    """Opt-in private ZIP -> automatically selected RGB -> multiple pitch facets.

    Selection uses all final metric BA poses and each *private* plane footprint,
    not arbitrary flight counter ranges or descriptor-only links. Each chosen
    camera's original JPEG is decoded directly from the read-only ZIP and
    undistorted in RAM by the existing verified single-plane helper.
    Individual patches are placed on one common metric ENU grid. No files.
    One already validated source-series index and a four-image RAM-only LRU
    are reused across facets; this does NOT bypass the calibration and BA
    frame-identity checks. Still bounded to six facets and at most eight
    cameras per facet, NOT a full-roof orthophoto or visibility solution.
    """
    from mcm_solarcheck.services.rgb_private_multi_plane_preview import (
        choose_private_pitched_plane_cameras,
        compose_private_pitched_rgb_orthopatches,
    )
    if (not isinstance(metric_candidate, PrivateRGBRTKWindowedBA)
            or metric_candidate.pitched_plane_candidates is None
            or not 2 <= len(metric_candidate.pitched_plane_candidates.planes_private) <= 6
            or metric_candidate.camera_reprojection_audit is None
            or metric_candidate.camera_reprojection_audit.cameras_above_p95_limit
            or metric_candidate.multiview_parallax_audit is None
            or not metric_candidate.multiview_parallax_audit.privacy_safe_summary()[
                "parallax_quality_passed"
            ]):
        raise ValueError("valid private multi-plane RTK BA preview source required")
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private RGB multi-plane ZIP preview cancelled")
    series = read_private_rgb_zip_series(archives, should_cancel=should_cancel)
    ids = tuple(f.frame_id for f in series.frames)
    if (ids != metric_candidate.frame_ids
            or len(ids) != metric_candidate.total_cameras):
        raise ValueError("private RGB source identities differ from fitted 3D cameras")
    intrinsics, _ = _calibrated_camera(calibration, series)
    width, height = series.frames[0].width, series.frames[0].height
    planes = metric_candidate.pitched_plane_candidates.planes_private
    patches = []
    source_cache: OrderedDict[int, np.ndarray] = OrderedDict()
    for candidate_index, plane in enumerate(planes):
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private RGB multi-plane ZIP preview cancelled")
        selected = choose_private_pitched_plane_cameras(
            plane, metric_candidate.world_enu_to_camera_private,
            intrinsics, width, height,
            max_cameras=max_cameras_per_plane,
            occluder_planes=tuple(
                other for j, other in enumerate(planes) if j != candidate_index
            ),
            should_cancel=should_cancel,
        )
        patches.append(render_private_pitched_preview_from_original_rgb_archives(
            archives, calibration, metric_candidate, candidate_index, selected,
            meters_per_pixel=meters_per_pixel,
            max_side=max_side,
            occluder_planes=tuple(
                other for j, other in enumerate(planes) if j != candidate_index
            ),
            source_fusion="priority_overlap",
            should_cancel=should_cancel,
            _series=series, _source_cache=source_cache,
        ))
    # Drop held full-resolution image references before composing patches.
    source_cache.clear()
    return compose_private_pitched_rgb_orthopatches(
        planes, tuple(patches), max_side=max_side,
        should_cancel=should_cancel,
    )
