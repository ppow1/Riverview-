<!--
Riverview~ controlled evidence
File Revision: 1.0.0
Task: RV-MCP-CHATGPT-OAUTH-RESOURCE-001
Component: EXTERNAL-REASONING-MCP-TRANSPORT
Captured: 2026-10-17T00:34:00Z
Environment: isolated Riverview checkout and disposable PostgreSQL 16.15 cluster
Secrets: none included
-->
# ChatGPT MCP OAuth and Tunnel investigation

## Source baseline

- Repository: `ppow1/Riverview-` checkout `/tmp/riverview-mcp-e5a373`
- Branch: `codex/camrui-mcp-commissioning-record-20261016`
- Base source commit: `20d9919b69f6bf8f111c9f1f8c0616f157a813b2`
- PR #74 remains the development vehicle; this checkout contains uncommitted implementation changes at capture time.
- Historical Camrui release last reported: `e5a373e43594785c885c6972baecccbc37c6ec34`; production service was last documented inactive. This turn could not reverify production.

## Official Tunnel finding

OpenAI's [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
describes `tunnel-client` on a private VM/systemd host, polling OpenAI over
outbound HTTPS and forwarding MCP requests to a private HTTP target. It needs no
inbound firewall port or public MCP listener. It can therefore carry the
Camrui loopback adapter without repointing the historical Comms/Comms5 Caddy
routes. The guide requires a Platform `tunnel_id`, a runtime API key, Tunnels
Read+Manage to create/configure, Tunnels Read+Use to run/select, and permission
to add custom MCP in the target ChatGPT workspace. The guide does not publish
pricing. Billing/entitlement for the required key was not verified.

Tunnel is transport, not user authentication: ChatGPT must still use OAuth for
this provider-scoped exchange. OpenAI documents that protected-resource OAuth
discovery can travel through the tunnel, but the authorization server itself is
not tunneled. See the official [MCP authentication contract](https://developers.openai.com/plugins/build/auth).
The authorization server must support authorization-code + PKCE `S256`, the
ChatGPT-supported client registration mode (CIMD, DCR or predefined client),
the resource/audience parameter, and an allowed token-endpoint auth method.

The connection method selected for Riverview is **Tunnel + OAuth**. No tunnel
ID, Platform key, Linux tunnel-client, approved OAuth issuer, ChatGPT OAuth user
subject, ChatGPT client ID, or provider mapping was present in this checkout.
No source search or prior deployment evidence establishes a current account-
side tunnel or an approved identity provider.

## Implementation and local verification

The existing MCP adapter was extended as an OAuth resource server; no OAuth
authorization server was created. It now publishes the RFC 9728 protected-
resource document, advertises OAuth scopes on all four tools, returns the
`mcp/www_authenticate` challenge for unauthenticated tool calls, validates
RS256/ES256 JWT signature through issuer JWKS, and requires exact issuer,
resource audience, expiry, scope, and preconfigured subject/client mapping.
The production launcher accepts only the protected OAuth provider map; the
old static bearer mapper remains test-only. OpenAI's tool discovery remains
unauthenticated per mixed-auth behavior; all tool calls are authenticated.

Exact commands and results:

- `PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_mcp -v` — **10 passed**.
- Full test suite on disposable PostgreSQL 16.15: `python3 -m unittest discover -s tests -v` — **507 passed, 1 skipped, 0 failed**. The skip is the dashboard ACL case that requires the production runtime role, intentionally absent from the disposable test cluster. Temporary cluster used separate port `55527` and private socket directory; it was stopped and removed after the run. Production PostgreSQL 16/main was not used or changed.
- `python3 -m compileall -q src/riverview_core/resident_execution/external_reasoning_mcp.py scripts/run_external_reasoning_mcp.py tests/test_external_reasoning_mcp.py` — passed.
- `python3 scripts/process_graph.py check` — **20 graphs / 513 nodes, PASS**.
- `python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json` — **PASS, zero issues**.
- `git diff --check` — passed.

The OAuth tests use a synthetic RSA signing key and synthetic provider claims.
The socket test starts the real adapter HTTP handler on loopback and verifies
valid signed-token dispatch and unauthenticated rejection. The PostgreSQL MCP
test exercises durable list/claim/submit/status operations. These are local
tests; no live IdP or ChatGPT user token was used.

## Production access and acceptance boundary

The checked SSH configuration resolves alias `camrui` to the unresolvable name
`camrui`. A single BatchMode connection to the existing known-host IP
`192.168.1.155` targeted account `admin1` and returned
`Permission denied (publickey,password)`. No further credential attempts were
made. The host key was already present locally; no host key was added or
changed.

Consequently this turn did not inspect current production service state, start
the MCP unit, install PyJWT in the production venv, create a Platform tunnel,
modify Caddy/DNS, provision a credential or AuthorityRegistry grant, configure
ChatGPT, or submit/retrieve a real external reasoning exchange. No public route
or unauthenticated MCP endpoint was created. The existing Comms/Comms5 routes,
M33 services, worker retirement work, and production PostgreSQL were not
modified.

## Next executable gates

1. Reestablish authorized Camrui administration for `admin1@192.168.1.155` (or
   supply the already-approved account/key route); do not send private-key
   material in chat.
2. An OpenAI Platform owner must confirm Tunnel access/any billing, create or
   identify the tunnel, and provide a runtime key through a protected local
   provisioning path. Associate the tunnel with the target ChatGPT workspace.
3. The Steward must identify an approved OAuth issuer (none was found in the
   inspected Riverview source/runtime evidence) or authorize selection and
   provisioning of an established provider. It must satisfy the official MCP
   OAuth requirements above and be reachable for browser authorization.
4. Once the issuer and exact ChatGPT OAuth subject/client are known, use
   AuthorityRegistry—not SQL—to approve the finite `resident.reasoning.escalate`
   grant for `resident:grace` on the selected provider scope. Configure the
   protected provider map with the exact subject/client pair and limited scope.
5. Start the already-packaged MCP service and tunnel client, verify health and
   external ChatGPT tool discovery, then complete one correlated advisory
   request/claim/response/Grace-consumption cycle.

Source implementation and isolated tests are **PASS**. Production service,
Tunnel, OAuth issuer, ChatGPT connection, and end-to-end Grace exchange are
**NOT VERIFIED / BLOCKED** by account, authority, and Camrui access prerequisites.
