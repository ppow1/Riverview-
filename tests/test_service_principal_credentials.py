# RIVERVIEW~ Controlled Source
# File: tests/test_service_principal_credentials.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Verify protected ChatGPT principal credential storage and fixed registration authorization.
"""Tests for the fixed-path, server-only ChatGPT principal credential sink."""

import os
from pathlib import Path
import stat
import tempfile

import pytest

from riverview_core.institutional_authority.service_principal_credentials import (
    CredentialDestinationUnavailable,
    ProtectedChatGPTCredentialStore,
)


def test_write_ahead_credential_is_private_and_reused_for_retry():
    with tempfile.TemporaryDirectory() as root:
        os.chmod(root, 0o700)
        store = ProtectedChatGPTCredentialStore(Path(root) / "service-chatgpt.credential")
        assert store.available()
        with store.registration_lock():
            first = store.load_or_create()
        info = store.path.stat()
        assert stat.S_IMODE(info.st_mode) == 0o400
        assert info.st_uid == os.geteuid()
        assert store.path.read_text().strip() == first
        with store.registration_lock():
            second = store.load_or_create()
        assert second == first
        assert list(Path(root).glob("*.tmp")) == []


def test_store_rejects_permissive_directory_and_symlink_credential():
    with tempfile.TemporaryDirectory() as root:
        os.chmod(root, 0o755)
        store = ProtectedChatGPTCredentialStore(Path(root) / "service-chatgpt.credential")
        assert not store.available()
        with pytest.raises(CredentialDestinationUnavailable):
            store.load_or_create()

    with tempfile.TemporaryDirectory() as root:
        os.chmod(root, 0o700)
        path = Path(root) / "service-chatgpt.credential"
        target = Path(root) / "target"
        target.write_text("x" * 48)
        path.symlink_to(target)
        store = ProtectedChatGPTCredentialStore(path)
        assert not store.available()


def test_adapter_uses_exact_identity_manage_and_never_returns_one_time_credential():
    from riverview_core.institutional_authority.comms5_adapter import (
        Comms5DelegationAuthorityAdapter,
    )

    class Registry:
        def __init__(self):
            self.authorization = []
            self.creation = None

        def authorize(self, token, action, scope):
            self.authorization.append((token, action, scope))
            return {"principal_id": "steward:camrui", "principal_kind": "steward"}

        def create_principal(self, token, principal_id, principal_kind, *, credential):
            self.creation = (token, principal_id, principal_kind, credential)
            return credential

    with tempfile.TemporaryDirectory() as root:
        os.chmod(root, 0o700)
        registry = Registry()
        adapter = object.__new__(Comms5DelegationAuthorityAdapter)
        adapter._registry = registry
        adapter._steward_token = "s" * 48
        adapter._steward_principal_id = "steward:camrui"
        adapter._chatgpt_credential_store = ProtectedChatGPTCredentialStore(
            Path(root) / "service-chatgpt.credential")
        adapter._authenticated_steward = lambda: "steward:camrui"
        adapter.registered_target = lambda principal_id, *, principal_kind=None: False
        result = adapter.register_chatgpt_service_principal()
        assert registry.authorization == [("s" * 48, "identity.manage", "institution")]
        assert registry.creation[:3] == (
            "s" * 48, "service:chatgpt", "service")
        assert registry.creation[3] == adapter._chatgpt_credential_store.path.read_text().strip()
        assert result == {"status": "registered", "principal_id": "service:chatgpt",
                          "principal_kind": "service", "credential_stored": True}
        assert registry.creation[3] not in repr(result)
