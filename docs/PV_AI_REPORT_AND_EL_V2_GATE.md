# AI findings to expert-reviewed report; EL in v2

Report workflow: verified RGB/thermal orthomosaic alignment -> candidate detection (future YOLO worker) -> source RGB/thermal crop inspection -> expert accepts, rejects or marks uncertain -> report includes observed signature, image references, expert conclusion, and follow-up recommendation. A probable cause must not be written as a confirmed electrical diagnosis without appropriate measurements. Radiometric temperatures require calibrated provenance.

Current code adds taxonomy and in-memory training-candidate validation only. No YOLO model weights, RGB fault dataset, customer training consent backend, automatic annotation transfer, persistent dataset, training run or report integration has been added. Do not claim a working end-to-end pipeline.

EL v2 requires independent imaging modality and safety-controlled electrical excitation, calibrated NIR-sensitive camera, acquisition protocol, licensed annotated EL training data, and a dedicated review workflow. Reserve extensibility in the fault taxonomy, but do not block RGB/thermal v1 on unavailable EL imagery.
