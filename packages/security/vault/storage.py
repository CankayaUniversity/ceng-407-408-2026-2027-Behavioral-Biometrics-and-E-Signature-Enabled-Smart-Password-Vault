"""Private local JSON vault storage for POSIX and Windows.

The parent directory must be owned/controlled by the current user. All writers
must cooperate using the adjacent .lock file. Windows requires pywin32.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

if os.name == "nt":
    import msvcrt
    try:
        import ntsecuritycon
        import win32api
        import win32con
        import win32file
        import win32security
    except ImportError as exc:
        raise ImportError("Windows vault storage requires pywin32") from exc
else:
    import fcntl


# Win32 CreateFile flag, also needed with pywin32 builds that omit it.
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000


class JsonVaultStorage:
    """Persist one encrypted vault, refusing unsafe files and stale updates."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @staticmethod
    def _set_private(path: Path) -> None:
        if os.name == "nt":
            token = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
            )
            try:
                owner = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            finally:
                token.Close()
            acl = win32security.ACL()
            acl.AddAccessAllowedAce(
                win32security.ACL_REVISION, ntsecuritycon.FILE_ALL_ACCESS, owner
            )
            win32security.SetNamedSecurityInfo(
                str(path),
                win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION
                | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
                None, None, acl, None,
            )
            # The default token owner can be a group. Apply the DACL first
            # so the user has WRITE_OWNER when assigning their own SID.
            win32security.SetNamedSecurityInfo(
                str(path),
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION,
                owner, None, None, None,
            )
        else:
            os.chmod(path, 0o600)

    @staticmethod
    def _check_private(path: Path, info: os.stat_result) -> None:
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Vault path must refer to a regular file")
        if info.st_nlink != 1:
            raise OSError("Unexpected hard links to vault file")
        if os.name == "nt":
            token = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
            )
            try:
                sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            finally:
                token.Close()
            security = win32security.GetNamedSecurityInfo(
                str(path), win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION
                | win32security.DACL_SECURITY_INFORMATION,
            )
            if security.GetSecurityDescriptorOwner() != sid:
                raise PermissionError("Vault file owner mismatch")
            acl = security.GetSecurityDescriptorDacl()
            if acl is None:
                raise PermissionError("Vault file must have a restrictive DACL")
            allowed_for_user = False
            for index in range(acl.GetAceCount()):
                ace = acl.GetAce(index)
                if ace[0][0] == win32security.ACCESS_ALLOWED_ACE_TYPE:
                    if ace[2] != sid:
                        raise PermissionError("Vault file is accessible to another principal")
                    allowed_for_user = True
            if not allowed_for_user:
                raise PermissionError("Vault file has no user access rule")
        else:
            if hasattr(os, "getuid") and info.st_uid != os.getuid():
                raise PermissionError("Vault file is not owned by current user")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise PermissionError("Vault file permissions are unsafe")

    @staticmethod
    def _open_safe(path: Path, *, for_lock: bool = False) -> int:
        """Open a non-reparse regular file, rejecting unsafe metadata."""
        if os.name == "nt":
            handle = win32file.CreateFile(
                str(path),
                win32con.GENERIC_READ | (win32con.GENERIC_WRITE if for_lock else 0),
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None,
                win32con.OPEN_ALWAYS if for_lock else win32con.OPEN_EXISTING,
                _FILE_FLAG_OPEN_REPARSE_POINT,
                None,
            )
            try:
                attributes = win32file.GetFileInformationByHandle(handle)[0]
                if attributes & (win32con.FILE_ATTRIBUTE_REPARSE_POINT | win32con.FILE_ATTRIBUTE_DIRECTORY):
                    raise OSError("Unsafe vault reparse point or directory")
                fd = msvcrt.open_osfhandle(
                    int(handle.Detach()),
                    os.O_BINARY | (os.O_RDWR if for_lock else os.O_RDONLY),
                )
            finally:
                handle.Close()
        else:
            if not hasattr(os, "O_NOFOLLOW"):
                raise OSError("O_NOFOLLOW is required")
            flags = os.O_NOFOLLOW | (os.O_RDWR | os.O_CREAT if for_lock else os.O_RDONLY)
            if hasattr(os, "O_NONBLOCK"):
                flags |= os.O_NONBLOCK
            fd = os.open(path, flags, 0o600)
        try:
            info = os.fstat(fd)
            if for_lock and os.name == "nt":
                # A lock file created in a private directory may inherit broad ACLs.
                # Make it private before validating it; parent folder is trusted.
                JsonVaultStorage._set_private(path)
                info = os.fstat(fd)
            JsonVaultStorage._check_private(path, info)
            return fd
        except BaseException:
            os.close(fd)
            raise

    @contextmanager
    def _writer_lock(self) -> Iterator[None]:
        lock_path = self._path.with_name(self._path.name + ".lock")
        fd = self._open_safe(lock_path, for_lock=True)
        locked = False
        try:
            if os.name == "nt":
                # A permanent byte allows msvcrt to lock a fixed file region.
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                    os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX)
            locked = True
            yield
        finally:
            if locked:
                if os.name == "nt":
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _write_temporary(self, vault: dict[str, Any]) -> Path:
        if not isinstance(vault, dict):
            raise TypeError("vault must be a dictionary")
        payload = json.dumps(vault, ensure_ascii=True, separators=(",", ":"))
        path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._path.parent,
                prefix=".vault-", suffix=".tmp", delete=False,
            ) as target:
                path = Path(target.name)
                self._set_private(path)
                target.write(payload)
                target.flush()
                os.fsync(target.fileno())
            return path
        except BaseException:
            if path is not None:
                path.unlink(missing_ok=True)
            raise

    def create(self, vault: dict[str, Any]) -> None:
        with self._writer_lock():
            temporary = self._write_temporary(vault)
            try:
                # A hard link cannot replace an existing destination.
                os.link(temporary, self._path)
                self._sync_directory()
            finally:
                temporary.unlink(missing_ok=True)

    def update(self, expected: dict[str, Any], vault: dict[str, Any]) -> None:
        if not isinstance(expected, dict) or not isinstance(vault, dict):
            raise TypeError("Vault snapshots must be dictionaries")
        with self._writer_lock():
            if self.read() != expected:
                raise RuntimeError("Vault changed since last read")
            temporary = self._write_temporary(vault)
            try:
                os.replace(temporary, self._path)
                self._sync_directory()
            finally:
                temporary.unlink(missing_ok=True)

    def read(self) -> dict[str, Any]:
        fd = self._open_safe(self._path)
        try:
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                fd = -1
                data = json.load(stream)
        finally:
            if fd >= 0:
                os.close(fd)
        if not isinstance(data, dict):
            raise ValueError("Vault file must contain a JSON object")
        return data

    def _sync_directory(self) -> None:
        if os.name == "nt":
            # Windows does not support POSIX directory fsync through os.open.
            # File contents were fsynced; power-loss rename durability differs.
            return
        if not hasattr(os, "O_DIRECTORY"):
            raise OSError("Directory fsync requires O_DIRECTORY")
        fd = os.open(self._path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
