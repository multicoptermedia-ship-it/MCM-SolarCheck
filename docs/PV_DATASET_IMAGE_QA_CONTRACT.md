# Local PV training dataset quality gates

Inspect only user-provided local RGB/thermal JPEG/PNG files. Image content is never uploaded, committed or automatically used for training. Check real image decoding, dimensions, pixel count and compressed file size. Colorized thermal JPEG is **not** radiometric temperature data.

For YOLO detection datasets, require a one-to-one pairing of image and .txt annotation by basename; an empty label is an intentional negative example. Require source-provided site/flight IDs for train, val and test. Group leakage is a hard failure; filenames alone do not establish independence.

A positive preliminary gate additionally requires human-reviewed commercial license approval and a complete mapping to observable classes. No automated download, weights, training, photogrammetry or customer-data reuse is authorized.
