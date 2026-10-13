# Offline pilot PDF with image evidence

The local pilot PDF now supports optional reviewed RGB and thermal image evidence per finding, labelled with source frame IDs and geometry provenance. The images are embedded into the PDF from existing local files; they are not uploaded or transmitted by this exporter.

Use `local_pilot_evidence(reviewed_inspection)` and `from_reviewed_inspection(reviewed_inspection, limitations="...")`, then `export_pilot_pdf(pilot, path, evidence=evidence)`.

The renderer checks JPEG/PNG decoding and bounds pixel count. Missing or symlinked local files fail rather than silently substituting a different image. The existing module assignment remains expert-reviewed, but geometry provenance such as `full_frame` is not a verified module polygon or orthomosaic location. Image presence does not establish radiometric calibration or diagnosis. Customer review and authorization remain mandatory.
