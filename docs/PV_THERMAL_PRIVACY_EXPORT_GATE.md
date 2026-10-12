# Thermal training export requirements

DJI M3T thermal JPEG contains radiometric APP3 data. Converting it through Pillow RGB loses raw values. A later exporter must use the validated radiometric parser, crop raw raster coordinates, and produce a metadata-free derivative while retaining calibration evidence privately. Never infer Celsius from uncalibrated raw data.

Require active opt-in, expert confirmation that only modules appear, bounded outputs, separate project grouping and revocation tracing. This block adds a local SQLite consent ledger and a consent-gated RGB exporter, not a thermal exporter. Existing exports cannot yet be automatically deleted on withdrawal; build a protected export inventory before production use. No cloud transfer or training is performed.
