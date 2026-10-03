"""Report-ready, read-only inspection data assembled from SQLite."""
from __future__ import annotations
from dataclasses import dataclass
from mcm_solarcheck.storage.queries import FindingRecord, InspectionQueries, InspectionSummary
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius

@dataclass(frozen=True)
class ReportFinding:
    finding: FindingRecord
    rgb_frame_id: str | None
    pair_confidence: float | None
    pair_method: str | None
    review_note: str | None
    reviewer: str | None

@dataclass(frozen=True)
class InspectionReportData:
    project_id: str
    project_name: str
    summary: InspectionSummary
    confirmed_findings: tuple[ReportFinding,...]
    temperature_evidence_validated: bool

class InspectionReportDataService:
    """Build report evidence without inventing missing calibration or pairing data."""
    def __init__(self,database:ProjectDatabase)->None:self.database=database;self.queries=InspectionQueries(database)
    def build(self,project_id:str)->InspectionReportData:
        summary=self.queries.summary(project_id);confirmed=self.queries.findings(project_id,confirmed_only=True)
        with self.database.connect() as db:
            project=db.execute('SELECT name FROM projects WHERE project_id=?',(project_id,)).fetchone()
            rows=[]
            for finding in confirmed:
                pair=db.execute('SELECT rgb_frame_id,confidence,method FROM image_pairs WHERE project_id=? AND thermal_frame_id=? ORDER BY confidence DESC,pair_id LIMIT 1',(project_id,finding.thermal_frame_id)).fetchone()
                review=db.execute("SELECT reviewer,note FROM finding_reviews WHERE project_id=? AND finding_id=? AND status='confirmed' ORDER BY review_id DESC LIMIT 1",(project_id,finding.finding_id)).fetchone()
                rows.append(ReportFinding(finding,pair['rgb_frame_id'] if pair else None,pair['confidence'] if pair else None,pair['method'] if pair else None,review['note'] if review else None,review['reviewer'] if review else None))
        # A numeric Celsius value alone is not proof of calibration. Persisted
        # provenance must explicitly identify validated provider output.
        validated=bool(confirmed) and all(
            has_validated_celsius(item.temperature_c, item.temperature_status, item.temperature_provider)
            for item in confirmed
        )
        return InspectionReportData(project_id,project['name'],summary,tuple(rows),validated)
