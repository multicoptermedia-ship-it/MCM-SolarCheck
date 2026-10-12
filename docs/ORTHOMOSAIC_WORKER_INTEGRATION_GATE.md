# Next integration gate: actual orthomosaic worker

The reconstruction plan is **metadata only**. It does not generate an orthomosaic, verify image overlap, establish a camera-to-module angle, or guarantee successful photogrammetry.

Before any real viewer manifest is published:
1. Load original photos locally or in explicitly authorized secure compute storage; never commit photos.
2. Calibrate RGB and thermal intrinsics and camera-to-camera extrinsics; confirm matched capture timing.
3. Reconstruct sufficient camera geometry and a coordinate frame per roof/module plane. Verify image overlap, reprojection residuals and coverage.
4. Rectify RGB and thermal into the same pixel grid; measure and threshold cross-sensor registration error.
5. Preserve radiometric raster and temperature calibration provenance separately from colorized thermal output.
6. Issue only authorized, same-origin, project-scoped image URLs to the shared viewer. Do not display unverified overlays.
7. If a plane cannot be reconstructed reliably, provide paired-source-image review instead of a fabricated orthomosaic.

Pilot controls the camera incidence during current missions; future flight-planning software can automate gimbal/route settings. No cloud deployment or paid processing is authorized by this documentation.
