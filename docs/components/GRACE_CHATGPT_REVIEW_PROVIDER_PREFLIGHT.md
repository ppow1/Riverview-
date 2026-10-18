<!--
Riverview~ Controlled Document
File: docs/components/GRACE_CHATGPT_REVIEW_PROVIDER_PREFLIGHT.md
Component: EXTERNAL-REASONING-MCP-TRANSPORT
File Revision: 1.0.1
Purpose: Give operators a read-only, non-secret preflight for provider-facing exact-proposal reviews
Authority: Existing resident.reasoning.escalate grant; provider responses remain advisory
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Initial offline and live-gate runbook
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-TYPED-REVIEW-SUBJECT | Document the typed PlanProposal/PlanStep subject contract
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

### Grace execution host

Check only unit state and configured provider-map key presence:

```sh
sudo systemctl show riverview-grace-execution.service \
  -p LoadState -p ActiveState -p SubState -p MainPID
sudo awk -F= '/^RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP=/ {
  if (length($2) > 0) print "RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP=PRESENT"
}' /etc/riverview/grace-execution.env
```

The provider ID must match the selected provider in the MCP OAuth map, and the
mapped principal must match the registered exchange principal. Provider IDs
seen in tests are synthetic examples and do not establish production identity.
The active Grace resident must hold the existing exact
`resident.reasoning.escalate` grant for `provider:<provider_id>`. Verify that
grant through the established protected authority workflow using the current
resident credential; do not infer it from a configuration entry or create a
grant to make the preflight pass.

### Comms5 and browser doorbell boundaries

Comms5 OAuth ingress is a distinct communication path. Its `/comms5/mcp` route
does not wake ChatGPT or provide the durable reasoning response. Verify its
OAuth host and Camrui adapter/tunnel through their own existing runbook; do not
add a second route or mailbox for this review.

The browser runtime must report a fresh local CDP target for the configured
conversation and the existing fixed action must be enabled. Do not inspect or
print cookies, tokens, page text, proposal text, or the browser profile. The
doorbell remains untriggered during preflight.

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
