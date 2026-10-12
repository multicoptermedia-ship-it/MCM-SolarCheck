# RGB overlap: implementation and next integration

The new ORB/RANSAC matcher reads local image pixels, produces verified correspondence counts, and checks graph connectivity across consecutive RGB frames. It uses existing OpenCV and NumPy dependencies. Synthetic tests cover textured, blank and invalid images.

Limitations: matching consecutive frames alone can miss cross-strip coverage; repeated solar cells can create convincing false homographies; an image pair may be planar but unsuitable for calibrated reconstruction. The worker does not yet assess all-pairs neighborhoods, camera calibration, per-module plane consistency, GPS/RTK priors, reprojection error, or RGB/thermal registration.

Next: integrate this worker into the project job pipeline, add overlap audit persistence, geometric degeneracy checks, robust cross-strip neighbors and a project-wide decision. Until then, graph connectivity is a diagnostic only and must not trigger the user-visible definitive error by itself. No user source images were read or transferred in this development block.
