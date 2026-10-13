# Local RGB feature-overlap worker

OpenCV ORB detects features in grayscale RGB imagery. A two-way descriptor match and homography RANSAC reject some ambiguous correspondences. The worker emits counts and provenance only; it does not export pixels. It requires at least four inliers to estimate a homography and checks minimum inlier fraction. Repetitive PV-cell patterns can still fool homographies, so verified inliers are **not** proof of reliable orthomosaic reconstruction.

Images are decoded locally, downsampled with an upper pixel bound, and checked for minimum dimensions. Unreadable images fail closed. Project-level coverage and flight-strip consistency are not yet measured. Never publish insufficient-overlap project status from a single pair.

This is an initial RGB pair matcher, not RGB/thermal co-registration, orthorectification, or a calibrated thermal pipeline.
