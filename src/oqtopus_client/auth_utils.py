from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from time import monotonic, sleep


def write_api_token_file(
    api_token_file: str | Path,
    token: str,
    *,
    as_json: bool = False,
    json_key: str = "api_token_secret",
    lock_timeout: float = 10.0,
    lock_poll_interval: float = 0.05,
) -> Path:
    """Write an API token file atomically with cross-process lock protection."""
    token_file = Path(api_token_file)
    lock_path = token_file.with_suffix(token_file.suffix + ".lock")
    _acquire_lock(lock_path, timeout=lock_timeout, poll_interval=lock_poll_interval)
    try:
        payload = token.strip()
        if not payload:
            raise ValueError("token must not be empty.")
        text = json.dumps({json_key: payload}) if as_json else payload
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=token_file.parent,
            delete=False,
        ) as tmp:
            tmp.write(text)
            tmp.write("\n")
            temp_path = Path(tmp.name)
        os.replace(temp_path, token_file)
        return token_file
    finally:
        _release_lock(lock_path)


def _acquire_lock(lock_path: Path, *, timeout: float, poll_interval: float) -> None:
    deadline = monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError as exc:
            if monotonic() >= deadline:
                raise TimeoutError(f"Timed out acquiring lock: {lock_path}") from exc
            sleep(poll_interval)


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
