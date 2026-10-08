# Commercialization and licensing release gate

This checklist is a technical release gate, not a statement that any third-party
license permits commercial use. Evidence must be reviewed for the exact version
and intended distribution before a customer build is released.

## MCM-owned product

- [ ] Choose and approve the MCM-SolarCheck application license/EULA.
- [ ] Record copyright ownership and contributor rights for shipped source/assets.
- [ ] Define customer ownership/export of project, RGB, thermal and inspection data.
- [ ] Document activation/update behavior without locking customer project data.

## Dependencies and runtime

- [ ] Generate a version-pinned dependency inventory for the customer build.
- [ ] Review each dependency license and required notices/attribution.
- [ ] Re-check Ultralytics terms for the exact backend/version and commercial use.
- [ ] Review GDAL/rasterio/OpenCV/Pillow/PySide and document-generation dependencies.
- [ ] Keep optional components optional where their license would alter distribution.

## Models, weights and datasets

- [ ] Record dataset source, terms and rights evidence for every trained model.
- [ ] Record rights to train, modify, use commercially and redistribute weights separately.
- [ ] Do not ship external/pretrained weights until redistribution rights are verified.
- [ ] Require the ModelPackageManifest distribution-rights gate before packaging weights.
- [ ] Preserve dataset/snapshot/training/evaluation/release/weight provenance.
- [ ] Keep machine suggestions advisory; customer reports require human review.

## Maps, imagery and UI assets

- [ ] Review satellite/basemap provider terms for desktop use, caching and attribution.
- [ ] Keep basemap tiles out of generated reports unless separately licensed.
- [ ] Review icons, fonts, sample imagery and other bundled assets.
- [ ] Implement WebODM-like workflow independently; do not copy protected assets/code
      except where the applicable license explicitly permits the intended use.

## Customer release evidence

- [ ] Archive the exact dependency/model/license inventory with each release.
- [ ] Include required third-party notices and attribution.
- [ ] Confirm representative M3T validation is independent from training data.
- [ ] Confirm model-package weights SHA-256 matches the approved release.
- [ ] Record the person/date approving commercial distribution rights.

A customer/commercial release is blocked while any applicable item above remains
unverified. Technical Phase 8 completion does not itself satisfy this gate.
