# Camera-angle fallback and overlap failure

Camera pose from EXIF/XMP is preferred when available, but manufacturer-neutral imagery may lack it. Ask: **„Bitte Kamerawinkel in Bezug zum Solarmodul eingeben.“** The angle is between the optical viewing direction and the module surface (90° = perpendicular). This is a scalar incidence angle, not yaw/pitch/roll; it cannot be converted into a complete camera pose. Mark source as user-supplied, retain per-image or series scope, and request reconstruction from feature matches when possible.

User guidance: normal operational target 70–95°; allow physically meaningful 0–180° input for the geometric angle between directed ray and plane, but clarify ambiguity: for an undirected plane acute incidence is 0–90°. We validate 0–90° as the canonical *acute* ray-to-plane angle and explain that 95° is treated as 85° if the ray direction is reversed. The manual field is not a substitute for calibration, positions or feature correspondences.

Only a real overlap/matching worker may set overlap to insufficient. Until assessed, status is unknown; never report failure from missing metadata alone. When insufficient, block reconstruction and display **„Keine Berechnung möglich, da die Bildüberlappung fehlerhaft ist.“** Include a separate diagnostic and allow new images or re-flight. No invented overlap scores.

This is a contract/UI milestone, not a functioning overlap detector or orthomosaic engine.
