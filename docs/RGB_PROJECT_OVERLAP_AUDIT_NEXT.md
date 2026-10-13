# RGB project overlap milestone

The project matcher now accepts real local RGB file paths, compares adjacent frames and caller-supplied cross-strip candidates, records feature counts, and computes graph connectivity. Candidate pairs are deduplicated and capped; audit summaries contain no image pixels.

Important limitations: caller must derive credible cross-strip candidates; this module does not infer flight strips from GPS/RTK. ORB/homography matches on repetitive panels are not sufficient proof of reconstruction feasibility. The audit deliberately leaves project_overlap_verified=false, even for a connected graph. A full-project coverage/degeneracy check, job/API persistence, thermal co-registration, and actual orthomosaic reconstruction remain outstanding.

No original customer images were opened in this block. No production/cloud operations were performed.
