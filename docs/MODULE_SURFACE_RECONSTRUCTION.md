# Module-plane reconstruction policy

Pilot aims camera approximately perpendicular to PV module surfaces; future flight-planning automation is out of scope. DJI XMP GimbalPitchDegree, GimbalRollDegree and GimbalYawDegree describe camera orientation, **not** incidence relative to a sloped module. Do not infer roof slope from camera pitch.

Ground-mount modules are often tilted 20–30 degrees, per operator field guidance. Rooftops can have multiple independent planes. A horizontal map orthomosaic is useful for overview but may distort sloped modules; a separate rectified module-plane view is needed for inspection. Each plane needs measured or reconstructed tilt and azimuth, confidence and provenance.

Use existing importer Pose fields from XMP; do not reparse JPEG metadata. Reject missing/nonfinite pose for geometry readiness; report diagnostics without pretending reconstruction succeeded. Pair registration, camera calibration, overlap, reconstruction and radiometric validation are separate gates. Thermal palette orthophoto is visualization, not Celsius. Preserve raw radiometric data separately. No photos or metadata with GPS should be committed.

## Implementation checkpoint: orientation readiness (2026-10-15)

`services/module_plane_geometry_readiness.py` defines `CameraOrientation`, `ModulePlane` and `assess_module_plane_geometry`. It checks finite pitch/roll/yaw and separately established module tilt/azimuth, provenance and confidence. `metadata_complete=True` only means these inputs are present and within configured bounds; **`ready_for_reconstruction` remains false** until independent camera calibration, reference-frame conventions, control-point accuracy, overlap and geometry checks exist. DJI pose values must be obtained from the existing importer Pose fields in future integration; this module does not reparse images. Do not infer incidence angle or roof slope from gimbal pitch, or claim that a planar homography alone validates a tilted roof orthophoto.

## Calibrated camera-ray to inclined module plane (2026-10-17)

`services/module_plane_projection.py` now computes **geometric ray intersections only** in explicitly defined local metric ENU (east/north/up) coordinates. Camera coordinates are x-right, y-down, z-forward, and the supplied proper orthonormal `camera_to_enu` matrix transforms camera rays into ENU. Intrinsics are calibrated pinhole fx/fy/cx/cy and input pixel coordinates must already be lens-undistorted. A surveyed plane is given by an ENU point and unit normal; invalid rotations, parallel rays, behind-camera intersections and nonfinite inputs fail closed. This is not a DJI GimbalPitch/Roll/Yaw to ENU conversion, and no such mapping should be guessed. Neither measured plane geometry, lens calibration, absolute georeferencing, DEM, image warping nor photogrammetric verification is supplied by this module. Synthetic tests validate the math, not field accuracy.
