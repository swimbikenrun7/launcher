"""Load apps.yaml, check whether each app is running, and start apps."""

import os
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

REQUIRED_FIELDS = ("name", "description", "icon", "path", "command", "port")


class AppsFileError(ValueError):
    """apps.yaml is missing, malformed, or has a bad entry."""


@dataclass(frozen=True)
class App:
    name: str
    description: str
    icon: str
    path: Path
    command: str
    port: int

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"


def load_apps(yaml_path: Path) -> list[App]:
    """Read the app list from apps.yaml. Raises AppsFileError with a readable message."""
    try:
        data = yaml.safe_load(Path(yaml_path).read_text())
    except FileNotFoundError as e:
        raise AppsFileError(f"Can't find {yaml_path}") from e
    except yaml.YAMLError as e:
        raise AppsFileError(f"{yaml_path} isn't valid YAML: {e}") from e

    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise AppsFileError(f"{yaml_path} needs a top-level 'apps:' list")

    apps = []
    ports_seen = {}
    for i, entry in enumerate(data["apps"], start=1):
        if not isinstance(entry, dict):
            raise AppsFileError(f"App #{i} should be a set of 'key: value' lines")
        missing = [f for f in REQUIRED_FIELDS if entry.get(f) in (None, "")]
        if missing:
            label = entry.get("name") or f"#{i}"
            raise AppsFileError(f"App {label} is missing: {', '.join(missing)}")
        port = entry["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise AppsFileError(f"App {entry['name']} has a bad port: {port!r}")
        if port in ports_seen:
            raise AppsFileError(f"Apps {ports_seen[port]} and {entry['name']} both use port {port}")
        ports_seen[port] = entry["name"]
        apps.append(
            App(
                name=str(entry["name"]),
                description=str(entry["description"]),
                icon=str(entry["icon"]),
                path=Path(str(entry["path"])).expanduser(),
                command=str(entry["command"]),
                port=port,
            )
        )
    return apps


def is_running(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """True if something is listening on the port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class AppStartError(RuntimeError):
    """An app couldn't be started."""


def log_path(app: App, logs_dir: Path) -> Path:
    slug = "".join(c if c.isalnum() else "-" for c in app.name.lower())
    return logs_dir / f"{slug}.log"


def child_env() -> dict[str, str]:
    """Our environment minus the launcher's own .venv, so apps use their own."""
    env = os.environ.copy()
    venv = env.pop("VIRTUAL_ENV", None) or sys.prefix
    venv_bin = str(Path(venv) / "bin")
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if p != venv_bin)
    return env


def start_app(app: App, logs_dir: Path) -> subprocess.Popen:
    """Run the app's command in its folder, in the background, logging to logs_dir.

    The app keeps running if the launcher is closed.
    """
    if not app.path.is_dir():
        raise AppStartError(f"{app.name}: folder {app.path} doesn't exist")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log = log_path(app, logs_dir)
    with log.open("w") as out:
        try:
            return subprocess.Popen(
                shlex.split(app.command),
                cwd=app.path,
                env=child_env(),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as e:
            raise AppStartError(f"{app.name}: couldn't run '{app.command}' ({e})") from e


def wait_until_running(app: App, proc: subprocess.Popen, timeout: float = 20) -> bool:
    """Wait for the app's port to answer. False if it exits or times out first."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_running(app.port):
            return True
        if proc.poll() is not None:
            return False
        time.sleep(0.25)
    return False


def tail(path: Path, lines: int = 20) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except FileNotFoundError:
        return ""
