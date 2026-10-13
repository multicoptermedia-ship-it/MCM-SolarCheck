# Next: opt-in training registry and thermal-safe extraction

Milestone 23 adds a local RGB-only crop export gated on explicit recorded consent and human confirmations. It decodes source pixels and writes a new random-name PNG with no source metadata, then checks the output. The reviewer must ensure only solar modules are visible. **This does not establish legal anonymization**: pixel content and separately retained consent/project mappings can permit re-identification.

No radiometric thermal JPEG export is supported. Future work must extract validated thermal pixel arrays without copying source EXIF/XMP, preserve original APP3 data only in the protected project, document radiometric calibration, and assess whether derived temperature arrays carry identifying content. Implement revocation and retention tracking in a separate protected database, site/flight grouping for evaluation, content scanning and privacy impact review. Do not use images for training without a lawful basis and valid consent policy.

No original images uploaded, no customer project data committed, no AI training, no IONOS access.
