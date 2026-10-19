<!--
Riverview~ Controlled Document
File: docs/components/GRACE_CHATGPT_REVIEW_PROVIDER_PREFLIGHT.md
Component: EXTERNAL-REASONING-MCP-TRANSPORT
File Revision: 1.0.2
Purpose: Give operators a read-only, non-secret preflight for provider-facing exact-proposal reviews
Authority: Existing resident.reasoning.escalate grant; provider responses remain advisory
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Initial offline and live-gate runbook
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-TYPED-REVIEW-SUBJECT | Document the typed PlanProposal/PlanStep subject contract
Changed: 2026-10-19 UTC | RV-W3-GRACE-BOUNDED-TRIAL-PLAN | Preserve the active owner-session and define a fresh, approval-gated acceptance trial; historical trial rows are not replay authority
History: Git
-->
# Grace to ChatGPT review provider preflight

This page describes the existing durable external-reasoning exchange and its
provider-facing MCP interface. The exchange remains the only mailbox. The
Playwright/CDP component sends its existing fixed wake message; it does not
carry proposal text or return a review. ChatGPT reads the exact subject through
the authenticated MCP tools and submits a correlated advisory. Grace evaluates
that advisory through its existing resident reasoning path.

## Provider contract

`reasoning_exchange_list_requests` returns only requests assigned to the
authenticated provider. Exact-review requests include the immutable
`review_subject` and `review_subject_sha256`. Its schema is
`rv.grace.proposal-review-subject.v1` and contains UUID `subject_id`, revision
1 through 3, `sha256`, and a bounded `PlanProposal` `{summary, steps}`. Summary
length is at most 4,000 characters and each of 1 through 20 steps preserves all
`PlanStep` fields: `step_id`, `objective`, `acceptance_criteria`, `depends_on`,
`execution_capability`, `authorized_paths`, `test_targets`,
`repository_reference`, and `repository_revision`. In particular, source-change
targets and pinned repository provenance are not flattened or dropped. The
adapter checks the same structural rules used by the resident `PlanProposal`
and `PlanStep` types. The digest is SHA-256 of
UTF-8 canonical JSON for `{subject_id, revision, proposal}` using sorted keys,
compact separators, `ensure_ascii=false`, and `allow_nan=false`.

After claiming the exact `request_id` and `correlation_id`, the provider submits
its existing bounded advisory response together with the explicit
`review_subject_sha256` argument. The MCP adapter checks the digest syntax and
correlation/provider ownership; the durable exchange compares it with the
stored immutable subject digest and rejects missing or mismatched values.
Requests without an exact review subject retain their existing advisory
contract. No provider response grants proposal approval or execution authority.

## Read-only preflight on the configured hosts

Run these checks independently on the host that owns each named service. They
read service state, environment key presence, file metadata, and loopback
listener state. They do not read credential contents, start or restart a
service, send a browser wake, or call ChatGPT.

### External reasoning MCP host

Confirm the unit state without printing its environment:

```sh
sudo systemctl show riverview-external-reasoning-mcp.service \
  -p LoadState -p ActiveState -p SubState -p MainPID
sudo ss -ltn '( sport = :11827 )'
```

The expected listener is `127.0.0.1:11827`. A public ChatGPT MCP route or
approved Secure MCP Tunnel must be verified separately; a loopback listener
alone does not establish remote reachability. The unit reads
`/etc/riverview/external-reasoning-mcp.env` and loads the protected
`provider-auth-map` from `/etc/riverview/external-reasoning/provider-auth-map.json`.
Report only the following environment-key presence, never their values:

```sh
sudo awk -F= '
  /^(RIVERVIEW_MCP_RESOURCE_URL|RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL)=/ {
    if (length($2) > 0) print $1 "=PRESENT"
  }
' /etc/riverview/external-reasoning-mcp.env
sudo stat -c 'provider-auth-map present; mode=%a owner=%U group=%G' \
  /etc/riverview/external-reasoning/provider-auth-map.json
```

An authorized operator must compare the configured resource URL with the OAuth
token audience and the configured authorization-server URL with the token
issuer. The protected map must contain the approved provider ID, principal,
ChatGPT OAuth client ID, subject mapping, and `reasoning:exchange` scope. Never
paste the map or token into an issue, log, or command transcript. A placeholder
URL or a missing map is a failed gate.

### Existing Grace owner-session

The operator reported on 2026-10-19 that
`riverview-grace-execution-owner-session.service` is already loaded, active,
and running; the generic `riverview-grace-execution.service` is absent. Treat
this as operator-reported live metadata from issue #120 comment 6258108851,
not a source-only recheck. Preserve the active owner-session unit, its existing
`/etc/riverview/grace-execution.env`, protected credentials, writable owner
state, and current release pointer. Do not run the owner-session installer,
install the generic unit, replace the existing environment file, enable or
start another service, or restart Grace as a readiness probe. The generic unit
references a different resident credential path and is not a fallback.

For a future separately authorized read-only check, inspect only the existing
unit's non-secret systemd metadata and file metadata:

```sh
sudo systemctl show riverview-grace-execution-owner-session.service \
  -p Id -p LoadState -p ActiveState -p SubState -p MainPID -p FragmentPath -p DropInPaths -p NRestarts
sudo systemctl show riverview-grace-execution.service \
  -p Id -p LoadState -p ActiveState -p SubState -p FragmentPath
sudo stat -c '%n %U:%G %a %s' /etc/riverview/grace-execution.env \
  /etc/riverview/grace/resident.credential
sudo awk -F= '/^RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP=/ {
  if (length($2) > 0) print "RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP=PRESENT"
}' /etc/riverview/grace-execution.env
```

Do not print environment values, credential contents, auth files, tokens, or
provider-map contents. The selected provider ID must match the approved MCP
OAuth map and registered exchange principal. Provider IDs in tests are
synthetic and establish no live identity. The active Grace resident must hold the existing exact
`resident.reasoning.escalate` grant for `provider:<provider_id>`. Verify that
grant through the established protected authority workflow using the current
resident credential; do not infer it from a configuration entry or create a
grant to make the preflight pass.

`GraceExecutionService.run_forever()` immediately enters `run_once()`, which
can dispatch existing authorized objectives and poll workers. A restart is
therefore an execution event, not a harmless health check. Do not restart the
already-running service to test readiness. A later release activation must
preserve this unit/configuration and owner state and use only the exact
separately approved release procedure.

### Comms5 and browser doorbell boundaries

Comms5 OAuth ingress is a distinct communication path. Its `/comms5/mcp` route
does not wake ChatGPT or provide the durable reasoning response. Verify its
OAuth host and Camrui adapter/tunnel through their own existing runbook; do not
add a second route or mailbox for this review.

The browser runtime must report a fresh local CDP target for the configured
conversation and the existing fixed action must be enabled. Do not inspect or
print cookies, tokens, page text, proposal text, or the browser profile. The
doorbell remains untriggered during preflight.

## Fresh bounded end-to-end acceptance trial — proposal only

Historical Grace rows reported in issue #120 comment 6258108851 were failed or
incomplete trials. Their `COMPLETED`, `WORK_ORDER_CREATED`, `verified`,
`assigned`, or `pending` labels are not proof of end-to-end success and do not
authorize retry, dispatch, or replay. Preserve those records and their audit
history. C1 must first provide record-level IDs, provenance, authority, failure
reason, and current dispatch/retry eligibility, plus a minimal non-destructive
guard recommendation. Do not mutate, quarantine by writing, delete, or replay
those rows from this procedure. Any unexpected eligible old work or unresolved
queue state blocks a new trial.

One **new** acceptance trial may be proposed only after all of these independent
gates pass: (1) PR acceptance and exact final source SHA are approved and
revalidated; (2) the fresh protected PostgreSQL backup and isolated restore,
required migration, release staging, and source verification each receive
their own Steward authorization and pass; (3) the existing active owner-session
unit/configuration is preserved and the release is activated only under its
separate approval; (4) C1's record-level queue review establishes that no
unintended historical trial can be picked up; and (5) the Steward separately
approves the exact harmless objective/proposal, provider and designated ChatGPT
conversation, expected effects, operator, observation window, and stop/rollback
procedure. These gates are not granted by this document.

Proposed test bounds, subject to explicit trial approval:

1. Use exactly one fresh, explicitly authorized objective and a harmless
   bounded proposal. Create one new immutable review subject, request ID,
   correlation ID, and idempotency key; do not reuse historical identifiers.
2. Exercise the existing path only: durable request → existing fixed browser
   wake → provider claim/response through the existing authenticated MCP
   exchange → Grace evaluation of the exact digest → either finish or one
   revision with a new successor subject/request/correlation pair.
3. Cap the trial at two review rounds total (at most one revision), even though
   source allows revisions through revision 3. Each exchange uses the existing
   finite deadline; do not extend an expired request, replay an ambiguous wake,
   or manually resubmit a response. Any second revision, unexpected row, digest
   or identity mismatch, ambiguous wake, terminal failure, timeout, or
   unauthorized side effect stops the trial for Steward review.
4. Do not create an Engineering assignment, approve work, change resident
   identity, invoke tools, alter provider grants, or change any other service.
   The provider response remains advisory; only Grace may evaluate or revise
   the proposal.
5. Retain a body-free trace of the same subject digest and round IDs, durable
   wake receipt, provider claim/response digests, Grace decision/consumption,
   and final finish/revision evidence. Do not publish proposal or response
   bodies, browser page text, tokens, cookies, or credential data. Mark all
   synthetic CI/test evidence as synthetic; it does not satisfy this trial.

Before creating the trial objective, prove from the reviewed exact path that
this input will not silently authorize an Engineering assignment or dispatch.
Do not use a temporary service flag, grant, queue edit, or unreviewed intake
route as a containment mechanism. If the existing production path cannot keep
the harmless test within the separately authorized trial scope, do not run it
there; request a separately isolated acceptance environment or explicitly
expanded trial authorization.

This is a proposed acceptance procedure, not a registered runtime workflow or
proof that any live round has run. A live test requires a separate explicit
Steward GO after the gates above; absent that GO, do not create its objective or
request and do not wake ChatGPT.

## Live smoke gate

No live review is authorized by this preflight. Before sending the fixed wake,
the Steward must approve the exact harmless proposal summary, designated
ChatGPT conversation, expected side effects, and test window. An operator must
also confirm the real provider/client/principal mapping, active exact Grace
grant, route, service health, and rollback/stop procedure. If any item is
missing, report the specific gate and stop before the browser wake. After a
separately authorized review, preserve evidence for the same proposal digest,
request/correlation pair, wake receipt, provider claim/reply, Grace evaluation,
and revise-or-finish decision. Offline synthetic tests must be labeled as such.
