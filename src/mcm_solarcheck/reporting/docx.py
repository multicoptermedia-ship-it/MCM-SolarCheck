"""DOCX renderer for the neutral inspection report model."""
from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.shared import Inches
from .model import InspectionReportModel
from .evidence_render import RenderedEvidence


def render_docx(model:InspectionReportModel,output_path:str|Path,*,rendered_evidence:tuple[RenderedEvidence,...]=())->Path:
    """Render a conservative report: missing or unvalidated evidence stays explicit."""
    output=Path(output_path);output.parent.mkdir(parents=True,exist_ok=True)
    evidence_by_id={item.finding_id:item for item in rendered_evidence}
    doc=Document();doc.add_heading(model.title,0);doc.add_paragraph(model.project_name)
    doc.add_heading('Inspection status',level=1);doc.add_paragraph(model.inspection_status)
    doc.add_heading('Thermal measurement status',level=1);doc.add_paragraph(model.temperature_statement)
    if model.warnings:
        doc.add_heading('Warnings',level=1)
        for warning in model.warnings:doc.add_paragraph(warning,style='List Bullet')
    doc.add_heading('Confirmed findings',level=1)
    if not model.evidence:doc.add_paragraph('No confirmed findings are available for this report.')
    for index,item in enumerate(model.evidence,1):
        doc.add_heading(f'Finding {index}: {item.finding_id}',level=2)
        table=doc.add_table(rows=0,cols=2)
        fields=(('Classification',item.classification),('Module',item.module_id),('Thermal frame',item.thermal_frame_id),('RGB frame',item.rgb_frame_id),('Raw sensor value',item.raw_value),('Raw delta from median',item.raw_delta_from_median),('Temperature [°C]',item.temperature_c),('Latitude',item.latitude),('Longitude',item.longitude),('Reviewer',item.reviewer),('Review note',item.review_note))
        for label,value in fields:
            cells=table.add_row().cells;cells[0].text=label;cells[1].text='Not available' if value is None else str(value)
        rendered=evidence_by_id.get(item.finding_id)
        if rendered is None:
            doc.add_paragraph('Visual evidence: not rendered or unavailable.')
            continue
        doc.add_heading('Visual evidence',level=3)
        image_table=doc.add_table(rows=1,cols=2);cells=image_table.rows[0].cells
        if rendered.thermal_image.exists():
            cells[0].paragraphs[0].add_run('Thermal evidence\n').bold=True
            cells[0].paragraphs[0].add_run().add_picture(str(rendered.thermal_image),width=Inches(3.0))
        else:cells[0].text='Thermal evidence unavailable.'
        if rendered.rgb_image is not None and rendered.rgb_image.exists():
            cells[1].paragraphs[0].add_run('RGB evidence — validated mapping\n').bold=True
            cells[1].paragraphs[0].add_run().add_picture(str(rendered.rgb_image),width=Inches(3.0))
        else:
            cells[1].text='RGB evidence with validated marker unavailable.'
    doc.save(output);return output
