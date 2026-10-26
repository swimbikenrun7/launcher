import os
import socket
import sys
from pathlib import Path

import pytest

from launcher.apps import (
    App,
    AppsFileError,
    AppStartError,
    child_env,
    is_running,
    load_apps,
    log_path,
    start_app,
    tail,
    wait_until_running,
)

REPO_APPS_FILE = Path(__file__).parent.parent / "apps.yaml"

GOOD_ENTRY = """\
  - name: Demo
    description: A demo app
    icon: "x"
    path: ~/somewhere
    command: run it
    port: 9001
"""


def write(tmp_path, text):
    f = tmp_path / "apps.yaml"
    f.write_text(text)
    return f


def test_real_apps_file_loads():
    apps = load_apps(REPO_APPS_FILE)
    assert [a.port for a in apps] == [8501, 8502, 8503]


def test_loads_fields_and_expands_home(tmp_path):
    (app,) = load_apps(write(tmp_path, "apps:\n" + GOOD_ENTRY))
    assert app.name == "Demo"
    assert app.port == 9001
    assert app.path == Path.home() / "somewhere"
    assert app.url == "http://localhost:9001"


def test_missing_file(tmp_path):
    with pytest.raises(AppsFileError, match="Can't find"):
        load_apps(tmp_path / "nope.yaml")


def test_invalid_yaml(tmp_path):
    with pytest.raises(AppsFileError, match="isn't valid YAML"):
        load_apps(write(tmp_path, "apps: [unclosed"))


def test_no_apps_list(tmp_path):
    with pytest.raises(AppsFileError, match="'apps:' list"):
        load_apps(write(tmp_path, "something_else: 1\n"))


def test_missing_field(tmp_path):
    text = "apps:\n" + GOOD_ENTRY.replace("    port: 9001\n", "")
    with pytest.raises(AppsFileError, match="Demo is missing: port"):
        load_apps(write(tmp_path, text))


@pytest.mark.parametrize("port", ["abc", "0", "70000", "true"])
def test_bad_port(tmp_path, port):
    text = "apps:\n" + GOOD_ENTRY.replace("9001", port)
    with pytest.raises(AppsFileError, match="bad port"):
        load_apps(write(tmp_path, text))


def test_duplicate_port(tmp_path):
    second = GOOD_ENTRY.replace("Demo", "Other")
    with pytest.raises(AppsFileError, match="both use port 9001"):
        load_apps(write(tmp_path, "apps:\n" + GOOD_ENTRY + second))


def test_is_running_true_when_port_listens():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        assert is_running(server.getsockname()[1])


def test_is_running_false_when_nothing_listens():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
    assert not is_running(free_port)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_app(path, command, port=9001):
    return App("My App", "d", "x", Path(path), command, port)


def test_start_app_runs_command_and_waits_for_port(tmp_path):
    port = free_port()
    command = f"{sys.executable} -m http.server {port} --bind 127.0.0.1"
    app = make_app(tmp_path, command, port)
    proc = start_app(app, tmp_path / "logs")
    try:
        assert wait_until_running(app, proc, timeout=10)
        assert is_running(port)
    finally:
        proc.terminate()
        proc.wait()


def test_start_app_reports_early_exit_and_logs_output(tmp_path):
    app = make_app(tmp_path, f"{sys.executable} -c \"print('boom'); raise SystemExit(1)\"")
    proc = start_app(app, tmp_path / "logs")
    assert not wait_until_running(app, proc, timeout=10)
    assert "boom" in tail(log_path(app, tmp_path / "logs"))


def test_start_app_missing_folder(tmp_path):
    with pytest.raises(AppStartError, match="doesn't exist"):
        start_app(make_app(tmp_path / "nope", "true"), tmp_path / "logs")


def test_start_app_missing_program(tmp_path):
    with pytest.raises(AppStartError, match="couldn't run"):
        start_app(make_app(tmp_path, ".venv/bin/streamlit run x.py"), tmp_path / "logs")


def test_child_env_drops_launcher_venv(monkeypatch):
    monkeypatch.setenv("VIRTUAL_ENV", "/x/launcher/.venv")
    monkeypatch.setenv("PATH", f"/x/launcher/.venv/bin{os.pathsep}/usr/bin")
    env = child_env()
    assert "VIRTUAL_ENV" not in env
    assert env["PATH"] == "/usr/bin"
