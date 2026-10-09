"""Standard-library HTTP adapter for SolarCheck email verification."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
import json
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from mcm_solarcheck.services.online_registration_controller import RegistrationRequest

from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


MAX_REGISTRATION_BODY_BYTES = 16 * 1024
MAX_PROJECT_UPLOAD_BYTES = 250 * 1024 * 1024
REGISTRATION_FIELDS = ("user_id", "display_name", "email", "street", "postal_code", "city", "password")
LOGIN_FIELDS = ("user_id", "password")
PROJECT_FIELDS = ("project_id", "name", "capacity_kwp")


def verification_handler(
    endpoint: EmailVerificationEndpoint,
    registration_controller=None,
    login_service=None,
    session_service=None,
    secure_cookies: bool = False,
    customer_entry=None,
    project_service=None,
    project_pricing_service=None,
    project_creation_service=None,
    project_upload_service=None,
    project_processing_service=None,
    compute_job_service=None,
    max_parallel_compute_jobs: int = 2,
    training_consent_service=None,
    upload_attempt_store=None,
) -> type[BaseHTTPRequestHandler]:
    """Bind the transport-neutral verification endpoint to HTTP GET requests."""
    from mcm_solarcheck.services.compute_jobs import ComputeCapacity
    compute_capacity = ComputeCapacity(max_parallel_compute_jobs)

    class VerificationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._respond(
                    200,
                    "SolarCheck Online – Anmeldung und Registrierung werden hier bereitgestellt.",
                )
                return
            if parsed.path in ("/app", "/api/runtime"):
                if session_service is None or customer_entry is None or project_service is None:
                    self._respond(404, "Not Found")
                    return
                try:
                    user_id = self._require_customer_user()
                except PermissionError:
                    self._respond(401, "online session is invalid")
                    return
                try:
                    customer_entry(user_id)
                except (PermissionError, RuntimeError, ValueError):
                    self._respond(403, "online customer entry is not available")
                    return
                if parsed.path == "/api/runtime":
                    self._respond_json(200, {"mode": "online", "features_ready": False})
                else:
                    from shared_ui.server import UI_FILE
                    body = UI_FILE.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                return
            if parsed.path == "/customer-entry" and session_service is not None and customer_entry is not None:
                self._handle_customer_entry()
                return
            if parsed.path == "/api/compute-job" and session_service is not None and customer_entry is not None and compute_job_service is not None:
                self._handle_compute_job_status(parsed)
                return
            if parsed.path == "/api/projects" and session_service is not None and customer_entry is not None and project_service is not None:
                self._handle_projects_json()
                return
            if parsed.path == "/projects" and session_service is not None and customer_entry is not None and project_service is not None:
                self._handle_projects()
                return
            if parsed.path == "/project-price" and session_service is not None and customer_entry is not None and project_pricing_service is not None:
                self._handle_project_price(parsed)
                return
            if parsed.path != "/verify-email":
                self._respond(404, "Not Found")
                return
            token = parse_qs(parsed.query).get("token", [None])[0]
            result = endpoint.verify(token)
            self._respond(result.status_code, result.message)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/login" and login_service is not None:
                self._handle_login()
                return
            if parsed.path == "/logout" and session_service is not None:
                self._handle_logout()
                return
            if parsed.path == "/projects" and session_service is not None and customer_entry is not None and project_creation_service is not None:
                self._handle_create_project()
                return
            if parsed.path == "/api/training-consent-withdraw" and session_service is not None and customer_entry is not None and training_consent_service is not None:
                self._handle_training_consent_withdraw()
                return
            if parsed.path == "/project-upload" and session_service is not None and customer_entry is not None and project_upload_service is not None:
                self._handle_project_upload()
                return
            if parsed.path == "/api/compute-job-start" and session_service is not None and customer_entry is not None and compute_job_service is not None:
                self._handle_start_compute_job(parsed)
                return
            if parsed.path == "/api/compute-jobs" and session_service is not None and customer_entry is not None and project_service is not None and compute_job_service is not None:
                self._handle_create_compute_job()
                return
            if parsed.path == "/api/project-process" and session_service is not None and customer_entry is not None and project_processing_service is not None:
                self._handle_project_process(parsed, as_json=True)
                return
            if parsed.path == "/project-process" and session_service is not None and customer_entry is not None and project_processing_service is not None:
                self._handle_project_process(parsed)
                return
            if parsed.path != "/register" or registration_controller is None:
                self._respond(404, "Not Found")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "registration content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "registration data is invalid")
                return
            if length <= 0:
                self._respond(400, "registration data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "registration data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in REGISTRATION_FIELDS):
                    raise ValueError("registration fields must occur exactly once")
                field = lambda name: form[name][0]
                message = registration_controller.register(
                    RegistrationRequest(
                        user_id=field("user_id"),
                        display_name=field("display_name"),
                        email=field("email"),
                        street=field("street"),
                        postal_code=field("postal_code"),
                        city=field("city"),
                        password=field("password"),
                    )
                )
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "registration data is invalid")
                return
            self._respond(202, message)

        def _handle_compute_job_status(self, parsed) -> None:
            try:
                user_id = self._require_customer_user()
                customer_entry(user_id)
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            query = parse_qs(parsed.query)
            projects, jobs = query.get("project_id", []), query.get("job_id", [])
            if len(projects) != 1 or not projects[0].strip() or len(jobs) != 1 or not jobs[0].strip():
                self._respond(400, "job query is invalid")
                return
            project_id, job_id = projects[0].strip(), jobs[0].strip()
            try:
                job = compute_job_service.get(job_id, user_id=user_id, project_id=project_id)
            except (PermissionError, KeyError):
                self._respond(404, "job is not available")
                return
            self._respond_json(200, {"project_id": project_id, "job_id": job.job_id, "status": job.status.value})

        def _handle_start_compute_job(self, parsed) -> None:
            from mcm_solarcheck.services.compute_jobs import ComputeJobStatus
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            query = parse_qs(parsed.query)
            projects, jobs = query.get("project_id", []), query.get("job_id", [])
            if len(projects) != 1 or not projects[0].strip() or len(jobs) != 1 or not jobs[0].strip():
                self._respond(400, "job query is invalid")
                return
            project_id, job_id = projects[0].strip(), jobs[0].strip()
            try:
                current = compute_job_service.get(job_id, user_id=user_id, project_id=project_id)
                if current.status is ComputeJobStatus.QUEUED:
                    current = compute_job_service.start(job_id, user_id=user_id, project_id=project_id, capacity=compute_capacity)
            except (PermissionError, KeyError):
                self._respond(404, "job is not available")
                return
            except (OSError, RuntimeError):
                self._respond(503, "job service is not available")
                return
            self._respond_json(200, {"project_id": project_id, "job_id": current.job_id, "status": current.status.value})

        def _handle_create_compute_job(self) -> None:
            from uuid import uuid4
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
                self._respond(415, "job content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "job data is invalid")
                return
            if length <= 0 or length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(400 if length <= 0 else 413, "job data is invalid")
                return
            try:
                form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
                project_ids = form.get("project_id", [])
                if len(project_ids) != 1 or not project_ids[0].strip():
                    raise ValueError("project id required")
                project_id = project_ids[0].strip()
                if not any(p.project_id == project_id for p in project_service.projects_for_customer(user_id)):
                    self._respond(404, "project is not available")
                    return
                job = compute_job_service.create(job_id=uuid4().hex, user_id=user_id, project_id=project_id)
                job = compute_job_service.start(job.job_id, user_id=user_id, project_id=project_id, capacity=compute_capacity)
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "job data is invalid")
                return
            except PermissionError:
                self._respond(403, "job creation is not permitted")
                return
            except (OSError, RuntimeError, KeyError):
                self._respond(503, "job service is not available")
                return
            self._respond_json(201, {"project_id": project_id, "job_id": job.job_id, "status": job.status.value})

        def _handle_project_process(self, parsed, *, as_json: bool = False) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return

            query = parse_qs(parsed.query)
            project_ids = query.get("project_id", [])
            job_ids = query.get("job_id", [])
            if len(project_ids) != 1 or not project_ids[0].strip():
                self._respond(400, "project id is invalid")
                return
            if len(job_ids) != 1 or not job_ids[0].strip():
                self._respond(400, "job id is invalid")
                return
            project_id = project_ids[0].strip()
            job_id = job_ids[0].strip()
            try:
                from mcm_solarcheck.services.project_processing import ProjectProcessingRequest

                result = project_processing_service.process(
                    ProjectProcessingRequest(user_id, project_id, job_id)
                )
                if attempt_id is not None:
                    upload_attempt_store.finish(attempt_id, succeeded=True)
            except PermissionError:
                self._respond(404, "project is not available")
                return
            except __import__(
                "mcm_solarcheck.services.project_processing",
                fromlist=["ProjectProcessingConflict"],
            ).ProjectProcessingConflict:
                self._respond(409, "project processing is already running")
                return
            except ValueError:
                self._respond(400, "project processing request is invalid")
                return
            except (OSError, RuntimeError):
                self._respond(503, "online project processing is not available")
                return
            if as_json:
                self._respond_json(200, {
                    "project_id": project_id,
                    "job_id": job_id,
                    "state": result.state.value,
                    "imported_thermal_frames": result.imported_thermal_frames,
                    "paired_frames": result.paired_frames,
                    "import_failures": result.import_failures,
                })
                return
            self._respond(
                200,
                (
                    f"Projekt verarbeitet: {project_id}; "
                    f"Thermalbilder: {result.imported_thermal_frames}; "
                    f"Paare: {result.paired_frames}; "
                    f"Importfehler: {result.import_failures}"
                ),
                headers={"Cache-Control": "no-store"},
            )

        def _same_origin_request(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return False
            expected_host = self.headers.get("Host", "")
            parsed_origin = urlparse(origin)
            return (
                parsed_origin.scheme in ("http", "https")
                and parsed_origin.netloc == expected_host
                and not parsed_origin.username
                and not parsed_origin.password
                and not parsed_origin.path
                and not parsed_origin.query
                and not parsed_origin.fragment
            )

        def _handle_training_consent_withdraw(self) -> None:
            if not self._same_origin_request():
                self._respond(403, "cross-origin consent withdrawal is forbidden")
                return
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            project_id = self.headers.get("X-SolarCheck-Project-Id", "").strip()
            if not project_id or self.headers.get("Content-Length", "0") != "0":
                self._respond(400, "withdrawal request is invalid")
                return
            try:
                training_consent_service.withdraw(customer_id=user_id, project_id=project_id)
            except PermissionError:
                self._respond(404, "project is not available")
                return
            except (ValueError, OSError, RuntimeError):
                self._respond(503, "training consent withdrawal is unavailable")
                return
            self._respond(200, "Trainingseinwilligung widerrufen", headers={"Cache-Control": "no-store"})

        def _handle_project_upload(self) -> None:
            if self.headers.get("Origin") and not self._same_origin_request():
                self._respond(403, "cross-origin project upload is forbidden")
                return
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return

            project_id = self.headers.get("X-SolarCheck-Project-Id", "").strip()
            filename = self.headers.get("X-SolarCheck-Filename", "").strip()
            content_type = self.headers.get("Content-Type", "")
            consent_choice = self.headers.get("X-SolarCheck-Training-Consent", "declined")
            if consent_choice not in ("granted", "declined"):
                self._respond(400, "training consent choice is invalid")
                return
            if consent_choice == "granted" and training_consent_service is None:
                self._respond(503, "training consent recording is unavailable")
                return
            if not project_id or not filename or not content_type:
                self._respond(400, "upload metadata is invalid")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "upload data is invalid")
                return
            if length <= 0:
                self._respond(400, "upload data is invalid")
                return
            if length > MAX_PROJECT_UPLOAD_BYTES:
                self._respond(413, "upload data is too large")
                return

            try:
                content = self.rfile.read(length)
                if len(content) != length:
                    self._respond(400, "upload data is incomplete")
                    return

                # Fail closed: invalidate any earlier grant before changing project files.
                # A failed upload or later audit write cannot leave that grant active.
                if training_consent_service is not None:
                    training_consent_service.withdraw(customer_id=user_id, project_id=project_id)

                from mcm_solarcheck.services.project_upload import ProjectUploadRequest

                attempt_id = None
                if upload_attempt_store is not None:
                    attempt_id = upload_attempt_store.begin(
                        customer_id=user_id, project_id=project_id, filename=filename
                    )
                upload = project_upload_service.upload(
                    ProjectUploadRequest(
                        customer_id=user_id,
                        project_id=project_id,
                        filename=filename,
                        content_type=content_type,
                        content=content,
                    )
                )
            except PermissionError:
                self._respond(404, "project is not available")
                return
            except ValueError:
                self._respond(400, "upload data is invalid")
                return
            except (OSError, RuntimeError):
                self._respond(503, "online upload is not available")
                return
            if training_consent_service is not None:
                try:
                    if consent_choice == "granted":
                        training_consent_service.grant(customer_id=user_id, project_id=project_id)
                    else:
                        training_consent_service.withdraw(customer_id=user_id, project_id=project_id)
                except (PermissionError, ValueError, OSError, RuntimeError):
                    self._respond(503, "upload saved but training consent recording failed; do not use images for training")
                    return
            self._respond(
                201,
                f"Upload gespeichert: {upload.filename} ({upload.size_bytes} Bytes)",
                headers={"Cache-Control": "no-store"},
            )

        def _handle_create_project(self) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "project content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "project data is invalid")
                return
            if length <= 0:
                self._respond(400, "project data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "project data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in PROJECT_FIELDS):
                    raise ValueError("project fields must occur exactly once")
                from mcm_solarcheck.services.project_creation import CreateProjectRequest

                project = project_creation_service.create(
                    CreateProjectRequest(
                        customer_id=user_id,
                        project_id=form["project_id"][0],
                        name=form["name"][0],
                        capacity_kwp=Decimal(form["capacity_kwp"][0]),
                    )
                )
            except (UnicodeDecodeError, InvalidOperation, ValueError):
                self._respond(400, "project data is invalid")
                return
            except (PermissionError, RuntimeError):
                self._respond(503, "online project could not be created")
                return
            self._respond(
                201,
                f"Projekt erstellt: {project.project_id}: {project.name}",
                headers={"Cache-Control": "no-store"},
            )

        def _require_customer_user(self) -> str:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is None:
                    raise PermissionError("online session is invalid")
                user_id = session_service.require_user(morsel.value)
            except (CookieError, PermissionError, ValueError) as exc:
                raise PermissionError("online session is invalid") from exc
            return user_id

        def _handle_project_price(self, parsed) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            project_ids = parse_qs(parsed.query).get("project_id", [])
            if len(project_ids) != 1 or not project_ids[0].strip():
                self._respond(400, "project id is invalid")
                return
            try:
                from mcm_solarcheck.services.project_pricing import ProjectPricingRequest

                snapshot = project_pricing_service.price(
                    ProjectPricingRequest(user_id, project_ids[0])
                )
            except PermissionError:
                self._respond(404, "project is not available")
                return
            except (RuntimeError, TypeError, ValueError):
                self._respond(503, "online project price is not available")
                return
            message = (
                f"{project_ids[0]}: {snapshot.net_total} EUR netto, "
                f"{snapshot.gross_total} EUR brutto "
                f"(Preisregel {snapshot.rule_version})"
            )
            self._respond(200, message, headers={"Cache-Control": "no-store"})

        def _handle_projects_json(self) -> None:
            """JSON projection behind the existing cookie session and customer gate."""
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond_json(401, {"error": "online session is invalid"})
                return
            try:
                from shared_ui.online_access import authorized_online_projects
                projects = authorized_online_projects(
                    user_id, customer_entry=customer_entry, project_service=project_service
                )
            except (PermissionError, RuntimeError, ValueError):
                self._respond_json(403, {"error": "online customer entry is not available"})
                return
            except (AttributeError, TypeError):
                self._respond_json(503, {"error": "online projects are not available"})
                return
            self._respond_json(200, {"projects": projects})

        def _respond_json(self, status_code: int, value: dict) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle_projects(self) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            try:
                projects = tuple(project_service.projects_for_customer(user_id))
                message = "Keine Projekte vorhanden." if not projects else "\n".join(
                    f"{project.project_id}: {project.name}" for project in projects
                )
            except (AttributeError, PermissionError, RuntimeError, TypeError, ValueError):
                self._respond(503, "online projects are not available")
                return
            self._respond(200, message, headers={"Cache-Control": "no-store"})

        def _handle_customer_entry(self) -> None:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is None:
                    raise PermissionError("online session is invalid")
                user_id = session_service.require_user(morsel.value)
            except (CookieError, PermissionError, ValueError):
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            self._respond(200, "SolarCheck Online Kundenzugang freigegeben.")

        def _handle_logout(self) -> None:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is not None and morsel.value:
                    session_service.revoke(morsel.value)
            except (CookieError, ValueError):
                pass
            cookie = (
                "solarcheck_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                + ("; Secure" if secure_cookies else "")
            )
            self._respond(200, "Abmeldung erfolgreich.", headers={"Set-Cookie": cookie})

        def _handle_login(self) -> None:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "login content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "login data is invalid")
                return
            if length <= 0:
                self._respond(400, "login data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "login data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in LOGIN_FIELDS):
                    raise ValueError("login fields must occur exactly once")
                user_id = login_service.login(
                    form["user_id"][0],
                    form["password"][0],
                )
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "login data is invalid")
                return
            except PermissionError:
                self._respond(401, "invalid online login")
                return
            if session_service is None:
                self._respond(200, f"Anmeldung erfolgreich: {user_id}")
                return
            session = session_service.create(user_id)
            remaining = int(
                (session.expires_at - datetime.now(timezone.utc)).total_seconds()
            )
            if remaining <= 0:
                session_service.revoke(session.token)
                self._respond(500, "online session could not be created")
                return
            cookie = (
                f"solarcheck_session={session.token}; Path=/; HttpOnly; SameSite=Strict"
                f"; Max-Age={remaining}"
                + ("; Secure" if secure_cookies else "")
            )
            self._respond(200, "Anmeldung erfolgreich.", headers={"Set-Cookie": cookie})

        def _respond(self, status_code: int, message: str, *, headers=None) -> None:
            if status_code >= 400:
                next_steps = {
                    400: "Bitte prüfen Sie Ihre Eingaben und versuchen Sie es erneut.",
                    401: "Bitte melden Sie sich erneut an.",
                    403: "Bitte prüfen Sie Ihren Kundenzugang oder wenden Sie sich an den SolarCheck-Support.",
                    404: "Bitte prüfen Sie die Projektauswahl oder kehren Sie zur Projektübersicht zurück.",
                    413: "Bitte reduzieren Sie die Datenmenge und versuchen Sie es erneut.",
                    415: "Bitte verwenden Sie das für diese Funktion vorgesehene Datenformat.",
                    500: "Bitte versuchen Sie es später erneut. Falls der Fehler bestehen bleibt, wenden Sie sich an den SolarCheck-Support.",
                    503: "Bitte versuchen Sie es später erneut.",
                }
                next_step = next_steps.get(
                    status_code,
                    "Bitte versuchen Sie es erneut oder wenden Sie sich an den SolarCheck-Support.",
                )
                content = (
                    f"<h1>SolarCheck – Fehler {status_code}</h1>"
                    f"<p>{escape(message)}</p>"
                    f"<p>{escape(next_step)}</p>"
                )
            else:
                content = f"<h1>SolarCheck</h1><p>{escape(message)}</p>"
            body = (
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                "<title>SolarCheck</title></head><body>"
                f"{content}</body></html>"
            ).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return VerificationHandler


def build_verification_server(
    endpoint: EmailVerificationEndpoint,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    server_factory: Callable[..., ThreadingHTTPServer] = ThreadingHTTPServer,
    registration_controller=None,
    login_service=None,
    session_service=None,
    secure_cookies: bool = False,
    customer_entry=None,
    project_service=None,
    project_pricing_service=None,
    project_creation_service=None,
    project_upload_service=None,
    project_processing_service=None,
    compute_job_service=None,
    max_parallel_compute_jobs: int = 2,
    training_consent_service=None,
    upload_attempt_store=None,
) -> ThreadingHTTPServer:
    """Build a local/test HTTP server without owning its process lifecycle."""
    return server_factory(
        (host, port),
        verification_handler(
            endpoint,
            registration_controller,
            login_service,
            session_service,
            secure_cookies,
            customer_entry,
            project_service,
            project_pricing_service,
            project_creation_service,
            project_upload_service,
            project_processing_service,
            compute_job_service,
            max_parallel_compute_jobs,
            training_consent_service,
            upload_attempt_store,
        ),
    )
