# Image-overlap verification, first worker boundary

Feature matches between neighboring source images are evidence of shared visual content, but do not by themselves establish correct camera geometry, whole-project coverage, or cross-sensor alignment. A pair can be texture-poor, blurred or differently exposed. Do not label the entire project insufficient from one failed pair.

The first implementation accepts bounded, externally measured pairwise feature-match evidence. An image-pair record has candidate match count, geometrically verified inlier count, and verifier provenance. An undirected graph of strong links provides a **necessary connectivity check**, not sufficient photogrammetric validation. Missing/weak links lead to UNKNOWN (not proven insufficient). Only an explicit project-wide failure assessment from a real worker with recorded evidence may set INSUFFICIENT and trigger the German user warning.

No EXIF-only or guessed overlap percentages. Future worker should detect features on RGB source images, match adjacent and cross-strip neighbors, verify matches geometrically (RANSAC), estimate coverage and reprojection error, then assess RGB and thermal registration separately. Must not upload user images to GitHub. No new third-party dependency is introduced by this block.
