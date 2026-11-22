"""Local JSON storage for encrypted vault envelopes (VLT-02).

This module handles persistence only. Encryption and key handling belong to
VaultService. The destination directory must already exist.
"""

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


class JsonVaultStorage:
    """Persist one vault as JSON, without overwriting an existing vault."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def create(self, vault: dict[str, Any]) -> None:
        """Write an encrypted vault atomically; refuse an existing destination.

        A temporary file is created in the same directory, flushed to disk,
        and hard-linked to the final filename without replacing existing data.
        """
        if not isinstance(vault, dict):
            raise TypeError("vault must be a dictionary")

        payload = json.dumps(vault, ensure_ascii=True, separators=(",", ":"))
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=".vault-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                os.chmod(temporary.name, 0o600)
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())

            # Unlike os.replace(), os.link() fails if the final file exists.
            os.link(temporary_path, self._path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def read(self) -> dict[str, Any]:
        """Load JSON metadata; cryptographic validation belongs to the service."""
        # POSIX mode bits and O_NOFOLLOW do not represent Windows ACLs.
        opener = self._open_private_file if os.name == "posix" else None
        with open(self._path, "r", encoding="utf-8", opener=opener) as source:
            data = json.load(source)
        if not isinstance(data, dict):
            raise ValueError("Vault file must contain a JSON object")
        return data

    @staticmethod
    def _open_private_file(path: str, flags: int) -> int:
        # O_NONBLOCK allows file-type validation without waiting on a FIFO.
        fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            mode = os.fstat(fd).st_mode
            if not stat.S_ISREG(mode):
                raise ValueError("Vault path must be a regular file")
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise PermissionError("Vault file must be accessible only to its owner")
        except BaseException:
            os.close(fd)
            raise
        return fd
