# Module-plane reconstruction policy

Pilot aims camera approximately perpendicular to PV module surfaces; future flight-planning automation is out of scope. DJI XMP GimbalPitchDegree, GimbalRollDegree and GimbalYawDegree describe camera orientation, **not** incidence relative to a sloped module. Do not infer roof slope from camera pitch.

Ground-mount modules are often tilted 20–30 degrees, per operator field guidance. Rooftops can have multiple independent planes. A horizontal map orthomosaic is useful for overview but may distort sloped modules; a separate rectified module-plane view is needed for inspection. Each plane needs measured or reconstructed tilt and azimuth, confidence and provenance.

Use existing importer Pose fields from XMP; do not reparse JPEG metadata. Reject missing/nonfinite pose for geometry readiness; report diagnostics without pretending reconstruction succeeded. Pair registration, camera calibration, overlap, reconstruction and radiometric validation are separate gates. Thermal palette orthophoto is visualization, not Celsius. Preserve raw radiometric data separately. No photos or metadata with GPS should be committed.
