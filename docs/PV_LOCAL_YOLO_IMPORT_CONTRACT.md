# Local YOLO dataset inspection contract

Input is a user-provided, already extracted local directory. No network requests, image upload, training or model downloads. Review commercial licensing separately and record a human decision in PublicDatasetRecord before declaring a dataset eligible.

Supported initial format: YOLO detection labels (one class and normalized xywh per line), matching local RGB JPEG/PNG images, explicit source-class-to-observable-signature mapping, and flight/site group IDs. Do not infer electrical fault diagnoses from RGB appearance. EL is reserved for v2.

Inspection is read-only. Restrict traversal and symlinks, cap file counts, bytes and image sizes, validate each annotation and reject missing image/label pairs. Validate train/val/test by site or flight before training. Report sanitized counts and errors, never image contents.
