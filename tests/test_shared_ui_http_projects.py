"""HTTP integration checks for the offline-only project listing."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from mcm_solarcheck.offline.composition import build_offline_services
from shared_ui.server import make_handler


def _get(server, path):
    with urlopen("http://127.0.0.1:" + str(server.server_port) + path, timeout=3) as response:
        return response.status, json.load(response)


def test_offline_http_lists_real_projects(tmp_path):
    database = tmp_path / "projects.sqlite3"
    build_offline_services(database).projects.create_project("p1", "Norddach")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("offline", database_path=database))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _get(server, "/api/projects")
        assert status == 200
        assert data == {"projects": [{"id": "p1", "name": "Norddach"}]}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_online_preview_denies_project_listing():
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("online"))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            _get(server, "/api/projects")
        except HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("online preview must reject project listing")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
