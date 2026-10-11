<!--
Riverview~ Controlled Document
File: docs/components/ASSIGNMENT_INTAKE_COOKBOOK.md
Component: ASSIGNMENT-INTAKE
File Revision: 1.0.0
Purpose: Diagnose and safely operate the exact-grant assignment request API
Authority: Loopback HTTP entry only; the exact assignment.create grant is mandatory
Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Initial operations guide
History: .riverview-backups/manifest.jsonl and Git
-->
# Governed assignment intake operations

**API:** `POST http://127.0.0.1:8768/api/v1/assignments`  
**Service:** `riverview-assignment-intake.service`  
**Unit file:** `deploy/systemd/riverview-assignment-intake.service`  
**Status:** Versioned service definition; live service commissioning is recorded separately.

## Request contract

The service accepts at most eight concurrent requests and a 16 KiB JSON body.
It binds only to a literal loopback address. A request must include one
`Authorization: Bearer …` credential issued by the Institutional Authority
registry and an exact active `assignment.create` grant for the body's
`authority_ref`. The service does not accept `actor_id`; actor attribution is
derived inside the exact-grant transaction. Assignment and
`assignment.created` event persist atomically. The route never calls the
non-authorizing low-level ledger API directly.

Required JSON properties are `assignment_id`, `owner`, `idempotency_key`,
`authority_ref`, and `objective_ref`. Optional properties are `contract_ref`,
`workflow_id`, `workflow_step`, `occupant_id`, and `correlation_id`. Unknown
fields, duplicate JSON keys, invalid content type, chunked transfer, or
oversized bodies are rejected. A success response contains only the request ID
and bounded assignment status metadata.

The server is loopback-only; a remote operator may use a specifically
authorized SSH local forward. Never bind this API to a public interface or put a
bearer token in shell history, a URL, a report, or a request body. Use an
owner-controlled mode-0600 client credential file. The server's PostgreSQL
passfile is delivered by systemd and copied to its private runtime directory;
the API does not receive Steward-management credentials.

## Health and diagnosis

```sh
systemctl status riverview-assignment-intake.service --no-pager
journalctl -u riverview-assignment-intake.service -n 100 --no-pager
ss -ltn '( sport = :8768 )'
curl --silent --show-error --max-time 3 http://127.0.0.1:8768/health
```

There is intentionally no unauthenticated health endpoint in v1; the final
command is expected to return HTTP 404 and proves only that the service is
reachable. `systemctl` and the structured `assignment_intake_started` event
provide service status. A listener on any address other than `127.0.0.1:8768`
is a security failure.

| Symptom | Expected interpretation | Safe response |
|---|---|---|
| Service fails before listening | Check the safe `assignment_intake_startup_failed` code, passfile credential mount, DSN schema, and exact-grant function preflight. | Correct only the unit/package configuration, then restart this unit and confirm the listener. Do not print passfiles or tokens. |
| HTTP 401 | Missing or malformed bearer header. | Use the protected Steward-issued client credential; never add it to the JSON body. |
| HTTP 403 `assignment_create_denied` | Credential, action, scope, principal or grant is absent/revoked/expired. | Verify the requested exact scope through the authority registry's redacted read procedure; request a new bounded grant through Steward authority if needed. |
| HTTP 503 `authority_unavailable` | Exact grant service did not return an authoritative decision. | Inspect authority DB health and function ACL; do not retry as though allowed. |
| HTTP 503 `persistence_unavailable` | Ledger PostgreSQL operation failed. | Check PostgreSQL and migration state; preserve the request and retry with its same idempotency key only after readiness. |
| HTTP 409 `assignment_not_created` | Persistence conflict or idempotency collision. | Inspect the matching assignment/event via read-only queries. Use a new idempotency key only for a genuinely new assignment. |
| Repeated timeout/client disconnect | The outcome may have committed despite a lost response. | Query by exact assignment ID, then retry the identical payload and idempotency key. |

Never repair by direct insert, changing actor attribution, editing grant rows
without the Authority API, or deleting assignments/events. Rollback means
disable this new service and retain its evidence; it does not delete valid
ledger data.

## Recovery and security checks

After an authorized package/service update, verify the recorded package
checksum, unit identity, loopback binding, database schema, current exact grant
function and a negative request without a credential. A `403` or `401` must
leave no assignment/event rows. An authorized smoke request must use an
explicitly disposable exact scope or a Steward-approved real scope; capture
assignment ID and response request ID, never its bearer. Restore the previous
root-owned release and unit from the recorded deployment checkpoint if startup
fails. Do not touch the dashboard, CME, event processor, notifications, or
shared migration ledger during route rollback.

See [institutional authority](INSTITUTIONAL_AUTHORITY.md),
[the request flow](ASSIGNMENT_INTAKE_FLOW.md), and the M3.3 revision record.
