import importlib.util
import io
import json
import os
import stat
import sys
from types import SimpleNamespace
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "ntfy_phone_test.py"
SPEC = importlib.util.spec_from_file_location("ntfy_phone_test", SCRIPT)
ntfy_phone_test = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ntfy_phone_test
SPEC.loader.exec_module(ntfy_phone_test)


def protected_file(path: Path, value: str) -> None:
    path.write_text(value)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def fake_root_owned_lstat(path: Path):
    info = os.stat(path)
    return SimpleNamespace(st_mode=info.st_mode, st_uid=0)


def test_main_publishes_private_high_priority_test_without_printing_credentials(tmp_path, monkeypatch, capsys):
    token_file = tmp_path / "token"
    topic_file = tmp_path / "topic"
    protected_file(token_file, "tk-secret-do-not-print")
    protected_file(topic_file, "topic-secret-do-not-print")
    monkeypatch.setattr(ntfy_phone_test, "TOKEN_FILE", token_file)
    monkeypatch.setattr(ntfy_phone_test, "TOPIC_FILE", topic_file)
    monkeypatch.setattr(ntfy_phone_test.os, "geteuid", lambda: 0)
    monkeypatch.setattr(ntfy_phone_test.Path, "lstat", fake_root_owned_lstat)

    class Response(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    class Opener:
        def open(self, request, timeout):
            assert timeout == 15
            assert request.full_url.endswith("/topic-secret-do-not-print")
            assert request.get_header("Authorization") == "Bearer tk-secret-do-not-print"
            assert request.get_header("Priority") == "4"
            assert request.get_header("Title") == "Riverview iPhone notification test"
            assert b"Check delivery with the app in the background or closed" in request.data
            return Response(json.dumps({"id": "message-id-1"}).encode())

    monkeypatch.setattr(ntfy_phone_test.urllib.request, "build_opener", lambda *_: Opener())
    assert ntfy_phone_test.main() == 0
    output = capsys.readouterr().out
    assert "message-id-1" in output
    assert "tk-secret-do-not-print" not in output
    assert "topic-secret-do-not-print" not in output
    assert "local publication only" in output


def test_main_rejects_unprotected_credential_file_without_reading_it(tmp_path, monkeypatch, capsys):
    token_file = tmp_path / "token"
    topic_file = tmp_path / "topic"
    token_file.write_text("do-not-print")
    token_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IROTH)
    protected_file(topic_file, "topic-name")
    monkeypatch.setattr(ntfy_phone_test, "TOKEN_FILE", token_file)
    monkeypatch.setattr(ntfy_phone_test, "TOPIC_FILE", topic_file)
    monkeypatch.setattr(ntfy_phone_test.os, "geteuid", lambda: 0)
    monkeypatch.setattr(ntfy_phone_test.Path, "lstat", fake_root_owned_lstat)
    assert ntfy_phone_test.main() == 1
    error = capsys.readouterr().err
    assert "no delivery is claimed" in error
    assert "do-not-print" not in error


def test_main_requires_root(monkeypatch, capsys):
    monkeypatch.setattr(ntfy_phone_test.os, "geteuid", lambda: 1000)
    assert ntfy_phone_test.main() == 2
    assert "sudo" in capsys.readouterr().err
