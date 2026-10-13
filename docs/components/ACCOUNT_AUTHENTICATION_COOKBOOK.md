<!--
Riverview~ Controlled Document
File: docs/components/ACCOUNT_AUTHENTICATION_COOKBOOK.md
Component: WEBSITE-ACCOUNT-AUTH
File Revision: 1.3.0
Purpose: Safely commission and diagnose Riverview account access and reusable SMTP configuration
Authority: Inspection is read-only; provider setup and Steward bootstrap require explicit local authorization
Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Document password login, grants and email-provider commissioning
Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-COMMIT-AND-STACKMAIL-PREP | Prepare candidate Stackmail SMTP profile and secure local entry command
Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-STACKMAIL-LOCAL-TEST | Document predeployment isolated SMTP and mailbox receipt test
History: Git and revision/backup manifest
-->
# Account authentication diagnostics and commissioning

This guide distinguishes repository verification from live readiness. Camrui has no account schema migration or configured account email provider. Website account login is therefore not deployed. The dashboard bearer recovery path remains active.

## Read-only diagnosis

| Check | Command | Expected / failure interpretation |
| --- | --- | --- |
| Dashboard service | `systemctl is-active riverview-status-dashboard.service` | `active`; account routes share this service after deployment. |
| Current release | `readlink -f /opt/riverview-status-dashboard/current` | Versioned release path; do not change it for diagnosis. |
| Account schema | `sudo -u postgres psql -X -d riverview -c "SELECT to_regclass('riverview_accounts.schema_migrations');"` | `schema_migrations` means initialized; null means absent. |
| Migration versions | `sudo -u postgres psql -X -d riverview -c "SELECT version, applied_at FROM riverview_accounts.schema_migrations ORDER BY version;"` | Versions/checksums must match the release migration set. |
| Account service status | Authenticated `GET /api/v1/status` | Read bounded readiness counts/status; no personal data or secrets. |
| Provider settings status | Steward-only email settings UI/API | Shows configured fields, password-configured flag and last test/delivery state; never returns SMTP password. |
| Bootstrap identity | `sudo -u postgres psql -X -d riverview -c "SELECT principal_id, status FROM riverview_authority.institutional_principals WHERE principal_id='steward:camrui';"` | Existing active Steward identity must remain present. Do not query credential tables. |

Never print challenge tokens, cookies, SMTP passwords, private keys, database DSNs with credentials, or passfiles into terminal capture, logs, shell history, or evidence.

## CueMastery email hosting findings

Public DNS currently points email to `mx.stackmail.com`, with SPF including `spf.stackmail.com`; this indicates existing 20i/Stackmail hosting. The mailbox/control-panel credentials and permission to send as the desired sender were not verified. Prepare this candidate profile for Steward/provider confirmation:

| Setting | Candidate value | Verification still needed |
| --- | --- | --- |
| SMTP host | `smtp.stackmail.com` | Confirm it is the active outgoing host for the CueMastery mailbox. |
| Port | `465` | Confirm outbound connection is allowed from Camrui. |
| TLS mode | `implicit` (TLS from connection start) | Confirm certificate and account policy with Stackmail. |
| Username | `social@cuemastery.com` | Confirm the mailbox exists and is the authorized SMTP account. |
| Sender address | `social@cuemastery.com` | Confirm the account may send as this address. |
| Administrator notification address | `social@cuemastery.com` | Steward-specified destination; confirm it receives mail. |
| Password | Enter only at the hidden prompt in the local root-console wizard | Never send it in chat, command arguments, shell history, source, or reports. |

20i also documents port 587 with STARTTLS; the proposed profile above uses port 465. These remain candidate settings, not verified account credentials or delivery readiness. No mail server or paid provider is being introduced.

## Isolated predeployment SMTP test

The dashboard's provider test reads settings from the account database and systemd key credential, so it cannot be safely used before account-schema commissioning. Use `scripts/test_stackmail_mailbox.py` from Camrui's **local physical terminal, outside SSH and outside Codex**. It has no database/service dependency. It prompts for an explicit one-message confirmation, accepts the mailbox password through hidden terminal input, authenticates to `smtp.stackmail.com:465` with implicit TLS, and sends exactly one test message from the mailbox to itself. It does not persist the password or settings. It then asks for the password again and searches INBOX read-only over IMAP for the unique Message-ID; it prints only authentication/submission/receipt outcomes and sanitized exception classes. If IMAP verification fails or times out, inspect Inbox and Junk manually. Do not put the password in shell arguments, environment variables, scripts, Codex input, or terminal recording.

Run it as:

```bash
cd /home/admin1/projects/Riverview-New-Core
python3 scripts/test_stackmail_mailbox.py
```

This sends one real email but changes no Riverview database or dashboard configuration. A PASS from SMTP means authenticated relay submission; only the read-only mailbox search or manual mailbox inspection confirms receipt.

## Commissioning sequence

1. Publish/checkout the reviewed release to Camrui only after commissioning approval. Then have the local PostgreSQL administrator inspect and apply the additive schema provisioning plan:

   ```bash
   sudo -u postgres python3 /opt/riverview-status-dashboard/current/scripts/provision_account_auth_schema.py
   sudo -u postgres python3 /opt/riverview-status-dashboard/current/scripts/provision_account_auth_schema.py --apply
   sudo -u postgres env PYTHONPATH=/opt/riverview-status-dashboard/current/src python3 /opt/riverview-status-dashboard/current/scripts/migrate_account_auth.py
   sudo -u postgres python3 /opt/riverview-status-dashboard/current/scripts/provision_account_auth_schema.py --apply
   ```

   The dedicated schema owner is NOLOGIN; the dashboard runtime receives only necessary DML grants. Never put account tables in `public`, `riverview_dev`, or `riverview_authority`. Do not migrate the live database until the release is reviewed and deployment is authorized.
2. Use Camrui's **local physical root console** to configure provider settings, after the reviewed release and schema migration are commissioned. Run `sudo python3 /opt/riverview-status-dashboard/current/scripts/configure_account_email_provider.py`. The root wizard requires the exact phrase `CONFIGURE RIVERVIEW EMAIL`; it creates an owner-only Fernet key, prompts for the candidate SMTP settings above, and reads the password using hidden terminal input before storing it encrypted in PostgreSQL. It rejects SSH/non-TTY execution and sends no message during initial configuration. Install the matching systemd credential drop-in only after the key exists. Enter the initial requested administrator inbox `social@cuemastery.com` at setup time; source and UI do not default to that address.
3. Confirm authority to send through the CueMastery mailbox, and use the SMTP test-email function to a controlled inbox. Confirm actual receipt, sender/reply-to, TLS delivery, and success/failure status. SMTP acceptance alone is not proof of inbox delivery. Check that a wrong password or unavailable relay is reported without exposing credentials.
4. Request access using a controlled test address. Verify the ownership challenge, pending state, and administrator notification. Open the notification link while signed out and confirm it does not expose the request or perform a decision. Sign in as Steward and review the request.
5. Exercise denial and each grant choice (one-time, 90 days, one year, permanent), roles, applicant notices, expiry/revocation behavior, and the one-session-only rule. A one-time grant allows only the first session ever, with a maximum 24-hour session; logout, expiry or revocation never makes a second session available.
6. Run the local-only `scripts/bootstrap_account_steward.py` from a physical root console after real delivery is verified. It requires the exact confirmation phrase, checks `steward:camrui`, and emails a one-use password-setup link. Complete the link, sign in, and verify queue, email settings, role/grant controls, recovery-token login, and exact-grant engineering boundaries before changing any recovery mechanism.

The systemd credential source path in the checked-in drop-in is `/etc/riverview/account-email-config.key`; its content must stay root-owned and mode 0600. Runtime access is via systemd's credential directory and does not expose the key to the browser or logs. Do not place SMTP credentials in environment variables, source control, or browser configuration. Do not enable autonomous Grace/Riverview mail workflows as part of this commissioning.

## Failure interpretation

| Outcome | Meaning | Safe next step |
| --- | --- | --- |
| `not_initialized` / missing relation | Account schema absent or migration incomplete | Verify release migration checksums and provisioning grants; do not restart repeatedly. |
| `unavailable` / HTTP 503 | Database/schema/key access issue | Inspect sanitized service error category and read-only grants; preserve secrets. |
| `email_delivery_unavailable` | No usable configured transport | Confirm key credential and provider settings; run test-email only after authorized configuration. |
| SMTP test failed | Relay/TLS/auth/address error | Review sanitized status and provider account settings; never log password. |
| Challenge invalid/expired | Challenge malformed, used, or older than 15 minutes | Request a fresh message; never edit challenge rows manually. |
| `not_authorized` / HTTP 403 | Role, session or CSRF check failed | Re-authenticate or ask a Steward; never weaken server checks. |
| Session denied | Disabled account, expired/revoked grant or session | Steward reviews account; one-time grants cannot create replacement sessions. |

For application rollback, restore the previous versioned dashboard release and restart only `riverview-status-dashboard.service` when deployment has occurred and rollback is needed. Preserve the additive account data and bearer recovery path.

## Evidence boundary

The source suite includes disposable PostgreSQL integration checks, HTTP checks, and a loopback HTTPS Firefox browser flow. These do not prove Camrui migration, live email delivery, an actual Steward bootstrap, or production browser authentication. Record these as unverified until commissioned with real provider access and receipt confirmation.
