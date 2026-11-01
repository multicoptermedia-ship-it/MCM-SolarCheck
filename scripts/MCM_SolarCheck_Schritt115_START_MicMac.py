"""Download-folder compatibility starter; delegates to the existing application.

Uses a manually downloaded, fixed source ZIP. No network, package installation,
customer-image reads, database logic or independent GUI lives in this file.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from zipfile import ZipFile

PROGRAM_COMMIT = "a0237d0a2339bda04efeb015ec65a10ae6c058d4"
PROGRAM_ZIP_URL = (
    "https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/"
    + PROGRAM_COMMIT + ".zip"
)
REQUIRED_HASHES = {
    "scripts/start_windows10_offline.ps1": "9c9114c8b20a825da1274af9002b73cfa97be3c72a7bffe2fff581d0f31b6b13",
    "src/mcm_solarcheck/offline/__main__.py": "c4373d34c625f3a716df0799926b99a535a477648f549cdd156c278453539620",
    "src/mcm_solarcheck/gui/micmac_dialog.py": "a06f5ec42ca6031abe47e383af9d22202c913dfa7a1861a5c8eb9acd667d7bbe",
    "src/mcm_solarcheck/services/micmac_orthophotos.py": "098671064cb10fe1de31ecf67071888ed5d3d64f8853b4ff015e21e0c1f85674",
}
READY = ".mcm-source-ready"
SOURCE_SUFFIXES = {".py", ".ps1", ".md", ".yml", ".txt", ".html", ".js"}


def check_program(program: Path) -> bool:
    """Detect incomplete or wrong-version local source, not a digital signature."""
    if not program.is_dir() or program.is_symlink():
        return False
    try:
        if (program / READY).read_text(encoding="ascii") != PROGRAM_COMMIT:
            return False
        return all(
            not (program / name).is_symlink()
            and sha256((program / name).read_bytes()).hexdigest() == digest
            for name, digest in REQUIRED_HASHES.items()
        )
    except OSError:
        return False


def prepare_program(archive: Path, updates: Path) -> Path:
    """Extract only the selected source archive into its own new directory."""
    destination = updates / ("MCM-MicMac-" + PROGRAM_COMMIT[:12])
    if check_program(destination):
        return destination
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("Der vorhandene MicMac-Testordner ist unvollstaendig oder geaendert. Er wird nicht ueberschrieben.")
    with ZipFile(archive) as package:
        infos = package.infolist()
        if package.comment != PROGRAM_COMMIT.encode("ascii"):
            raise RuntimeError("Die Programm-ZIP hat nicht den erwarteten Programmstand.")
        if len(infos) > 5000 or sum(i.file_size for i in infos) > 100 * 1024 * 1024:
            raise RuntimeError("Die Datei entspricht nicht der erwarteten Quellcode-ZIP.")
        expected_root = "MCM-SolarCheck-" + PROGRAM_COMMIT
        files = {}
        seen = set()
        for info in infos:
            path = PurePosixPath(info.filename)
            if (path.is_absolute() or not path.parts or path.parts[0] != expected_root
                    or any(p in ("..", ".git", ".venv") or ":" in p or "\\" in p for p in path.parts)
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise RuntimeError("Die ZIP enthaelt einen unzulaessigen Dateipfad.")
            relative = PurePosixPath(*path.parts[1:])
            if info.is_dir():
                continue
            if relative.suffix.lower() not in SOURCE_SUFFIXES or str(relative).casefold() in seen:
                raise RuntimeError("Nur eindeutige Quellcode-Dateien werden aus der ZIP uebernommen.")
            seen.add(str(relative).casefold())
            files[str(relative)] = info
        for name, digest in REQUIRED_HASHES.items():
            if name not in files or sha256(package.read(files[name])).hexdigest() != digest:
                raise RuntimeError("Programmdateien passen nicht zum geprueften MicMac-Stand.")
        updates.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".mcm-source-", dir=updates))
        try:
            for name, info in files.items():
                target = stage.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
            (stage / READY).write_text(PROGRAM_COMMIT, encoding="ascii")
            stage.rename(destination)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
    return destination


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("Diese Startdatei ist fuer den Windows-10-Auswerterechner vorgesehen.")
    python = Path(sys.executable)
    # F:\MCM-SolarCheck\.venv\Scripts\python.exe -> F:\MCM-SolarCheck
    updates = python.parents[2] / "test-updates"
    program = updates / ("MCM-MicMac-" + PROGRAM_COMMIT[:12])
    if not check_program(program):
        downloads = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"
        archives = list(downloads.glob("MCM-SolarCheck-" + PROGRAM_COMMIT + "*.zip"))
        if not archives:
            raise RuntimeError(
                "Bitte zuerst die Programm-ZIP in Downloads speichern (nicht entpacken):\n" + PROGRAM_ZIP_URL
            )
        archive = max(archives, key=lambda p: p.stat().st_mtime_ns)
        print("Programm-ZIP wird in einen getrennten lokalen Testordner entpackt ...", flush=True)
        program = prepare_program(archive, updates)
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    print("SolarCheck startet mit der vorhandenen Python-Umgebung. Bitte bisherige Projektdatei auswaehlen.", flush=True)
    return subprocess.run(
        [str(powershell), "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File",
         str(program / "scripts/start_windows10_offline.ps1"), "-PythonExe", str(python), "-UseExistingProject"],
        cwd=program, check=False,
    ).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("SolarCheck-Start nicht moeglich: " + str(error), file=sys.stderr)
        raise SystemExit(1)
