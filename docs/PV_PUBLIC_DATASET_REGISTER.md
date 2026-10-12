# Public PV dataset intake register (review required)

All entries are **candidates**, not approved for commercial training. Free download does not establish commercial reuse rights. Inspect original copyright, derivative versions, attribution, privacy and model-license requirements before activation.

| Candidate | Modality | Annotation | Source | License review |
| --- | --- | --- | --- | --- |
| PV-Multi-Defect | surface images; verify capture modality before RGB use | VOC-style XML and JPEG | https://github.com/CCNUZFW/PV-Multi-Defect | unresolved: paper CC license is not proof of image license |
| PV-Multi-Defect Roboflow derivative | surface images | YOLO export advertised | https://universe.roboflow.com/initial-e1ks9/pv-multi-defect-adsij | CC BY 4.0 claimed by derivative; verify original rights |
| MSPS | electroluminescence, **not RGB** | segmentation | https://github.com/wch313/MSPS-Dataset | CC BY 4.0 declared; reserve for EL v2 |
| ELPV | electroluminescence, **not RGB** | defect probabilities | https://github.com/zae-bayern/elpv-dataset | CC BY-NC-SA 4.0 images: NOT approved for commercial training |

For each proposed dataset record: origin URL, publisher, image modality, original and derivative licenses, commercial-use decision, attribution, checksum, class definitions, annotation format, capture/site group, split methodology, reviewer and approval timestamp.

Do not copy public imagery into Git, fetch from untrusted sources automatically, or upload customer imagery. No model training or weight downloads in this milestone. EL remains version 2.
