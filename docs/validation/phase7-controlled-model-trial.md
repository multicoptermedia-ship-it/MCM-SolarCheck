# Phase 7 controlled external-model trial

This trial is deliberately separated from customer-project authorization.

## Candidate

PV-HSD-2025 `yolov8s-p1` is registered as a thermal validation candidate.
Its recorded weight digest is immutable in the model candidate manifest. The
upstream usage restriction means it is **not approved for commercial/customer
use** without documented permission.

## Input boundary

A model trial must declare the image representation it consumes. MCM-SolarCheck
does not pass a radiometric temperature matrix directly into a model trained on
rendered imagery. The current accepted representations are `rendered_rgb` and
`grayscale_8bit`; the exact expected representation must match before
inference.

This prevents two errors: treating raw radiometric values as ordinary image
pixels, and silently changing the model's preprocessing contract.

## Trial sequence

1. Obtain the exact upstream weight artifact without committing it to Git.
2. Verify SHA-256 before model construction.
3. Record backend and preprocessing contract.
4. Select representative Mavic 3T thermal frames and module crops.
5. Run inference as advisory evidence only.
6. Human-review the reference defects and false positives.
7. Evaluate the resulting validation summary against the M3T acceptance policy.
8. Keep customer-project authorization disabled unless commercial rights are
   independently documented.

No trial result may convert a model suggestion into a confirmed diagnosis.
