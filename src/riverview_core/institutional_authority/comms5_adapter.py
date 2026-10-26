# Revision: 1.1.0
# Changed: 2026-10-26 UTC | RV-ISSUE343-BASE-INTEGRATION | Preserve protected ChatGPT principal registration and add exact host-scoped delegation pairs.
"""Protected adapter for Comms5 delegated grant lifecycle and identity registration.

The adapter owns the manager connection and Steward credential. Neither value
is accepted from MCP arguments or browser requests.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict, make_conninfo

from .registry import AuthorityDenied, AuthorityRegistry
from .service_principal_credentials import (
    CHATGPT_PRINCIPAL_ID, ProtectedChatGPTCredentialStore,
)


_PROMOTION_ACTION = "comms5.proposal.promote"
_PROMOTION_POLICY = "policy:delegation.v1"
_HOST_SCOPED_ACTIONS = {
    "comms5.command.submit.powershell_identity": "host:desktop-ja3rpnq",
    "comms5.command.execute.readonly.powershell_identity.standard": "host:desktop-ja3rpnq",
    "comms5.command.submit.ssh_camrui_hostname": "host:camrui",
    "comms5.command.execute.readonly.ssh_camrui_hostname.standard": "host:camrui",
}
_UNCHANGED = object()
from riverview_core.comms5.delegation_policy import (
    DELEGATED_ACTION, DELEGATED_POLICY, DELEGATED_PROJECT_SCOPE, is_delegable_tool,
)


def _read_credential(path: str | Path, *, systemd_name: str) -> str:
    credential_path = Path(path)
    if credential_path.is_symlink():
        raise RuntimeError("protected_authority_credential_unavailable")
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    is_systemd = (credential_dir is not None and
        credential_path.parent.resolve() == Path(credential_dir).resolve() and
        credential_path.name == systemd_name)
    descriptor = os.open(credential_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                         | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "r", encoding="ascii") as stream:
        metadata = os.fstat(stream.fileno())
        mode = metadata.st_mode & 0o777
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("protected_authority_credential_unavailable")
        if is_systemd:
            valid_mode = mode in {0o400, 0o440}
        else:
            valid_mode = not (mode & 0o077)
        if not valid_mode:
            raise RuntimeError("protected_authority_credential_unavailable")
        value = stream.read().strip()
    if len(value) < 32:
        raise RuntimeError("protected_authority_credential_unavailable")
    return value


def _read_manager_password(path: str | Path, dsn: str, manager_role: str) -> str:
    """Resolve one matching protected pgpass entry without passing its path to libpq."""
    credential_path = Path(path)
    credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    is_systemd = (credential_dir is not None and
        credential_path.parent.resolve() == Path(credential_dir).resolve() and
        credential_path.name == "authority-manager-pgpass")
    descriptor = os.open(credential_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                         | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "r", encoding="ascii") as stream:
        metadata = os.fstat(stream.fileno())
        mode = metadata.st_mode & 0o777
        valid_mode = (mode in {0o400, 0o440} if is_systemd else not (mode & 0o077))
        if not stat.S_ISREG(metadata.st_mode) or not valid_mode:
            raise RuntimeError("protected_authority_credential_unavailable")
        lines = stream.read().splitlines()
    settings = conninfo_to_dict(dsn)
    hosts = (settings.get("host") or "localhost").split(",")
    ports = (settings.get("port") or "5432").split(",")
    databases = [settings.get("dbname") or settings.get("database") or ""]

    def fields(line):
        result, current = [], []
        escaped = False
        for char in line:
            if escaped:
                current.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == ":":
                result.append("".join(current))
                current = []
            else:
                current.append(char)
        if escaped:
            current.append("\\")
        result.append("".join(current))
        return result

    matches = []
    for line in lines:
        if not line or line.startswith("#"):
            continue
        parts = fields(line)
        if len(parts) != 5:
            continue
        host, port, database, user, password = parts
        if (user != manager_role or not password or
                not any(host in {"*", item} for item in hosts) or
                not any(port in {"*", item} for item in ports) or
                not any(database in {"*", item} for item in databases)):
            continue
        matches.append(password)
    if len(set(matches)) != 1:
        raise RuntimeError("protected_authority_credential_unavailable")
    return matches[0]


class Comms5DelegationAuthorityAdapter:
    """Expose only fixed Comms5 grant lifecycle operations over AuthorityRegistry."""

    def __init__(self, dsn: str, *, schema: str, manager_passfile: str | Path,
                 steward_token_file: str | Path, manager_role="riverview_authority_manager",
                 chatgpt_credential_store=None):
        self._steward_token = _read_credential(steward_token_file,
            systemd_name="authority-steward-token")
        # psycopg conninfo safely quotes values and does not expose the password.
        connection_settings = conninfo_to_dict(dsn)
        for option in ("user", "password", "passfile", "service", "servicefile",
                       "application_name"):
            connection_settings.pop(option, None)
        manager_password = _read_manager_password(manager_passfile, dsn, manager_role)
        protected_dsn = make_conninfo(**connection_settings, user=manager_role,
                                      password=manager_password,
                                      application_name="comms5-protected-delegation")
        self._registry = AuthorityRegistry(protected_dsn, schema=schema,
                                           runtime_safe=True)
        self._chatgpt_credential_store = (chatgpt_credential_store or
                                          ProtectedChatGPTCredentialStore())
        try:
            with self._registry.db.transaction():
                with self._registry.db.cursor() as cur:
                    self._registry._path(cur)
                    principal = self._registry._authenticate(cur, self._steward_token)
                    if principal["principal_kind"] != "steward":
                        raise AuthorityDenied("protected Steward context is invalid")
                    self._steward_principal_id = principal["principal_id"]
        except Exception:
            self._registry.close()
            raise

    def close(self):
        self._registry.close()

    def registered_target(self, principal_id: str, *, principal_kind: str | None = None) -> bool:
        """Check an exact target against active canonical identity records."""
        if not isinstance(principal_id, str) or not principal_id:
            return False
        with self._registry.db.transaction():
            with self._registry.db.cursor() as cur:
                self._registry._path(cur)
                cur.execute("SELECT principal_kind,status FROM institutional_principals WHERE principal_id=%s",
                            (principal_id,))
                row = cur.fetchone()
        return bool(row and row["status"] == "active" and
                    (principal_kind is None or row["principal_kind"] == principal_kind))

    def chatgpt_registration_available(self) -> bool:
        return self._chatgpt_credential_store.available()

    def register_chatgpt_service_principal(self):
        """Create only the fixed Comms5 service principal after exact Steward authority.

        Its bearer is written ahead of the registry transaction to the fixed
        protected server-side store. It is never returned to the browser.
        """
        actor_id = self._authenticated_steward()
        actor = self._registry.authorize(
            self._steward_token, "identity.manage", "institution")
        if (actor_id != self._steward_principal_id or
                actor.get("principal_id") != actor_id or
                actor.get("principal_kind") != "steward"):
            raise AuthorityDenied("institutional identity management is not authorized")
        with self._chatgpt_credential_store.registration_lock():
            if self.registered_target(CHATGPT_PRINCIPAL_ID, principal_kind="service"):
                return {"status": "already_registered", "principal_id": CHATGPT_PRINCIPAL_ID,
                        "principal_kind": "service", "credential_stored": True}
            credential = self._chatgpt_credential_store.load_or_create()
            self._registry.create_principal(self._steward_token,
                CHATGPT_PRINCIPAL_ID, "service", credential=credential)
            del credential
            return {"status": "registered", "principal_id": CHATGPT_PRINCIPAL_ID,
                    "principal_kind": "service", "credential_stored": True}

    @staticmethod
    def _validate_action_scope(action, scope_ref, policy_ref):
        if action == DELEGATED_ACTION:
            if (scope_ref != DELEGATED_PROJECT_SCOPE or policy_ref != DELEGATED_POLICY):
                raise AuthorityDenied("Comms5 broad delegation requires Riverview project scope")
            return
        if action == _PROMOTION_ACTION:
            if (not scope_ref.startswith(("project:", "issue:"))
                    or policy_ref != _PROMOTION_POLICY):
                raise AuthorityDenied("Comms5 proposal delegation requires exact project or issue scope")
            return
        expected_host = _HOST_SCOPED_ACTIONS.get(action)
        if expected_host is None or scope_ref != expected_host or policy_ref != DELEGATED_POLICY:
            raise AuthorityDenied("Comms5 delegation action and scope are not an approved pair")

    def request_grant(self, *, requester_id, principal_id, action, scope_ref,
                      policy_ref, request_ref, max_uses=None, valid_until=None,
                      duration_spec=None, idempotency_key):
        self._validate_action_scope(action, scope_ref, policy_ref)
        if action == DELEGATED_ACTION:
            if max_uses is not None:
                raise AuthorityDenied("Comms5 broad delegation requires Riverview scope and unlimited use")
        return self._registry.request_grant(requester_id=requester_id,
            principal_id=principal_id, action=action, scope_ref=scope_ref,
            policy_ref=policy_ref, request_ref=request_ref, max_uses=max_uses,
            valid_until=valid_until, duration_spec=duration_spec,
            idempotency_key=idempotency_key)

    def request_change(self, *, requester_id, grant_id, action, scope_ref,
                       policy_ref, request_ref, max_uses=_UNCHANGED,
                       valid_until=_UNCHANGED, duration_spec=None,
                       change_kind=None, idempotency_key):
        self._validate_action_scope(action, scope_ref, policy_ref)
        if action == DELEGATED_ACTION:
            if (max_uses is not _UNCHANGED and max_uses is not None):
                raise AuthorityDenied("Comms5 broad delegation requires Riverview scope and unlimited use")
        change = {}
        if max_uses is not _UNCHANGED:
            change["max_uses"] = max_uses
        if valid_until is not _UNCHANGED:
            change["valid_until"] = valid_until
        return self._registry.request_change(requester_id=requester_id,
            grant_id=grant_id, action=action, scope_ref=scope_ref,
            policy_ref=policy_ref, request_ref=request_ref,
            duration_spec=duration_spec, change_kind=change_kind,
            idempotency_key=idempotency_key, **change)

    def get_status(self, *, requester_id, request_id=None, grant_id=None):
        return self._registry.get_status(requester_id=requester_id,
                                         request_id=request_id, grant_id=grant_id)

    def surrender_grant(self, *, grantee_id, grant_id, reason_code="grantee_surrendered",
                        idempotency_key):
        return self._registry.surrender_grant(grantee_id=grantee_id,
            grant_id=grant_id, reason_code=reason_code,
            idempotency_key=idempotency_key)

    def decide_request(self, *, authenticated_steward_id, request_id, decision,
                       expected_request_sha256, idempotency_key, approval_ref=None):
        principal = self._authenticated_steward()
        if authenticated_steward_id != principal:
            raise AuthorityDenied("authenticated Steward identity does not match protected credential")
        return self._registry.decide_request(steward_token=self._steward_token,
            request_id=request_id, decision=decision,
            expected_request_sha256=expected_request_sha256,
            idempotency_key=idempotency_key, approval_ref=approval_ref)

    def _authenticated_steward(self):
        with self._registry.db.transaction():
            with self._registry.db.cursor() as cur:
                self._registry._path(cur)
                principal = self._registry._authenticate(cur, self._steward_token)
                if (principal["principal_kind"] != "steward" or
                        principal["principal_id"] != self._steward_principal_id):
                    raise AuthorityDenied("Steward authority required")
                return principal["principal_id"]

    def reserve_delegated_grant(self, principal_id, grant_id, action, scope_ref,
                                operation_ref, *, idempotency_key):
        self._proposal_action(action)
        if principal_id != self._authenticated_steward():
            raise AuthorityDenied("promotion actor does not match protected Steward identity")
        return self._registry.reserve_delegated_grant(self._steward_token,
            grant_id, action, scope_ref, operation_ref,
            idempotency_key=idempotency_key)

    def consume_delegated_grant(self, principal_id, reservation_id, result_ref):
        if principal_id != self._authenticated_steward():
            raise AuthorityDenied("promotion actor does not match protected Steward identity")
        return self._registry.consume_delegated_grant(self._steward_token,
            reservation_id, result_ref)

    def release_delegated_grant(self, principal_id, reservation_id, reason_code):
        if principal_id != self._authenticated_steward():
            raise AuthorityDenied("promotion actor does not match protected Steward identity")
        return self._registry.release_delegated_grant(self._steward_token,
            reservation_id, reason_code)

    def authorize_operation(self, *, principal_id, tool, operation_ref):
        if not is_delegable_tool(tool):
            raise AuthorityDenied("Comms5 operation is excluded from delegated authority")
        if not isinstance(principal_id, str) or not principal_id:
            raise AuthorityDenied("authenticated Comms5 principal is required")
        return self._registry.authorize_delegated_principal_operation(
            principal_id, DELEGATED_ACTION, DELEGATED_PROJECT_SCOPE,
            DELEGATED_POLICY, operation_ref)
