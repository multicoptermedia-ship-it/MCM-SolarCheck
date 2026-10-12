# Flight-wide RGB overlap candidate selection

Consecutive images are not sufficient for grid/roof inspections. Inspect adjacent frames plus explicit cross-strip candidate pairs based on flight planning, image footprints, or independently verified metadata. Do not compare all N² frames blindly; cap candidate count. Candidate generation does not prove overlap. A disconnected feature graph is diagnostic only, never an automatic definitive project failure.

Each project audit retains frame IDs, candidate reasons, match counts, verifier, and connectivity status, but no pixels or GPS coordinates. Repeated PV module patterns can produce false homographies; a future worker must validate spatial coverage, residuals, camera poses, and repeated-pattern degeneracy before approving reconstruction. Cross-strip suggestions must not be invented from frame names alone.
