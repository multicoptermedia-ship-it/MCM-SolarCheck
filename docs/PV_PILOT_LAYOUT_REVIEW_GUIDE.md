# SolarCheck illustrated report review

Create a fictional PDF locally:

```bash
python -m mcm_solarcheck.services.pv_pilot_sample_cli ./solarcheck-muster.pdf
```

This sample uses generated diagram-like images, **not drone photos**, and is not a real inspection. No images or report are uploaded. Inspect the PDF manually for readability, pagination, the position of source references, image aspect ratios, disclaimers and missing measurement conditions. Automated smoke tests do not establish visual quality.

Next iteration: use side-by-side RGB/thermal layout when it remains legible at A4 width, add repeatable headers/footers, then review an actual locally rendered PDF. Customer sharing only after explicit approval.
