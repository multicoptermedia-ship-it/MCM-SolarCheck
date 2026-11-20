# Public PV dataset intake register (review required)

Status19.11.2026: the user selected a bounded **CVUT public-data/model pilot**. See [Windows intake](CVUT_PV_PILOT_WINDOWS10.md) and [current handoff](AKTUELLER_ENTWICKLUNGSSTAND.md). Dataset permission, model-weight permission and dependency licenses are separate. No customer imagery is part of this pilot.

| Individual-module candidate | Publisher evidence / scope | Intake decision |
| --- | --- | --- |
| [CVUT PVsegmentation](https://imr.ciirc.cvut.cz/Datasets/PVsegmentation) | 136RGB+74thermal images, >3000 masks; mask images and contour labels. Publisher explicitly states **CC BY4.0**, commercial use with attribution. Kozák/Košnar/Chudoba/Kulich/Přeučil, CTU Prague; cite related publication and source/license, identify changes. | First pilot selected. User browser download/local inventory PASS20.11:344288853Bytes, observed SHA61d981c2…8ab14b(full hash in Windows guide); three.pth files, no license/architecture documents. RGB module member selected, nonexecuting structure inspector implemented; User layout PASS:118entries, RGB3/two logits2, modern Torch ZIP/protocol2. RGB SHA8e862b64…fa1cac8. External GPL3.0 U-Net reference is structurally compatible; isolated CPU candidate implemented, original CVUT preprocessing/class mapping and production rights remain unverified. Provider here HTTP503. Observed local SHA is not an upstream checksum. No training/inference/production approval from this inventory. Model selection must exclude the whole-installation model. |
| [PVIS-10K](https://zenodo.org/records/23886365) / [publisher code](https://github.com/plzhang1998/PVDataset) | RGB UAV individual-module COCO polygons, site-based split; dataset CC BY4.0, original processing code Apache2.0, third-party licenses separate. | Later option, no31GB download now. No supervised checkpoints provided in code release; SAM3 runtime/license is a separate decision. |

Primary-page evidence checked19.11.2026 via indexed provider pages; live CVUT page/archive requests failed HTTP503. Preserve attribution and record concrete archive/version/hash before actual data use. Dataset licensing is not evidence of a particular weight/code/runtime license. [Paper](https://arxiv.org/abs/2501.14587) describes U-Net mask-to-instance postprocessing and domain/reflection limitations; it does not establish SolarCheck orthophoto accuracy.

The older entries below remain **candidates**, not approved for commercial training. Free download does not establish commercial reuse rights. Inspect original copyright, derivative versions, attribution, privacy and model-license requirements before activation.

| Candidate | Modality | Annotation | Source | License review |
| --- | --- | --- | --- | --- |
| PV-Multi-Defect | surface images; verify capture modality before RGB use | VOC-style XML and JPEG | https://github.com/CCNUZFW/PV-Multi-Defect | unresolved: paper CC license is not proof of image license |
| PV-Multi-Defect Roboflow derivative | surface images | YOLO export advertised | https://universe.roboflow.com/initial-e1ks9/pv-multi-defect-adsij | CC BY 4.0 claimed by derivative; verify original rights |
| MSPS | electroluminescence, **not RGB** | segmentation | https://github.com/wch313/MSPS-Dataset | CC BY 4.0 declared; reserve for EL v2 |
| ELPV | electroluminescence, **not RGB** | defect probabilities | https://github.com/zae-bayern/elpv-dataset | CC BY-NC-SA 4.0 images: NOT approved for commercial training |

For each proposed dataset record: origin URL, publisher, image modality, original and derivative licenses, commercial-use decision, attribution, checksum, class definitions, annotation format, capture/site group, split methodology, reviewer and approval timestamp.

Do not copy public imagery/weights into Git, fetch from untrusted sources automatically, or upload customer imagery. Earlier milestone's blanket no-download rule is superseded only for the explicitly selected bounded public CVUT intake: official U-Net model ZIP, metadata/documentation only, no extraction or model execution. Public image downloads/training are later steps with concrete dataset records and qualified runtime. EL remains version 2.

20.11.2026: explicit public CVUT pilot now includes a separately manually started CPU candidate. Only the observed RGB weights and pinned external reference/license are copied locally. Restricted weights_only CPU loading and synthetic probe precede any saved-ROI evaluation. This supersedes the earlier inventory-only execution limit within the already selected bounded pilot; it is not a commercial, distribution or customer-training clearance.
