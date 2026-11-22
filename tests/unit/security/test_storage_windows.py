"""Windows-specific vault filesystem regression tests (run on Windows CI)."""

import os
from pathlib import Path

import pytest

from packages.security.vault.storage import JsonVaultStorage

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows ACL checks only")


def test_windows_create_read_and_atomic_update(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    storage = JsonVaultStorage(path)
    original = {"records": []}
    updated = {"records": [{"ciphertext": "example"}]}
    storage.create(original)
    assert storage.read() == original
    storage.update(original, updated)
    assert storage.read() == updated
    with pytest.raises(RuntimeError, match="changed"):
        storage.update(original, original)
    with pytest.raises(FileExistsError):
        storage.create(original)


def test_windows_rejects_nonprivate_acl(tmp_path: Path) -> None:
    import ntsecuritycon
    import win32security

    path = tmp_path / "vault.json"
    storage = JsonVaultStorage(path)
    storage.create({"records": []})
    everyone = win32security.CreateWellKnownSid(win32security.WinWorldSid, None)
    security = win32security.GetNamedSecurityInfo(
        str(path), win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
    )
    acl = security.GetSecurityDescriptorDacl()
    acl.AddAccessAllowedAce(
        win32security.ACL_REVISION, ntsecuritycon.FILE_GENERIC_READ, everyone
    )
    win32security.SetNamedSecurityInfo(
        str(path), win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION,
        None, None, acl, None,
    )
    with pytest.raises(PermissionError):
        storage.read()


def test_windows_rejects_reparse_point(tmp_path: Path) -> None:
    target = tmp_path / "real.json"
    storage = JsonVaultStorage(target)
    storage.create({"records": []})
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks require Windows developer mode or privilege")
    with pytest.raises(OSError, match="reparse"):
        JsonVaultStorage(link).read()
