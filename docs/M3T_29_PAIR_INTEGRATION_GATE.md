# DJI M3T: 29-pair local integration gate

The uploaded ZIPs contain 36 thermal and 29 visible images. The user confirmed the mismatch is caused by chat upload size limits, not a missing flight capture. The current scope is sequences 0001–0029 only.

The structural APP3 check of all 29 selected thermal images succeeded locally. This is not evidence of calibrated Celsius values or verified PV defects. The full importer, metadata-based matching, candidate counts, and quality grades must be measured independently.

Run locally from a checkout with the original archives available:

```bash
PYTHONPATH=src python -m mcm_solarcheck.services.m3t_local_smoke_test /path/to/thermal3.zip /path/to/vis3.zip
```

The command stages only 58 selected files in a temporary directory, prints counts (no coordinates), and fails closed on import or pairing errors. Do not upload original imagery or location metadata to GitHub, CI, or IONOS.
