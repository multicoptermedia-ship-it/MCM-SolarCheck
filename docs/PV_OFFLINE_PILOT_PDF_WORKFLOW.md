# Local customer pilot PDF workflow

The report is explicitly an illustrative inspection document inspired by DIN IEC/TS 62446-3 (VDE V 0126-23-3):2018-04, not a claim of conformity. The first example is entirely fictional and must not be represented as a completed inspection.

From a configured local Python environment with reportlab installed:

```python
from pathlib import Path
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf

export_pilot_pdf(fictional_pilot_report(), Path("musterbericht.pdf"))
```

The destination directory must exist. This adapter does not send, upload or publish customer data. Review the PDF locally, then obtain permission before sharing any actual customer material. Collect comments about clarity, visual layout, evidence, recommendations and length.

Production integration remains open: convert reviewed inspection evidence into the pilot contract; include RGB/thermal images and module positions; use common export semantics for offline and online; perform a licensed full-text normative gap review before claiming compliance.
