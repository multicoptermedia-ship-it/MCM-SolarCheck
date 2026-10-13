# Customer pilot PDF layout v2

Block 30 adds a repeatable page header and footer, page numbering, and a two-column RGB/thermal evidence pair for each expert-reviewed module finding. A short observation sits directly above its image pair; source frame and geometry references remain below each image. Missing images are explicitly marked.

The document retains its statement that it is inspired by DIN IEC/TS 62446-3 and is **not** proof of conformity. RGB/thermal imagery is not proof of a validated module polygon, electrical diagnosis or radiometric temperature.

Run the fictional sample generator with `python -m mcm_solarcheck.services.pv_pilot_sample_cli ./solarcheck-muster.pdf`. Review the resulting file visually on A4 and check long source identifiers, multi-page flow and footer legibility. No real customer imagery is required.
