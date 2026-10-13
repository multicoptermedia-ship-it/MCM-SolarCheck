# Orthomosaic comparison: shared online/offline contract

MCM-SolarCheck requires one registered RGB orthomosaic and one registered thermal orthomosaic for the same inspection area. A WebODM-like horizontal reveal slider must allow simultaneous inspection, pan/zoom and eventual candidate overlays.

The uploaded 29 DJI M3T pairs are the intended input. User confirms flight image overlap. Geometric reconstruction, registration accuracy, and radiometric integrity still require validation; none is claimed by this UI work.

**Fail closed:** no fabricated imagery, no guessed coordinates, no candidate overlay without verified orthomosaic registration. The browser receives same-origin, backend-authorized imagery only. Offline uses the local loopback server. Online must enforce ownership and report/demo gates at the API layer.

Thermal color previews are visualization only; 16-bit raw measurements and their provenance remain separate. Never treat palette colors as Celsius temperatures. Reviewer decisions and report export require their existing authorization and approval gates.

Initial milestone: validated comparison manifest, shared viewer with accessible reveal control, and tests. Full photogrammetry, tiles, reprojection and hotspot-to-module mapping are separate follow-up work.
