<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/EXTERNAL-MCP-CAMRUI-COMMISSION/20261016T233656Z-local-staging/checkout.md
File Revision: 1.0.0
Task: RV-EXTERNAL-MCP-ADAPTER-001
Source commit: e5a373e43594785c885c6972baecccbc37c6ec34
Environment: Camrui Ubuntu, 2026-10-16 UTC
Authority: Authorized local MCP deployment preparation; no new public route or authentication authority
Data: Sanitized; no credential contents, tokens, or conversation bodies
-->

# Camrui MCP local staging follow-up — OAuth gate remains NO-GO

## Immutable release and service-specific path correction

- Source release: `e5a373e43594785c885c6972baecccbc37c6ec34`.
- Archive: `/tmp/riverview-camrui-e5a373e43594785c885c6972baecccbc37c6ec34.tar.gz`.
- Archive SHA-256: `42b6cb7af93a42884fb1a05357e37690e8e8e0adc678cc91f4d5627487ebdc0d`.
- Staged release `SOURCE_COMMIT` and all 1,331 package manifest entries verified; checksum matched.
- Created the service-specific pointer `/opt/riverview-external-reasoning-mcp/current` to the immutable release. The shared `/opt/riverview-core` pointer was not changed.
- Installed `/etc/systemd/system/riverview-external-reasoning-mcp.service` with its `WorkingDirectory`, source paths, and launcher pointed at the service-specific `current` path. The existing `/opt/riverview-core/.venv/bin/python` is retained.
- Installed unit SHA-256: `e8ab7ed501a58f3d9d2c38b2e5694183bfdcab3bc57e2bccdbdd9bca9665c01d`.
- `systemd-analyze verify /etc/systemd/system/riverview-external-reasoning-mcp.service` passed. Systemd reports the unit loaded, **disabled and inactive**. No process listens on `127.0.0.1:11827`.
- Before this staging, neither service-specific pointer nor system unit existed. Rollback is to remove only this unit and pointer; retain the immutable release and migration/data.

## Protected credential and identity readiness

Metadata was inspected as root; credential contents were not read. `/etc/riverview` is root-owned mode `0700`; the existing `/etc/riverview/pgpass` is root-owned mode `0600` and can be passed through systemd `LoadCredential`. The MCP-specific environment file and `/etc/riverview/external-reasoning/provider-token-map.json` do not exist. No provider identity or token was created.

The adapter requires both a canonical protected-resource URL and an authorization-server URL at startup. It validates a fixed bearer token by SHA-256 lookup against a protected provider/principal/scope/expiry map; it does not issue OAuth tokens or validate OAuth JWT issuer, audience, signature, or scopes. Therefore, an OAuth access token from a ChatGPT custom connector cannot be safely represented as the adapter's static bearer-map credential without a reviewed OAuth validation or trusted gateway integration.

## ChatGPT requirements and existing ingress

Official OpenAI documentation checked on 2026-10-16:

- [Authenticated MCP server requirements](https://developers.openai.com/plugins/build/auth): authenticated custom MCP is expected to implement OAuth 2.1 authorization-code + PKCE; publish real protected-resource and authorization-server metadata; and validate token signature, issuer, audience, expiry, and scopes. The same documentation says ChatGPT does not support customer API keys or customer-provided mTLS credentials.
- [Custom MCP server connection options](https://developers.openai.com/api/docs/guides/custom-mcp-server): ChatGPT offers OAuth, no-auth, or mixed authentication. “Static credentials” in its OAuth setup do not establish that a fixed resource-server bearer token is accepted as API-key auth.
- [ChatGPT custom MCP connection help](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt): configure an HTTPS endpoint or supported secure tunnel and the server's authentication.

Read-only requests to `https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server`, `/.well-known/openid-configuration`, and `/.well-known/oauth-protected-resource/mcp` returned HTTP 404 with TLS verification success. This only establishes that these well-known paths are not published at that host; it does not rule out an approved issuer on another host.

The historical Comms and Comms5 Caddy routes remain separate. Their static-bearer validation, header attestation, Host normalization and TLS ingress mechanics can be reused only where compatible. The historical `/mcp` and `/comms5/mcp` paths remain occupied; the remote Caddy host identity/route ownership still requires trusted read-only inspection. No route, tunnel, DNS, or public exposure was changed.

## Current service state

- Dashboard, CME monitor, and event processor: active.
- Assignment intake: inactive; not changed.
- `riverview-grace-execution-owner-session.service`: active under `admin1`.
- Short-name `riverview-grace-owner-session.service`: not found; no restart attempted.
- M33 worker and verifier remain inactive. The previously documented expired-authorization failures were not changed.
- External reasoning MCP: loaded, disabled, inactive; 11827 has no listener.
- Migration `0011` remains applied, with the narrow ACL and zero-production-exchange-row evidence recorded in the preceding commissioning record. No migration or production exchange row was added in this staging step.

## Acceptance status and exact remaining prerequisite

**Local service-path staging: PASS. MCP production loopback: NOT RUN. External ChatGPT exchange: NOT READY. Grace reasoning round trip: NOT demonstrated.**

The outstanding blocker is a verified, approved OAuth authorization-server identity and a reviewed mapping from its validated end-user claims/scopes to the adapter's fixed provider principal. The present adapter accepts static bearer mappings only; the current production configuration has no provider map or MCP env file. Do not create a dummy issuer, token, or provider identity. After an existing approved issuer is identified, the smallest safe next step is a reviewed adapter/gateway change that validates that issuer's tokens and maps exact scopes to the authorized provider, followed by protected credential provisioning, production loopback checks, trusted Caddy ownership inspection, and a separately approved distinct HTTPS route. ChatGPT-side app registration remains unconfigured.
