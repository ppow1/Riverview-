# Riverview Delegation Grants

This contract extends the existing `AuthorityRegistry`. Comms5, internal
callers, and the Riverview website use the same registry methods and the same
PostgreSQL transaction boundary. HTTP and MCP adapters authenticate callers,
then pass the verified principal to this API; callers never provide proof of
identity in grant arguments.

## Grant limits

`max_uses` and `duration_spec` are independent:

| Request | `max_uses` | `duration_spec` |
| --- | ---: | --- |
| One successful execution | `1` | `{"unit":"indefinite"}` or a finite duration |
| Fixed count | positive integer | indefinite or finite duration |
| Unlimited count | omitted / `null` | indefinite or finite duration |
| Time limited | `1` or a larger count | finite duration |
| Combined | positive integer | finite duration |
| Indefinite | count or unlimited | `{"unit":"indefinite"}` |

Successful consumption remains atomic in `AuthorityRegistry`; reservations
that fail are released and do not increment `used_count`. A count-only grant
can be indefinite. A grant with no count limit must explicitly include a
duration, including `indefinite`.

Supported duration objects use one of these exact forms:

```json
{"unit":"minutes","value":30}
{"unit":"hours","value":2}
{"unit":"days","value":7}
{"unit":"weeks","value":2}
{"unit":"months","value":1}
{"unit":"quarters","value":1}
{"unit":"years","value":1}
{"unit":"custom","seconds":5400}
{"unit":"indefinite"}
```

Month, quarter, and year durations use calendar arithmetic from the activation
timestamp, clamping to the last valid day in the destination month. Other units
are elapsed UTC time. Finite values are bounded to 100 years. A duration starts
when a Steward approves it, using the transaction's database clock. Legacy
absolute `valid_until` requests remain supported and cannot be combined with
`duration_spec`.

## Lifecycle

The canonical API is the `AuthorityRegistry` in
`src/riverview_core/institutional_authority/registry.py`:

| Lifecycle action | API |
| --- | --- |
| Request | `request_grant(...)` |
| Approve or deny | `decide_request(..., decision="approve"|"reject", ...)` |
| Inspect | `get_status(requester_id=..., request_id=...|grant_id=...)` |
| Extend | `request_change(..., change_kind="extend", ...)` |
| Upgrade permission | `request_change(..., change_kind="upgrade", ...)` |
| Extend and upgrade together | `request_change(..., change_kind="extend_upgrade", ...)` |
| Revoke by Steward | `revoke_grant(steward_token, grant_id, ...)` |
| Voluntary surrender | `surrender_delegated_grant(grantee_token, grant_id, ...)` |

Change requests create a pending successor. Steward approval locks the old
grant and request, carries successful-use accounting forward, creates the
successor, and revokes the old grant in one transaction. `supersedes_grant_id`
and append-only authority events preserve lineage. A request that changes
permissions and lifetime together is one request and requires one Steward
decision.

The Comms5 adapter accepts only actions allowed by the existing explicit
delegation policy. Host-scoped grants are limited to the four fixed
Command Gateway permission IDs and their exact registered host pairs:
`desktop-ja3rpnq` for the PowerShell identity probe and `camrui` for the SSH
hostname probe. Unknown command actions or action/host mismatches are rejected.
Broad Comms5 authority remains bound to
`project:Riverview`, `policy:delegation.v1`, unlimited count, and the existing
non-destructive action class. Other actions remain exact. Steward approval,
account-session authentication, CSRF validation, request digests, idempotency,
quota enforcement, and destructive-operation exclusions remain in force.

## Canonical caller methods

```python
pending = registry.request_grant(
    requester_id=authenticated_principal,
    principal_id=grantee_principal,
    action="comms5.operations.non_destructive.v1",
    scope_ref="project:Riverview",
    policy_ref="policy:delegation.v1",
    request_ref="ticket-or-approval-context",
    max_uses=None,
    duration_spec={"unit": "days", "value": 7},
    idempotency_key="stable-request-key",
)
```

The method above creates a pending request only. It does not grant authority.
Only the existing authenticated Steward decision path activates it.
`request_change` takes the same grant values plus the existing `grant_id` and
`change_kind`; omitted `max_uses` and absolute expiry fields preserve the
predecessor's values. For an extension, `duration_spec` adds its interval to
the predecessor's current expiry, or to approval time if that grant has
expired. An indefinite predecessor cannot be shortened with a finite
extension; it can remain indefinite or receive a use-count extension.

All request and response examples, including one request for a combined
extension and permission upgrade, are in [`examples.json`](examples.json).
The HTTP/MCP wire shapes are specified in [`openapi.json`](openapi.json).
