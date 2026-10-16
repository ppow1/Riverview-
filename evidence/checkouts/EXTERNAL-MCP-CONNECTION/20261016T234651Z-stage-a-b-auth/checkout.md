<!--
Riverview Controlled Evidence
File: evidence/checkouts/EXTERNAL-MCP-CONNECTION/20261016T234651Z-stage-a-b-auth/checkout.md
Component: EXTERNAL-REASONING-MCP-TRANSPORT
File Revision: 1.0.1
Task: RV-EXTERNAL-MCP-LOCAL-COMMISSIONING-AUTH-DISCOVERY
Purpose: Record bounded read-only local commissioning and authentication discovery
Authority: No identity, grant, token, service, public route, or DNS change made
Date: 2026-10-16T23:46:51Z
History: Git + .riverview-backups/manifest.jsonl
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-LOCAL-COMMISSIONING-AUTH-DISCOVERY | Add OAuth tool-metadata incompatibility and exact PR CI result; predecessor preserved in .riverview-backups/20261016T235151734006Z/...
-->

# External MCP local commissioning and authentication discovery

## Result

- **Local MCP commissioning: BLOCKED before credential provisioning or service start.**
- **Grace-to-MCP exchange: BLOCKED; no production exchange was created.**
- **Public exposure: NOT ATTEMPTED.** No Caddy, DNS, route, tunnel, or ChatGPT configuration was changed.
- **Target checkout:** `/tmp/riverview-mcp-e5a373`, branch `codex/camrui-mcp-commissioning-record-20261016`, HEAD `6fcf4431ada773a05a7803559cf74036e9900cde`.
- **Immutable deployed source:** `e5a373e43594785c885c6972baecccbc37c6ec34`.

## Local production evidence (Camrui, read-only)

Commands and outcomes:

| Check | Command / evidence | Result |
|---|---|---|
| MCP systemd state | `systemctl show riverview-external-reasoning-mcp.service -p ActiveState -p SubState -p UnitFileState -p NRestarts` | Loaded; inactive/dead; disabled; `NRestarts=0`. No service start or restart performed. |
| Listener | `ss -ltn '( sport = :11827 )'` | No listener. `curl http://127.0.0.1:11827/healthz` could not connect (`HTTP 000`). |
| Release pointer | `readlink -f /opt/riverview-external-reasoning-mcp/current` | Resolves to `/opt/riverview-external-reasoning-mcp/releases/e5a373e43594785c885c6972baecccbc37c6ec34`. `SOURCE_COMMIT` matches. |
| Package | `sha256sum /tmp/riverview-camrui-e5a373e43594785c885c6972baecccbc37c6ec34.tar.gz`; `sha256sum -c PACKAGE_SHA256SUMS` | Archive SHA-256 `42b6cb7af93a42884fb1a05357e37690e8e8e0adc678cc91f4d5627487ebdc0d`; all **1,331** staged manifest entries verified. |
| Service configuration | `systemctl cat riverview-external-reasoning-mcp.service` | Uses service-specific immutable release pointer and binds `127.0.0.1:11827`; runs as `riverview`; loads `pgpass` and `provider-token-map` with systemd credentials; has an `EnvironmentFile`. |
| Protected configuration presence | Root-only `stat` of the exact configured paths; no file contents read | `/etc/riverview/pgpass` is root:root `0600`; `/etc/riverview/external-reasoning-mcp.env` is absent; `/etc/riverview/external-reasoning/provider-token-map.json` is absent. |
| PostgreSQL migration and ACL | Sanitized `psql` catalog/privilege queries as local postgres | `0011_external_reasoning_exchange` present with checksum `93e2603dd92237b95700356f723e21553bcafdee5314800bb04cd18469163b30`; exchange relations exist; `riverview_core` has the expected table `SELECT`/`INSERT` access on exchanges and events. |
| Existing exchange state | `SELECT count(*)` only | `external_reasoning_exchanges` contains zero rows; no synthetic or production exchange was inserted. |
| Exact escalation authorization | Counts only in `riverview_authority.authority_grants` | Zero `resident.reasoning.escalate` grants and zero provider-prefixed principals in grants. No grant was issued. |

The service unit's configured bearer map and resource/issuer metadata are runtime prerequisites, not proof of OAuth. The adapter source loads opaque bearer tokens by SHA-256 digest into fixed provider/principal/scope/expiry mappings; tool arguments cannot choose the provider identity. The four tools are `reasoning_exchange_list_requests`, `reasoning_exchange_claim_request`, `reasoning_exchange_submit_response`, and `reasoning_exchange_status`. They expose advisory exchange operations only; no approval, dispatch, execution, verification, or Grace-consumption tool exists.

The `AuthorityRegistry.grant()` operation requires an authenticated Steward credential with `authority.grant` on `institution`; exact escalation admission then requires the active Grace resident principal to have `resident.reasoning.escalate` on `provider:<provider_id>`. The grant is absent. The current environment also lacks the token map and issuer/resource configuration. Thus the adapter cannot safely start with a valid registered external identity, and a Grace-originated authorized request cannot be admitted. Provisioning now would require creating an identity/credential and changing institutional authorization without an applicable grant. It was not done.

Existing Grace/CME/dashboard services were left untouched. Read-only `systemctl show` found the dashboard, Grace owner-session, CME monitor, and event processor active/running, each with `NRestarts=0`. No unrelated service was restarted.

## Source and test checks

The adapter contract is in `src/riverview_core/resident_execution/external_reasoning_mcp.py`; the launcher is `scripts/run_external_reasoning_mcp.py`; unit contract is `deploy/systemd/riverview-external-reasoning-mcp.service`; cookbook is `docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md`.

- `PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_mcp -v`: **4 passed**. These are isolated adapter/independent-client tests, not production listener acceptance.
- `PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_exchange.ExternalReasoningExchangePostgresTests.test_mcp_provider_scoped_round_trip_uses_durable_exchange -v`: **skipped**, because `RIVERVIEW_TEST_PG_DSN` is not configured in this checkout. Prior isolated PostgreSQL round-trip evidence remains in the PR #69 implementation record; this command did not touch production PostgreSQL.
- `python3 -m unittest tests.test_external_reasoning_mcp -v` without `PYTHONPATH=src`: failed to import the package. Rerunning with the documented source path passed. This was a test invocation issue, not an adapter failure.

No production MCP initialize, discovery, auth rejection, scope-denial, list/claim/submit/status call, or Grace-consumption call was possible because the listener is inactive and its auth configuration is absent. Consequently local commissioning and Grace round-trip are not passes.

## Authentication inventory

### Current Riverview

`docs/components/ACCOUNT_AUTHENTICATION.md` describes local account/password enrollment, email verification, and secure cookie sessions stored in `riverview_accounts`. Those website roles do not confer institutional grants. Source and deployment configuration search found no existing OAuth/OIDC issuer, discovery endpoint, authorization-code flow, JWKS publication, or OAuth access-token validator. This account system is not currently an OAuth provider.

### Historical Comms / Comms5

Historical source `ppow1/Riverview` at commit `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2` records two separate services:

- Comms: loopback `11825`, public `/mcp`.
- Comms5: loopback `11826`, public `/comms5/mcp`, reverse-tunnelled to the historical Caddy host.

The historical Caddy ingress used static bearer validation, separate service-held credentials, upstream Host normalization, and trusted identity-attestation headers. Historical checkpoint documents report that old ChatGPT Comms setup completed authenticated initialize/tool discovery and a tool call. This establishes historical acceptance for that prior integration, not OAuth issuance or compatibility with today's ChatGPT custom MCP connection.

Current DNS for `riverview-comms.ionoge.com` resolves to `64.227.21.54`. Anonymous TLS probes returned HTTP 401 at `/mcp` and `/comms5/mcp`; the three OAuth/OIDC well-known paths probed returned HTTP 404, with certificate verification succeeding. These status responses do not establish route ownership or the backend revision. The local `known_hosts` file has no trusted entry for `ionoge-control-01` or `64.227.21.54`; no SSH attempt was made and no Caddy configuration was read or changed. The historical hostname/routes must not be reused for the new adapter without verified owner/route authority.

### Compatibility with ChatGPT

Current OpenAI MCP documentation requires OAuth 2.1 for authenticated custom MCP use, with protected-resource and authorization-server metadata, authorization-code + PKCE/S256, resource/audience binding, expiry/scope enforcement, and per-request token validation. ChatGPT cannot present customer-defined API-key headers or use machine-to-machine client-credentials flows. The custom MCP setup's “static credentials” are static OAuth-client configuration, not the adapter's fixed resource bearer token. Therefore the historical Caddy static-bearer arrangement and the new digest-map adapter are **not compatible as-is** with the intended authenticated ChatGPT connector. See [OpenAI MCP authentication](https://developers.openai.com/plugins/build/auth) and [ChatGPT custom MCP setup](https://developers.openai.com/api/docs/guides/custom-mcp-server).

The source inspection finds two further adapter changes for an OAuth connection: (1) `tools/list` definitions do not currently include the per-tool OAuth `securitySchemes` described by OpenAI, and tool errors do not return the documented MCP OAuth challenge metadata; (2) the request handler authenticates against the static digest map, which checks a locally configured token expiry and scope but does not validate JWT signature/JWKS, OAuth `iss`, `aud`/resource, or token `exp`/`nbf` claims. The adapter's `authorization_server_url` is only advertised as metadata; it does not implement or validate that issuer. These are source-verified integration gaps, not runtime failures, because the service is inactive.

## OAuth choices (not provisioned)

| Choice | Fit / cost indication | Complexity and security obligations |
|---|---|---|
| Existing Riverview account system | No third-party subscription discovered, but it is not an issuer. | Highest engineering/security burden: implement and operate OAuth authorization code + PKCE, user consent, metadata, token signing/JWKS or equivalent, revocation, resource/audience and scope mapping. OpenAI recommends using an established provider instead of writing authentication from scratch. |
| Managed Auth0 | OpenAI lists Auth0 as a provider pattern. Current Auth0 pricing lists Free at `$0/month` up to 25,000 MAUs with one custom domain (custom-domain credit-card verification applies); Essentials currently lists `$35/month` for up to 500 MAUs. Feature and contract suitability must be confirmed before selection. | Lower server operations but creates an external identity/data processor and account/tenant administration. Must configure user authorization code + PKCE, exact resource audience, scopes, issuer mapping, redirect allowlist, and no broad self-signup. Auth0 DCR is disabled by default; enabling it is open registration unless additionally controlled. Prefer a reviewed CIMD/pre-registered client route if compatible. Auth0 documents a Resource Parameter Compatibility Profile requirement for MCP `resource` audience handling. |
| Managed Amazon Cognito | Current pricing is MAU-based: Essentials/Lite lists 10,000 direct/social MAUs free; above-free example rate is `$0.015/MAU` for Essentials; Plus lists `$0.020/MAU`; email/SMS and advanced security can add cost. Existing-account eligibility and region/feature pricing must be confirmed. | Could reuse an AWS account if one is institutionally approved, but none was found in this repo/runtime inventory. Must verify RFC 8707 `resource` echo/audience, ChatGPT client registration mode, scopes, PKCE, issuer metadata, and token validation before selecting. Not a proven drop-in. |
| Self-hosted Keycloak | No software license charge for the open-source distribution; actual recurring costs are Camrui/VM/database/storage, TLS, backups, monitoring, patching, and operator time. | Full operational ownership: production database, TLS/proxy hardening, issuer keys/JWKS, PKCE, client registration strategy, recovery, and security maintenance. Keycloak production guidance requires TLS and recommends a reverse proxy; admin interfaces should remain private. No instance currently discovered. |

No provider was selected or installed. **Recommended discovery path:** if the Steward already has an approved Auth0 tenant, perform a bounded compatibility check there first using the exact ChatGPT OAuth metadata/`resource` behavior, with pre-registered/CIMD client handling rather than unrestricted DCR. If there is no such tenant, compare the actual AWS account/contract and managed cost against self-hosted Keycloak operations before choosing. The adapter still needs reviewed OAuth resource-token validation and mapping before either provider can be used; do not put a fabricated issuer URL into its current configuration.

## Remaining gates and resume point

1. Steward-authorized temporary provider identity: fixed `provider_id`, provider principal ID, classification limit, `reasoning:exchange` scope only, and finite expiry.
2. Steward/AuthorityRegistry exact grant for Grace: action `resident.reasoning.escalate`, scope `provider:<provider_id>`, finite expiry, approved policy reference. Use the existing `AuthorityRegistry` grant API; do not write SQL directly.
3. Protected local test credential generated and installed on Camrui using a reviewed secure provisioning procedure; do not transmit the bearer in chat or evidence. Set only the loopback resource/issuer metadata needed for the controlled local test; no public route.
4. For ChatGPT connectivity, identify/approve an OAuth issuer and plan/vendor account, provide the issuer's exact discovery/resource configuration, and review the adapter's token signature/issuer/audience/expiry/scope validation and identity mapping change.
5. Before any ingress work, provide or establish a trusted SSH host key for the actual Caddy host through its authorized channel; verify Caddy route ownership and choose a distinct hostname/route. No public exposure is authorized by this record.
6. After those gates, start only `riverview-external-reasoning-mcp.service`, run loopback MCP/auth/scope tests, create one harmless authorized synthetic Grace request, verify provider claim/response and Grace consumption, then disable/rollback the MCP unit while preserving exchange history if acceptance fails.

## PR and change status

This record is evidence-only; no source, database, grant, credential, service, route, or production data changed. The pre-record PR #74 head was `6fcf4431ada773a05a7803559cf74036e9900cde`; the evidence record was committed as `0af51b05748369eec109941877ed7d2977e80b6a` on `codex/camrui-mcp-commissioning-record-20261016`. PR #74 remains open and mergeable into `codex/grace-conversation-ui-refinement`. Exact-head CI run `38983358534` passed: **501 tests, 2 skipped; 20 process graphs / 513 nodes; controlled revision audit passed with zero issues**. The audit update in this revision is a documentation clarification and requires a fresh CI run before the PR can be treated as fully checked.
