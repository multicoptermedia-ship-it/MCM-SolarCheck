"""Read-only inspection queries for review screens and reporting.

The query layer deliberately distinguishes calibrated Celsius evidence from raw
sensor values. Missing calibration is represented as ``None`` and is never
silently converted or estimated.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import json
from .sqlite import ProjectDatabase
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius

@dataclass(frozen=True)
class InspectionSummary:
    project_id: str
    rgb_frames: int
    thermal_frames: int
    image_pairs: int
    pv_modules: int
    findings: int
    unreviewed_findings: int
    confirmed_findings: int
    rejected_findings: int
    unclear_findings: int
    calibrated_findings: int

@dataclass(frozen=True)
class ImportVerificationSummary:
    project_id: str
    thermal_frames: int
    quality_pass: int
    quality_review: int
    quality_reject: int
    missing_timestamp: int
    missing_position: int
    missing_camera_identity: int


@dataclass(frozen=True)
class TechnicalPairAudit:
    """Anonymous aggregates of persisted metadata pairing, not registration."""
    pairs_recorded: int
    supported_by_current_rules: int
    require_review: int
    with_matching_sequence: int
    with_close_time: int
    with_close_position: int
    unmatched_rgb: int
    unmatched_thermal: int

@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    created_at: str

@dataclass(frozen=True)
class FindingRecord:
    finding_id: str
    thermal_frame_id: str
    module_id: str | None
    pixel_x: int
    pixel_y: int
    finding_type: str
    confidence: float | None
    raw_value: int | None
    raw_delta_from_median: float | None
    temperature_c: float | None
    reviewer_status: str
    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    rgb_frame_id: str | None = None
    pair_id: str | None = None
    pair_confidence: float | None = None
    rgb_pixel_x: float | None = None
    rgb_pixel_y: float | None = None
    transform_method: str | None = None
    transform_validated: bool | None = None
    transform_error_px: float | None = None
    cross_sensor_status: str | None = None
    temperature_status: str | None = None
    temperature_provider: str | None = None

@dataclass(frozen=True)
class ExpertReviewAuditRecord:
    """Actual persisted human review event, never the current model prediction."""
    review_id: int
    finding_id: str
    status: str
    reviewer: str
    reviewed_at_utc: str
    note: str | None
    thermal_frame_id: str
    module_id: str | None


@dataclass(frozen=True)
class ExpertReviewHistory:
    total: int
    offset: int
    entries: tuple[ExpertReviewAuditRecord, ...]


@dataclass(frozen=True)
class ModuleEvidenceRecord:
    """One observed module, not a confirmed unique physical PV-module identity."""
    module_id: str
    frame_id: str
    detector: str
    detection_confidence: float | None
    proposed_physical_id: str | None
    identity_status: str | None
    findings: int
    unreviewed: int
    confirmed: int
    rejected: int
    unclear: int


@dataclass(frozen=True)
class ModuleIdentityReadiness:
    """Project-wide counts of *candidate* links, never proven physical modules."""
    observed_modules: int
    linked_observations: int
    unresolved_observations: int
    distinct_candidate_labels: int
    orphaned_identity_links: int


@dataclass(frozen=True)
class ModuleIdentityRecord:
    frame_id:str
    local_module_id:str
    physical_module_id:str
    status:str
    normalized_distance:float|None

class InspectionQueries:
    """Stable read boundary between SQLite and UI/report generation."""
    def __init__(self,database:ProjectDatabase)->None:self.database=database
    def projects(self)->tuple[ProjectRecord,...]:
        """Return persisted projects for selection without synthesizing GUI state."""
        with self.database.connect() as db:
            rows=db.execute(
                "SELECT project_id,name,created_at FROM projects "
                "ORDER BY created_at DESC, project_id"
            ).fetchall()
        return tuple(ProjectRecord(**dict(row)) for row in rows)

    def summary(self,project_id:str)->InspectionSummary:
        with self.database.connect() as db:
            project=db.execute('SELECT 1 FROM projects WHERE project_id=?',(project_id,)).fetchone()
            if project is None:raise KeyError(f'Unknown project: {project_id}')
            def count(table:str)->int:return int(db.execute(f'SELECT COUNT(*) FROM {table} WHERE project_id=?',(project_id,)).fetchone()[0])
            statuses={row['reviewer_status']:int(row['n']) for row in db.execute('SELECT reviewer_status, COUNT(*) AS n FROM findings WHERE project_id=? GROUP BY reviewer_status',(project_id,))}
            calibrated=0
            for row in db.execute('SELECT temperature_c, metadata_json FROM findings WHERE project_id=?',(project_id,)):
                if row['temperature_c'] is None:
                    continue
                try:
                    metadata=json.loads(row['metadata_json'] or '{}')
                except (TypeError,json.JSONDecodeError):
                    continue
                if isinstance(metadata,dict) and has_validated_celsius(row['temperature_c'],metadata.get('temperature_status'),metadata.get('temperature_provider')):
                    calibrated+=1
            return InspectionSummary(project_id,count('image_frames'),count('thermal_frames'),count('image_pairs'),count('pv_modules'),count('findings'),statuses.get('unreviewed',0),statuses.get('confirmed',0),statuses.get('rejected',0),statuses.get('unclear',0),calibrated)
    def technical_pair_audit(self, project_id: str) -> TechnicalPairAudit:
        """Independently re-score saved pairs without opening pictures or writing.

        Stored numbers, metadata and coordinates stay inside the query.
        No geometric registration, Celsius calibration or expert approval.
        """
        from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame, Position
        from mcm_solarcheck.pairing.rgb_thermal import pair_score

        with self.database.connect() as db:
            if db.execute(
                "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
            ).fetchone() is None:
                raise KeyError("Unknown project")
            rgb_total = int(db.execute(
                "SELECT COUNT(*) FROM image_frames WHERE project_id=?", (project_id,)
            ).fetchone()[0])
            thermal_total = int(db.execute(
                "SELECT COUNT(*) FROM thermal_frames WHERE project_id=?", (project_id,)
            ).fetchone()[0])
            rows = db.execute("""
                SELECT p.confidence, p.method, p.rgb_frame_id, p.thermal_frame_id,
                       r.source_file AS rgb_source,
                       r.timestamp_utc AS rgb_time,
                       r.latitude AS rgb_lat, r.longitude AS rgb_lon,
                       t.source_file AS thermal_source,
                       t.timestamp_utc AS thermal_time,
                       t.latitude AS thermal_lat, t.longitude AS thermal_lon
                  FROM image_pairs AS p
                  LEFT JOIN image_frames AS r
                    ON r.project_id=p.project_id AND r.frame_id=p.rgb_frame_id
                  LEFT JOIN thermal_frames AS t
                    ON t.project_id=p.project_id AND t.frame_id=p.thermal_frame_id
                 WHERE p.project_id=?
                 ORDER BY p.pair_id
            """, (project_id,)).fetchall()

        count_sequence = count_time = count_position = supported = 0
        used_rgb, used_thermal = set(), set()
        for row in rows:
            if row["rgb_frame_id"] in used_rgb or row["thermal_frame_id"] in used_thermal:
                continue  # One acquisition cannot establish several unique pairs.
            used_rgb.add(row["rgb_frame_id"])
            used_thermal.add(row["thermal_frame_id"])
            if row["rgb_source"] is None or row["thermal_source"] is None:
                continue

            def to_frame(prefix: str, kind):
                stamp = row[prefix + "_time"]
                lat, lon = row[prefix + "_lat"], row[prefix + "_lon"]
                date = datetime.fromisoformat(stamp) if stamp else None
                location = None
                if lat is not None and lon is not None:
                    if not (isfinite(lat) and isfinite(lon)
                            and -90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValueError("invalid stored position")
                    location = Position(lat, lon)
                return kind(
                    frame_id=row["rgb_frame_id"] if prefix == "rgb"
                             else row["thermal_frame_id"],
                    source_file=Path(row[prefix + "_source"]),
                    timestamp_utc=date, position=location,
                )

            try:
                confidence, method, _distance, _delta = pair_score(
                    to_frame("rgb", ImageFrame),
                    to_frame("thermal", ThermalFrame),
                )
            except (ValueError, TypeError, OverflowError):
                continue
            factors = set(method.split("+"))
            count_sequence += "sequence" in factors
            count_time += "time" in factors
            count_position += "position" in factors
            if (confidence >= 0.70 and isfinite(row["confidence"])
                    and abs(row["confidence"] - confidence) < 0.00001
                    and row["method"] == method):
                supported += 1
        return TechnicalPairAudit(
            pairs_recorded=len(rows),
            supported_by_current_rules=supported,
            require_review=len(rows) - supported,
            with_matching_sequence=count_sequence,
            with_close_time=count_time,
            with_close_position=count_position,
            unmatched_rgb=max(0, rgb_total - len(used_rgb)),
            unmatched_thermal=max(0, thermal_total - len(used_thermal)),
        )

    def import_verification(self,project_id:str)->ImportVerificationSummary:
        """Summarize persisted thermal metadata and quality without inferring validity."""
        with self.database.connect() as db:
            project=db.execute('SELECT 1 FROM projects WHERE project_id=?',(project_id,)).fetchone()
            if project is None:raise KeyError(f'Unknown project: {project_id}')
            rows=db.execute(
                'SELECT quality_grade,timestamp_utc,latitude,longitude,camera_make,camera_model '
                'FROM thermal_frames WHERE project_id=?',(project_id,)
            ).fetchall()
        grades=[row['quality_grade'] for row in rows]
        return ImportVerificationSummary(
            project_id=project_id,
            thermal_frames=len(rows),
            quality_pass=grades.count('pass'),
            quality_review=grades.count('review'),
            quality_reject=grades.count('reject'),
            missing_timestamp=sum(row['timestamp_utc'] is None for row in rows),
            missing_position=sum(row['latitude'] is None or row['longitude'] is None for row in rows),
            missing_camera_identity=sum(
                not (row['camera_make'] or '').strip() or not (row['camera_model'] or '').strip()
                for row in rows
            ),
        )
    def module_evidence_page(
        self, project_id: str, *, limit: int = 100, offset: int = 0,
    ) -> tuple[ModuleEvidenceRecord, ...]:
        """Read a bounded page of local module observations and review counts.

        The grouping is per persisted local module ID and is strictly scoped
        by project. A geometric identity suggestion never becomes a verified
        physical assignment merely because it is stored.
        """
        if type(limit) is not int or not (1 <= limit <= 100):
            raise ValueError("module page limit must be between 1 and 100")
        if type(offset) is not int or offset < 0:
            raise ValueError("module page offset must be a non-negative integer")
        sql = """
            SELECT m.module_id, m.frame_id, m.detector, m.detection_confidence,
                   i.physical_module_id AS proposed_physical_id,
                   i.status AS identity_status,
                   COALESCE(f.total, 0) AS findings,
                   COALESCE(f.unreviewed, 0) AS unreviewed,
                   COALESCE(f.confirmed, 0) AS confirmed,
                   COALESCE(f.rejected, 0) AS rejected,
                   COALESCE(f.unclear, 0) AS unclear
              FROM pv_modules AS m
              LEFT JOIN module_identity_links AS i
                ON i.project_id=m.project_id AND i.frame_id=m.frame_id
               AND i.local_module_id=m.module_id
              LEFT JOIN (
                SELECT project_id,module_id,COUNT(*) AS total,
                       SUM(CASE WHEN reviewer_status='unreviewed' THEN 1 ELSE 0 END)
                         AS unreviewed,
                       SUM(CASE WHEN reviewer_status='confirmed' THEN 1 ELSE 0 END)
                         AS confirmed,
                       SUM(CASE WHEN reviewer_status='rejected' THEN 1 ELSE 0 END)
                         AS rejected,
                       SUM(CASE WHEN reviewer_status='unclear' THEN 1 ELSE 0 END)
                         AS unclear
                  FROM findings
                 WHERE project_id=? AND module_id IS NOT NULL
                 GROUP BY project_id,module_id
              ) AS f ON f.project_id=m.project_id AND f.module_id=m.module_id
             WHERE m.project_id=?
             ORDER BY m.module_id,m.frame_id
             LIMIT ? OFFSET ?
        """
        with self.database.connect() as db:
            rows = db.execute(sql, (project_id, project_id, limit, offset)).fetchall()
        return tuple(ModuleEvidenceRecord(**dict(row)) for row in rows)

    def unassigned_module_findings(self, project_id: str) -> int:
        """Count findings not linked to any local module in the same project."""
        with self.database.connect() as db:
            row = db.execute("""
                SELECT COUNT(*) FROM findings AS f
                 WHERE f.project_id=?
                   AND (
                     f.module_id IS NULL OR TRIM(f.module_id)=''
                     OR NOT EXISTS (
                        SELECT 1 FROM pv_modules AS m
                         WHERE m.project_id=f.project_id
                           AND m.module_id=f.module_id
                     )
                   )
            """, (project_id,)).fetchone()
        return int(row[0])

    def module_identity_readiness(self, project_id: str) -> ModuleIdentityReadiness:
        """Aggregate project-scoped identity readiness without paging or writes.

        Only 'new'/'matched' candidate links with a nonblank ID qualify.
        Counts of candidate IDs are NOT counts of real physical PV modules.
        """
        with self.database.connect() as db:
            counts = db.execute("""
                SELECT COUNT(*) AS observed_modules,
                       COALESCE(SUM(CASE
                           WHEN i.status IN ('new', 'matched')
                            AND i.physical_module_id IS NOT NULL
                            AND TRIM(i.physical_module_id) <> ''
                           THEN 1 ELSE 0 END), 0) AS linked_observations,
                       COUNT(DISTINCT CASE
                           WHEN i.status IN ('new', 'matched')
                            AND i.physical_module_id IS NOT NULL
                            AND TRIM(i.physical_module_id) <> ''
                           THEN i.physical_module_id ELSE NULL END)
                           AS distinct_candidate_labels
                  FROM pv_modules AS m
                  LEFT JOIN module_identity_links AS i
                    ON i.project_id=m.project_id
                   AND i.frame_id=m.frame_id
                   AND i.local_module_id=m.module_id
                 WHERE m.project_id=?
            """, (project_id,)).fetchone()
            orphaned = int(db.execute("""
                SELECT COUNT(*)
                  FROM module_identity_links AS i
                 WHERE i.project_id=?
                   AND NOT EXISTS (
                       SELECT 1 FROM pv_modules AS m
                        WHERE m.project_id=i.project_id
                          AND m.frame_id=i.frame_id
                          AND m.module_id=i.local_module_id
                   )
            """, (project_id,)).fetchone()[0])
        observed = int(counts["observed_modules"])
        linked = int(counts["linked_observations"])
        return ModuleIdentityReadiness(
            observed_modules=observed,
            linked_observations=linked,
            unresolved_observations=observed - linked,
            distinct_candidate_labels=int(counts["distinct_candidate_labels"]),
            orphaned_identity_links=orphaned,
        )

    def module_identities(self,project_id:str,*,physical_module_id:str|None=None)->tuple[ModuleIdentityRecord,...]:
        sql='SELECT frame_id,local_module_id,physical_module_id,status,normalized_distance FROM module_identity_links WHERE project_id=?'
        params=[project_id]
        if physical_module_id is not None:sql+=' AND physical_module_id=?';params.append(physical_module_id)
        sql+=' ORDER BY physical_module_id,frame_id,local_module_id'
        with self.database.connect() as db:rows=db.execute(sql,tuple(params)).fetchall()
        return tuple(ModuleIdentityRecord(**dict(row)) for row in rows)
    def expert_review_history(
        self, project_id: str, *, limit: int = 25, offset: int = 0,
    ) -> ExpertReviewHistory:
        """Read bounded, latest-first persisted audit events for one project.

        An audit event may be older than the finding's current status. Never
        substitute the present status for the immutable historic decision.
        """
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("review history limit must be 1 through 50")
        if type(offset) is not int or offset < 0:
            raise ValueError("review history offset must be nonnegative")
        with self.database.connect() as db:
            total = int(db.execute(
                "SELECT COUNT(*) FROM finding_reviews WHERE project_id=?",
                (project_id,),
            ).fetchone()[0])
            rows = db.execute(
                """
                SELECT a.review_id, a.finding_id, a.status, a.reviewer,
                       a.reviewed_at_utc, a.note,
                       f.thermal_frame_id, f.module_id
                  FROM finding_reviews AS a
                  JOIN findings AS f
                    ON f.project_id=a.project_id
                   AND f.finding_id=a.finding_id
                 WHERE a.project_id=?
                 ORDER BY a.review_id DESC
                 LIMIT ? OFFSET ?
                """,
                (project_id, limit, offset),
            ).fetchall()
        return ExpertReviewHistory(
            total, offset,
            tuple(ExpertReviewAuditRecord(**dict(row)) for row in rows),
        )

    def findings(self,project_id:str,*,reviewer_status:str|None=None,confirmed_only:bool=False,limit:int|None=None,offset:int=0)->tuple[FindingRecord,...]:
        if confirmed_only and reviewer_status is not None:raise ValueError('Use either confirmed_only or reviewer_status, not both')
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError('findings limit must be a positive integer')
        if type(offset) is not int or offset < 0:
            raise ValueError('findings offset must be a non-negative integer')
        if offset and limit is None:
            raise ValueError('paged findings require a bounded limit')
        status='confirmed' if confirmed_only else reviewer_status
        sql='''SELECT f.finding_id,f.thermal_frame_id,f.module_id,f.pixel_x,f.pixel_y,
                      f.finding_type,f.confidence,f.raw_value,f.raw_delta_from_median,
                      f.temperature_c,f.reviewer_status,f.latitude,f.longitude,f.altitude_m,
                      l.rgb_frame_id,l.pair_id,l.pair_confidence,l.rgb_pixel_x,l.rgb_pixel_y,
                      l.transform_method,l.transform_validated,l.transform_error_px,
                      l.status AS cross_sensor_status,f.metadata_json
               FROM findings f LEFT JOIN finding_sensor_links l
                 ON l.project_id=f.project_id AND l.finding_id=f.finding_id
               WHERE f.project_id=?'''
        params:list[object]=[project_id]
        if status is not None:sql+=' AND f.reviewer_status=?';params.append(status)
        sql+=' ORDER BY f.thermal_frame_id,f.pixel_y,f.pixel_x,f.finding_id'
        if limit is not None:
            sql+=' LIMIT ? OFFSET ?'
            params.extend((limit, offset))
        with self.database.connect() as db:rows=db.execute(sql,tuple(params)).fetchall()
        records=[]
        for row in rows:
            values=dict(row)
            try:
                metadata=json.loads(values.pop('metadata_json') or '{}')
            except (TypeError,json.JSONDecodeError):
                metadata={}
            if not isinstance(metadata,dict):
                metadata={}
            values['temperature_status']=metadata.get('temperature_status')
            values['temperature_provider']=metadata.get('temperature_provider')
            if values['transform_validated'] is not None:values['transform_validated']=bool(values['transform_validated'])
            records.append(FindingRecord(**values))
        return tuple(records)
