# Pilot report evidence integration

Block 27 maps the existing reviewed InspectionReport model into the shared customer pilot and extracts RGB/thermal frame references without copying or uploading image files. A report must be explicitly expert-reviewed. The pilot report still states that it is inspired by DIN IEC/TS 62446-3, not certified compliant.

Open work: include source-frame identifiers, verified module geometry, and actual approved RGB/thermal images in the PDF layout. The current PDF pilot is text-only; the existing general report renderer has image support but is not yet connected to the pilot. No Celsius values from thermal preview colors. Do not imply source images are available solely because a frame reference exists.
