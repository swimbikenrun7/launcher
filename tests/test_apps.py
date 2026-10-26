import socket
from pathlib import Path

import pytest

from launcher.apps import AppsFileError, is_running, load_apps

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
