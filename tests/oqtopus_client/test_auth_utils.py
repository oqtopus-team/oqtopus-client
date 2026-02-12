from __future__ import annotations

import json
import threading
import time
from typing import Any

import pytest

from oqtopus_client.auth_utils import write_api_token_file
from oqtopus_client.auth_utils import _release_lock


def test_write_api_token_file_plain_text(tmp_path: Any) -> None:
    token_file = tmp_path / "token.txt"
    write_api_token_file(token_file, "plain-token")
    assert token_file.read_text(encoding="utf-8").strip() == "plain-token"


def test_write_api_token_file_json(tmp_path: Any) -> None:
    token_file = tmp_path / "token.json"
    write_api_token_file(token_file, "json-token", as_json=True)
    payload = json.loads(token_file.read_text(encoding="utf-8"))
    assert payload["api_token_secret"] == "json-token"


def test_write_api_token_file_is_lock_safe(tmp_path: Any) -> None:
    token_file = tmp_path / "token.txt"
    errors: list[Exception] = []

    def write_token(token: str) -> None:
        try:
            write_api_token_file(token_file, token, lock_timeout=1.0)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    thread_1 = threading.Thread(target=write_token, args=("token-1",))
    thread_2 = threading.Thread(target=write_token, args=("token-2",))
    thread_1.start()
    thread_2.start()
    thread_1.join()
    thread_2.join()

    assert not errors
    assert token_file.read_text(encoding="utf-8").strip() in {"token-1", "token-2"}


def test_write_api_token_file_rejects_empty_token(tmp_path: Any) -> None:
    token_file = tmp_path / "token.txt"
    with pytest.raises(ValueError):
        write_api_token_file(token_file, "   ")


def test_write_api_token_file_times_out_when_lock_is_held(tmp_path: Any) -> None:
    token_file = tmp_path / "token.txt"
    lock_file = token_file.with_suffix(".txt.lock")
    lock_file.write_text("held", encoding="utf-8")

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        write_api_token_file(token_file, "token", lock_timeout=0.01, lock_poll_interval=0.005)
    assert time.monotonic() - started >= 0.01

    lock_file.unlink()


def test_release_lock_ignores_missing_file(tmp_path: Any) -> None:
    missing_lock = tmp_path / "missing.lock"
    _release_lock(missing_lock)
