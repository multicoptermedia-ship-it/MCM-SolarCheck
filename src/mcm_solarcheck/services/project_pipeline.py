"""Application service for importing one M3T inspection project into SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from mcm_solarcheck.importers.project import ProjectImportResult, import_m3t_project
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.storage.queries import InspectionQueries, InspectionSummary, ModuleEvidenceRecord, ProjectRecord
from mcm_solarcheck.services.workflow import ActionAvailability, ProjectWorkflowService, WorkflowAction, WorkflowAttempt, ProjectWorkflowState, action_availability, record_attempt, require_action
from mcm_solarcheck.services.product_entitlements import OFFLINE_DESKTOP, ProductCapabilities, ProductOperation, effective_output_availability
from mcm_solarcheck.reporting.export import export_report
from mcm_solarcheck.reporting.report_assembler import assemble_inspection_report
from mcm_solarcheck.review.findings import ReviewStatus, review_finding


class ProjectImportCancelled(Exception):
    """The running import was cancelled before its database transaction committed."""


@dataclass(frozen=True)
class ProjectPipelineSummary:
    rgb_frames: int
    thermal_frames: int
    thermal_failures: int
    pairs: int
    findings: int
    unpaired_rgb: int
    unpaired_thermal: int


@dataclass(frozen=True)
class PlantOverview:
    """Authoritative counts plus a bounded page of local PV module observations."""
    summary: InspectionSummary
    modules: tuple[ModuleEvidenceRecord, ...]
    unassigned_findings: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ProjectProcessingOverview:
    """Persisted project evidence plus existing action gates, never an invented result."""

    summary: InspectionSummary
    process: ActionAvailability
    review: ActionAvailability


def import_and_store_m3t_project(
    source_directory: str | Path,
    database_path: str | Path,
    *,
    project_id: str,
    project_name: str,
    minimum_pair_confidence: float = 0.70,
    candidate_percentile: float = 99.9,
    candidate_limit: int = 100,
) -> tuple[ProjectImportResult, ProjectPipelineSummary]:
    """Run import, pairing and persistence as one application-level operation."""
    result = import_m3t_project(
        source_directory,
        minimum_pair_confidence=minimum_pair_confidence,
        candidate_percentile=candidate_percentile,
        candidate_limit=candidate_limit,
    )
    database = ProjectDatabase(database_path)
    database.initialize()
    database.create_project(project_id, project_name)
    database.save_image_frames(project_id, result.rgb_frames)
    for thermal in result.thermal_batch.results:
        database.save_thermal_frame(project_id, thermal.frame, thermal.quality)
        database.save_findings(project_id, thermal.findings)
    database.save_pairs(project_id, result.pairs)

    summary = ProjectPipelineSummary(
        rgb_frames=len(result.rgb_frames),
        thermal_frames=len(result.thermal_batch.results),
        thermal_failures=len(result.thermal_batch.failures),
        pairs=len(result.pairs),
        findings=sum(len(item.findings) for item in result.thermal_batch.results),
        unpaired_rgb=result.unpaired_rgb_count,
        unpaired_thermal=result.unpaired_thermal_count,
    )
    return result, summary



class ProjectApplicationService:
    """Guard application operations with the persisted workflow contract."""

    def __init__(self, database: ProjectDatabase) -> None:
        self.database = database
        self.workflow = ProjectWorkflowService(database)

    def projects(self) -> tuple[ProjectRecord, ...]:
        """Expose persisted project selection through the application boundary."""
        return InspectionQueries(self.database).projects()

    def projects_for_customer(self, customer_id: str) -> tuple[ProjectRecord, ...]:
        """Expose only projects owned by the authenticated online customer."""
        return self.database.projects_for_customer(customer_id)

    def create_project(self, project_id: str, name: str) -> ProjectRecord:
        """Create a new persisted project without silently overwriting an existing one."""
        project_id = project_id.strip()
        name = name.strip()
        if not project_id:
            raise ValueError("project_id must not be blank")
        if not name:
            raise ValueError("name must not be blank")
        if any(project.project_id == project_id for project in self.projects()):
            raise ValueError(f"Project already exists: {project_id}")
        self.database.create_project(project_id, name)
        return next(
            project for project in self.projects() if project.project_id == project_id
        )

    def create_project_with_profile(
        self, project_id: str, name: str, profile: ProjectProfile
    ) -> ProjectRecord:
        """Atomically create a project together with validated master data."""
        project_id = project_id.strip()
        name = name.strip()
        if not project_id:
            raise ValueError("project_id must not be blank")
        if not name:
            raise ValueError("name must not be blank")
        if not isinstance(profile, ProjectProfile):
            raise TypeError("profile must be ProjectProfile")
        if any(project.project_id == project_id for project in self.projects()):
            raise ValueError(f"Project already exists: {project_id}")
        self.database.create_project_with_profile(project_id, name, profile)
        return next(
            project for project in self.projects() if project.project_id == project_id
        )

    def save_project_profile(self, project_id: str, profile: ProjectProfile) -> ProjectProfile:
        """Persist validated project master data through the application boundary."""
        if not isinstance(profile, ProjectProfile):
            raise TypeError("profile must be ProjectProfile")
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        self.database.save_project_profile(project_id, profile)
        return profile

    def update_project_profile_if_unchanged(
        self, project_id: str, expected: ProjectProfile | None,
        updated: ProjectProfile,
    ) -> bool:
        """Persist an explicit master-data edit only if its snapshot is current.

        Return False for a no-op. Preserve the database's project-scoped
        compare-and-set so concurrent dialogs cannot silently overwrite data.
        """
        if not isinstance(updated, ProjectProfile):
            raise TypeError("updated profile must be ProjectProfile")
        if expected is not None and not isinstance(expected, ProjectProfile):
            raise TypeError("expected profile must be ProjectProfile or None")
        return self.database.update_project_profile_if_unchanged(
            project_id, expected, updated,
        )

    def project_profile(self, project_id: str) -> ProjectProfile | None:
        """Expose persisted project master data without inventing missing values."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return self.database.project_profile(project_id)

    def open_project(self, project_id: str) -> ProjectWorkflowState:
        """Open only a persisted project and return its authoritative workflow state."""
        projects = self.projects()
        if not any(project.project_id == project_id for project in projects):
            raise KeyError(f"Unknown project: {project_id}")
        return self.state(project_id)

    def require(self, project_id: str, action: WorkflowAction) -> None:
        """Reject an operation before side effects when its workflow gate is closed."""
        require_action(self.workflow.state(project_id), action)

    def state(self, project_id: str) -> ProjectWorkflowState:
        """Expose the same persisted state used to guard operations."""
        return self.workflow.state(project_id)

    def execute(self, project_id: str, action: WorkflowAction, operation):
        """Guard, execute once, then re-derive state from persisted evidence."""
        state_before = self.state(project_id)
        require_action(state_before, action)
        try:
            result = operation()
        except Exception as error:
            return record_attempt(action, error), None, self.state(project_id)
        return record_attempt(action), result, self.state(project_id)

    def inspect_project_geotiff(self, project_id: str, source_path: str | Path):
        """Inspect a local GIS file in an existing project without importing or approving it."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        from mcm_solarcheck.services.orthomosaic_geotiff_contract import inspect_existing_geotiff
        return inspect_existing_geotiff(source_path)

    def register_project_geotiff(self, project_id: str, source_path: str | Path, *, source_kind: str):
        """Persist observed GIS provenance; never approve an orthophoto."""
        import hashlib
        if source_kind not in ("webodm", "external_gis", "unknown"):
            raise ValueError("GeoTIFF source_kind must be webodm, external_gis or unknown")
        reference = self.inspect_project_geotiff(project_id, source_path)
        source = Path(source_path).resolve(strict=True)
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        self.database.save_geotiff_inspection(
            project_id, source, source_kind, digest.hexdigest(), reference
        )
        return reference

    def generate_project_planar_orthophotos(
        self, project_id, rgb_frames, thermal_frames, rgb_controls, thermal_controls,
        rgb_reference, thermal_reference, rgb_destination, thermal_destination,
        *, planar_surface_verified=False,
    ):
        """Generate from explicitly supplied imported frames and surveyed geometry.

        No automatic reconstruction or inferred survey approval is performed.
        """
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        from mcm_solarcheck.services.orthophoto_imported_pair import (
            generate_imported_planar_orthophoto_pair,
        )
        return generate_imported_planar_orthophoto_pair(
            rgb_frames, thermal_frames, rgb_controls, thermal_controls,
            rgb_reference, thermal_reference, rgb_destination, thermal_destination,
            planar_surface_verified=planar_surface_verified,
        )

    def imported_orthophoto_sources(self, project_id: str):
        """Expose persisted original RGB and thermal frames without inventing controls."""
        from mcm_solarcheck.services.orthophoto_project_sources import project_imported_frames
        return project_imported_frames(self.database, project_id)

    def generate_imported_project_orthophotos(
        self, project_id, rgb_controls, thermal_controls,
        rgb_reference, thermal_reference, rgb_destination, thermal_destination,
        *, planar_surface_verified=False,
    ):
        """Generate separate orthophotos using original frames stored in this project."""
        if planar_surface_verified is not True:
            raise ValueError("verified planar surface model required")
        rgb_frames, thermal_frames = self.imported_orthophoto_sources(project_id)
        if not rgb_frames or not thermal_frames:
            raise ValueError("project requires imported RGB and thermal originals")
        return self.generate_project_planar_orthophotos(
            project_id, rgb_frames, thermal_frames, rgb_controls, thermal_controls,
            rgb_reference, thermal_reference, rgb_destination, thermal_destination,
            planar_surface_verified=planar_surface_verified,
        )

    def project_geotiff_inspections(self, project_id: str):
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return self.database.geotiff_inspections(project_id)

    def import_summary(self, project_id: str):
        """Expose persisted import counts through the application boundary."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return InspectionQueries(self.database).summary(project_id)

    def plant_overview(
        self, project_id: str, *, offset: int = 0, limit: int = 100,
    ) -> PlantOverview:
        """Display persisted local module evidence, never a fabricated site map.

        Exactly the same project boundary and overall counts as Import/Review
        are reused. Spatial accuracy and unique physical identity are not
        inferred from image-local detector labels.
        """
        if type(limit) is not int or not (1 <= limit <= 100):
            raise ValueError("module page limit must be between 1 and 100")
        if type(offset) is not int or offset < 0:
            raise ValueError("module page offset must be a non-negative integer")
        summary = self.import_summary(project_id)
        queries = InspectionQueries(self.database)
        return PlantOverview(
            summary=summary,
            modules=queries.module_evidence_page(
                project_id, offset=offset, limit=limit,
            ),
            unassigned_findings=queries.unassigned_module_findings(project_id),
            offset=offset,
            limit=limit,
        )

    def processing_overview(self, project_id: str) -> ProjectProcessingOverview:
        """Read the authoritative SQLite evidence and existing workflow gates.

        An imported frame does not imply a finished processing job or a
        reviewed finding. This read-only view never starts processing.
        """
        summary = self.import_summary(project_id)
        state = self.state(project_id)
        return ProjectProcessingOverview(
            summary=summary,
            process=action_availability(state, WorkflowAction.PROCESS),
            review=action_availability(state, WorkflowAction.REVIEW),
        )

    def import_verification(self, project_id: str):
        """Expose persisted import metadata verification through the application boundary."""
        if not any(project.project_id == project_id for project in self.projects()):
            raise KeyError(f"Unknown project: {project_id}")
        return InspectionQueries(self.database).import_verification(project_id)

    def import_project_images(
        self,
        project_id: str,
        source_directory: str | Path,
        *,
        minimum_pair_confidence: float = 0.70,
        candidate_percentile: float = 99.9,
        candidate_limit: int = 100,
    ):
        """Import imagery only through the guarded application boundary."""
        project = next(
            (item for item in self.projects() if item.project_id == project_id),
            None,
        )
        if project is None:
            raise KeyError(f"Unknown project: {project_id}")

        return self.execute(
            project_id,
            WorkflowAction.IMPORT,
            lambda: import_and_store_m3t_project(
                source_directory,
                self.database.path,
                project_id=project.project_id,
                project_name=project.name,
                minimum_pair_confidence=minimum_pair_confidence,
                candidate_percentile=candidate_percentile,
                candidate_limit=candidate_limit,
            ),
        )

    def import_project_images_cancellable(
        self,
        project_id: str,
        source_directory: str | Path,
        *,
        should_cancel=None,
        on_progress=None,
        minimum_pair_confidence: float = 0.70,
        candidate_percentile: float = 99.9,
        candidate_limit: int = 100,
    ):
        """Offline worker entry: import first, then atomically persist all evidence.

        No writes take place during decoding or pairing. The single
        save_project_import transaction contains all RGB frames, thermal
        frames, candidate findings, and pairs. A cooperative cancellation
        before its commit rolls the whole transaction back.
        """
        self.require(project_id, WorkflowAction.IMPORT)
        project = next(
            (item for item in self.projects() if item.project_id == project_id),
            None,
        )
        if project is None:
            raise KeyError(f"Unknown project: {project_id}")

        phase, count = "Einlesen und Zuordnen", 0

        def heartbeat():
            nonlocal count
            if should_cancel is not None and should_cancel():
                raise ProjectImportCancelled("DJI-Projektimport abgebrochen")
            count += 1
            if on_progress is not None and count % 50 == 0:
                on_progress(phase, count)

        def set_phase(value):
            nonlocal phase, count
            phase, count = value, 0
            if on_progress is not None:
                on_progress(value, 0)

        try:
            set_phase("Einlesen und Zuordnen")
            heartbeat()
            result = import_m3t_project(
                source_directory,
                minimum_pair_confidence=minimum_pair_confidence,
                candidate_percentile=candidate_percentile,
                candidate_limit=candidate_limit,
                heartbeat=heartbeat,
                retain_rasters=False,  # Offline persistence needs findings, not raw pixels.
            )
            heartbeat()
            # Do not quietly commit only the readable part of a flight after
            # the thermal importer has recorded corrupt/unreadable images.
            if result.thermal_batch.failures:
                raise ValueError(
                    f"{len(result.thermal_batch.failures)} Thermaldateien konnten "
                    "nicht importiert werden; Projekt bleibt unverändert"
                )
            if not result.rgb_frames and not result.thermal_batch.results:
                raise ValueError("Keine importierbaren DJI-Bilder im Verzeichnis")
            set_phase("Atomare SQLite-Speicherung")
            self.database.save_project_import(
                project_id, result, checkpoint=heartbeat,
            )
        except ProjectImportCancelled:
            raise
        except Exception as exc:
            return (
                record_attempt(WorkflowAction.IMPORT, exc),
                None,
                self.state(project_id),
            )

        summary = ProjectPipelineSummary(
            rgb_frames=len(result.rgb_frames),
            thermal_frames=len(result.thermal_batch.results),
            thermal_failures=len(result.thermal_batch.failures),
            pairs=len(result.pairs),
            findings=sum(len(item.findings) for item in result.thermal_batch.results),
            unpaired_rgb=result.unpaired_rgb_count,
            unpaired_thermal=result.unpaired_thermal_count,
        )
        return (
            record_attempt(WorkflowAction.IMPORT),
            (result, summary),
            self.state(project_id),
        )

    def output_availability(
        self,
        project_id: str,
        capabilities: ProductCapabilities,
        operation: ProductOperation,
    ):
        """Expose one application boundary combining persisted and product gates."""
        workflow_action = (
            WorkflowAction.EXPORT
            if operation is ProductOperation.EXPORT
            else WorkflowAction.PREPARE_REPORT
        )
        workflow = action_availability(self.state(project_id), workflow_action)
        return effective_output_availability(
            capabilities,
            operation,
            workflow_allowed=workflow.allowed,
            workflow_blockers=workflow.blockers,
        )



    def expert_review_history(
        self, project_id: str, *, limit: int = 25, offset: int = 0,
    ):
        """Read-only, project-scoped audit trail of explicit human decisions."""
        self.import_summary(project_id)  # Fail on an unknown project.
        return InspectionQueries(self.database).expert_review_history(
            project_id, limit=limit, offset=offset,
        )

    def pending_review_findings(
        self, project_id: str, *, limit: int = 50, offset: int = 0,
    ):
        """Read a bounded, stable-ordered page of the project's open findings."""
        if type(offset) is not int or offset < 0:
            raise ValueError("review queue offset must be a non-negative integer")
        self.import_summary(project_id)  # Reject unknown projects explicitly.
        return InspectionQueries(self.database).findings(
            project_id, reviewer_status=ReviewStatus.UNREVIEWED.value,
            limit=limit, offset=offset,
        )

    def preview_review_images(
        self, project_id: str, finding_id: str, selected_folder: str | Path,
    ) -> tuple[bytes | None, bytes | None]:
        """Read local thumbnails only for an active, pending project finding."""
        self.require(project_id, WorkflowAction.REVIEW)
        from mcm_solarcheck.services.review_image_preview import (
            preview_pending_finding_images,
        )
        return preview_pending_finding_images(
            self.database, project_id, finding_id, selected_folder,
        )

    def preview_review_image_evidence(
        self, project_id: str, finding_id: str, selected_folder: str | Path,
    ):
        """Expose project-gated thumbnails and truthful import-hash status."""
        self.require(project_id, WorkflowAction.REVIEW)
        from mcm_solarcheck.services.review_image_preview import (
            preview_pending_finding_image_evidence,
        )
        return preview_pending_finding_image_evidence(
            self.database, project_id, finding_id, selected_folder,
        )

    def review_pending_finding(
        self, project_id: str, finding_id: str, *,
        status: ReviewStatus, reviewer: str, note: str | None = None,
    ):
        """Decide an existing pending finding using the established expert gate.

        Never accept caller-created findings as evidence. An atomic SQLite
        condition prevents repeated/stale decisions and cross-project updates.
        """
        self.require(project_id, WorkflowAction.REVIEW)
        if not isinstance(status, ReviewStatus) or status is ReviewStatus.UNREVIEWED:
            raise ValueError("explicit completed expert decision required")
        if not isinstance(finding_id, str) or not finding_id.strip():
            raise ValueError("stored finding ID required")
        finding = self.database.load_finding_for_review(project_id, finding_id)
        if finding.reviewer_status != ReviewStatus.UNREVIEWED.value:
            raise ValueError("finding has already been reviewed")
        reviewed, audit = review_finding(
            finding, status=status, reviewer=reviewer, note=note,
        )
        self.database.save_review(
            audit, project_id=project_id, require_unreviewed=True,
            reviewed_metadata=reviewed.metadata,
        )
        return reviewed, audit, self.state(project_id)

    def review_finding(
        self,
        project_id: str,
        finding,
        *,
        status: ReviewStatus,
        reviewer: str,
        note: str | None = None,
        reviewed_at_utc=None,
    ):
        """Apply and persist a human review only through the workflow boundary."""
        self.require(project_id, WorkflowAction.REVIEW)
        reviewed, audit = review_finding(
            finding,
            status=status,
            reviewer=reviewer,
            note=note,
            reviewed_at_utc=reviewed_at_utc,
        )
        self.database.save_review(audit, project_id=project_id)
        return reviewed, audit, self.state(project_id)


    def prepare_report(
        self,
        project_id: str,
        report_id: str,
        inspection_started_at,
        *,
        release_status: str = "draft",
        asset_dir=None,
        operator_profile=None,
    ):
        """Assemble a report only when persisted workflow evidence permits it."""
        self.require(project_id, WorkflowAction.PREPARE_REPORT)
        if release_status == "released":
            profile = self.project_profile(project_id)
            if profile is None or profile.site_timezone is None:
                raise ValueError("released report requires explicit project site timezone")
        return assemble_inspection_report(
            self.database,
            project_id,
            report_id,
            inspection_started_at,
            release_status=release_status,
            asset_dir=asset_dir,
            operator_profile=operator_profile,
        )


    def export_offline_draft(
        self,
        project_id: str,
        report_id: str,
        inspection_started_at,
        destination: str | Path,
        *,
        capabilities: ProductCapabilities,
    ) -> Path:
        """Safely publish a freshly assembled, *unreleased* local report draft.

        Recheck persisted workflow/product restrictions on every invocation,
        generate inside a private temporary directory, then exclusively create
        the destination. Never overwrite an existing file or an original photo.
        """
        if capabilities != OFFLINE_DESKTOP:
            raise PermissionError("offline draft export requires offline desktop entitlement")
        destination = Path(destination)
        if destination.suffix.lower() not in (".pdf", ".odt", ".docx"):
            raise ValueError("draft report output must be PDF, ODT or DOCX")
        if not destination.is_absolute():
            raise ValueError("draft report destination must be an absolute local path")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"destination already exists: {destination}")
        parent = destination.parent
        if not parent.is_dir():
            raise ValueError("draft report destination directory must exist")
        if any(part.is_symlink() for part in (parent, *parent.parents)):
            raise ValueError("draft report destination cannot traverse symbolic links")

        availability = self.output_availability(
            project_id, capabilities, ProductOperation.EXPORT,
        )
        if not availability.allowed:
            raise ValueError("export action is blocked: " + "; ".join(availability.blockers))
        report = self.prepare_report(
            project_id, report_id, inspection_started_at, release_status="draft",
        )
        if report.project_id != project_id or report.release_status != "draft":
            raise ValueError("draft report identity or release status mismatch")

        with TemporaryDirectory(prefix=".solarcheck-draft-", dir=parent) as workspace:
            staged = Path(workspace) / ("report" + destination.suffix.lower())
            # Keep the existing service as the single report/renderer boundary.
            self.export_report(project_id, capabilities, report, staged)
            created = False
            try:
                with staged.open("rb") as source:
                    with destination.open("xb") as target:
                        created = True
                        shutil.copyfileobj(source, target, length=1024 * 1024)
            except BaseException:
                # Never delete the user's existing file: only our own
                # exclusively created, incomplete destination can be removed.
                if created:
                    destination.unlink(missing_ok=True)
                raise
        return destination

    def export_report(
        self,
        project_id: str,
        capabilities: ProductCapabilities,
        report,
        destination: str | Path,
        *,
        format: str | None = None,
        banner_path: str | Path | None = None,
    ):
        """Export only after both persisted workflow and product gates allow it."""
        if report.project_id != project_id:
            raise ValueError("report project does not match active project")
        availability = self.output_availability(
            project_id, capabilities, ProductOperation.EXPORT
        )
        if not availability.allowed:
            reasons = "; ".join(availability.blockers)
            raise ValueError(f"export action is blocked: {reasons}")
        return export_report(
            report,
            destination,
            format=format,
            banner_path=banner_path,
        )
