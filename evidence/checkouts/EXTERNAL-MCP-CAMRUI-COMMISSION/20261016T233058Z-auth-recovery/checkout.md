<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/EXTERNAL-MCP-CAMRUI-COMMISSION/20261016T233058Z-auth-recovery/checkout.md
File Revision: 1.0.0
Task: RV-EXTERNAL-MCP-ADAPTER-001
Source baseline: e5a373e43594785c885c6972baecccbc37c6ec34
Evidence update after: 450aecfe6c4ed00d07fa960949469f079180b9c0
Authority: Read-only historical/live ingress inspection; no auth authority or public route added
Data: Sanitized; no credentials, private keys, tokens, or MCP payloads
-->

# Authentication and ingress recovery follow-up

## Historical implementation recovered

Historical repository `ppow1/Riverview` was verified at commit
`08c1162c4ad04a21df71ed7814a3e22bd9ba41a2`.

- Comms used `127.0.0.1:11825/mcp`; its Caddy template was
  `config/riverview-comms-ingress.Caddyfile.example`. Caddy compared a
  service-held client bearer, replaced the upstream Authorization value with a
  separately held backend bearer, injected `X-Riverview-Comms`, normalized
  `Host` to `127.0.0.1:11825`, bounded request size/time, and served TLS.
- Comms5 was distinct: public `/comms5/mcp` was rewritten to loopback
  `127.0.0.1:11826/mcp`; Caddy used separate client/upstream bearers, injected
  `X-Riverview-Comms5` plus the fixed `steward` attestation, and normalized
  Host to `127.0.0.1:11826`. Its documented reverse tunnel was VPS loopback
  `11826` to Windows loopback `11826`.
- Historical acceptance records report authenticated MCP initialization,
  discovery and tool invocation for those predecessor applications. This does
  not prove their identity headers or their database contracts work with the
  new adapter.
- Reusable mechanics: Caddy TLS ingress, separate client/backend secrets,
  exact path match, request bounds/timeouts, upstream Authorization replacement,
  Host normalization, and reverse-tunnel topology. Comms and Comms5 paths,
  their fixed attestation headers, tools and database backends must remain
  untouched.

The current adapter is different: it requires a bearer whose SHA-256 digest
maps in a protected systemd credential to a fixed `provider_id`,
`principal_id`, scopes and expiry. It derives provider identity from that map;
it does not consume the historical Comms identity headers. A Caddy bridge could
only reuse the old *pattern* by authenticating a supported upstream principal
and replacing Authorization with the new adapter's own narrowly scoped
provider bearer. The old bearer and Comms5 `steward` attestation are not valid
substitutes for an external reasoning provider identity.

## Current ChatGPT authentication compatibility

OpenAI's current official documentation states that authenticated custom MCP
servers are expected to implement OAuth 2.1: a protected-resource document
advertises a real authorization-server issuer; that server publishes OAuth
metadata and supports authorization-code + PKCE; ChatGPT obtains a token; and
the resource server checks issuer, audience, expiry and scopes on every
request. The current adapter only checks a preloaded opaque token digest and
expiry; it neither implements that authorization server nor verifies token
issuer/audience. Its env example still has placeholder URLs. Consequently the
historical Caddy static-bearer design is **not established as compatible with
current authenticated ChatGPT web custom MCP**. It remains suitable only for a
client that is explicitly configured to send a fixed bearer, subject to
separate security review.

Sources checked 2026-10-16:

- [ChatGPT custom MCP connection help](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt): configure a public HTTPS endpoint or supported tunnel and choose authentication; OAuth setup/discovery is described for authenticated use.
- [OpenAI MCP plugin authentication](https://developers.openai.com/plugins/build/auth): authenticated servers are expected to follow OAuth 2.1; protected-resource metadata must name the actual issuer; ChatGPT uses authorization code + PKCE and the resource server verifies issuer, audience, expiry and scopes. It also says ChatGPT does not support customer API keys or customer-provided mTLS certificates.
- [OpenAI custom MCP server guide](https://developers.openai.com/api/docs/guides/custom-mcp-server): current connection authentication options include OAuth, no auth, or mixed OAuth/no-auth. Static OAuth client credentials do not mean a fixed resource-server bearer token can replace the OAuth user flow.

No OAuth issuer is configured or advertised by Riverview production. No issuer URL, client registration, token, or provider map was invented.

## Current DNS, live route checks and Caddy ownership boundary

- DNS A lookup for `riverview-comms.ionoge.com` returned `64.227.21.54`; no AAAA answer was returned.
- Read-only HTTPS GETs with no Authorization header returned HTTP `401` with valid TLS for both `https://riverview-comms.ionoge.com/mcp` and `/comms5/mcp`. This confirms an authenticated edge is present at both paths; it does not identify the current Caddyfile owner or prove either route serves the new adapter.
- Historical records identify `64.227.21.54` as `ionoge-control-01` and record active Caddy ownership there. The current Camrui SSH configuration has no trusted known-host key for that host/IP. A strict, read-only SSH attempt failed host-key verification. Strict checking was not bypassed, and no Caddy configuration was changed.
- Therefore `/mcp` is occupied by the predecessor Comms route and `/comms5/mcp` is occupied by Comms5. No new path has been selected. A distinct path on the same hostname may be possible only after Caddy ownership/configuration is inspected through a trusted host identity; it remains subject to separate approval because it creates public exposure.

## Production adapter status

No change since the prior commissioning record:

- Migration 0011 and the verified protected backup are retained.
- The exact merged MCP release remains staged but the daemon is not installed or active; port 11827 has no listener.
- No MCP env file or provider token-map credential exists. No production exchange row was created.
- Production HTTP initialization, provider operations, and Grace consumption have not been claimed as tested. Exact-package independent HTTP and PostgreSQL round-trip tests passed only in the disposable environment as recorded in the preceding evidence record.
- The source unit's `/opt/riverview-core/current` paths do not match the existing shared core layout. Any later unit must point to the MCP immutable release root and existing Python environment; the shared core symlink must remain unchanged.
- Grace owner-session is currently inactive with no loaded unit fragment. It was not restarted. Assignment intake, M33 worker and M33 verifier are also inactive; M33's known expired-authorization/`WorkerAuthorizationError` issue remains separate and untouched. Dashboard, CME monitor and event processor remain active.

## Safe next steps

1. Obtain the trusted SSH host-key fingerprint for `ionoge-control-01` (or an already trusted host-key record) before inspecting current Caddy route ownership. Do not use TOFU or disable strict checking for root SSH.
2. Identify the existing approved OAuth/OIDC issuer and its owner. Verify its metadata, PKCE support, redirect allowlist, refresh-token behavior and user-to-provider identity mapping. If none exists, obtain a separate explicit decision before creating or integrating an authorization server; the present MCP deployment authorization does not authorize a new authentication authority.
3. Adapt the resource server to validate issued tokens' signature/issuer, audience, expiry and exact scopes, or use a reviewed trusted OAuth gateway that performs those checks and injects a fixed, protected backend provider token. Keep the provider map least-privilege and ChatGPT/user identity provenance explicit.
4. Correct the service-specific unit paths, install/start only after valid issuer and provider configuration, and verify production loopback auth denial/success and tools. Create a harmless synthetic exchange only through the existing authorized Grace escalation path; then verify one correlated provider round trip and Grace consumption.
5. After local checks pass and Caddy ownership/path availability is proven, prepare a distinct route and reverse tunnel on a new path/port without changing `/mcp` or `/comms5/mcp`. Public exposure and the ChatGPT-side connector test remain a separate approval checkpoint.
