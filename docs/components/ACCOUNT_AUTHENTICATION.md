<!--
Riverview~ Controlled Document
File: docs/components/ACCOUNT_AUTHENTICATION.md
Component: WEBSITE-ACCOUNT-AUTH
File Revision: 1.1.0
Purpose: Specify verified enrollment, password access, Steward approval, grants, sessions and reusable email configuration
Authority: Website roles protect the dashboard only; engineering authority remains exact-grant based
Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Specify password login, access grants and SMTP administration
History: Git and revision/backup manifest
-->
# Riverview website account authentication

**Component:** WEBSITE-ACCOUNT-AUTH  
**Execution model:** Request-driven account API backed by PostgreSQL 16.  
**State:** Source and isolated verification are ready for commissioning; actual email delivery, live schema, Steward bootstrap and deployment are not verified.

## Visitor and Steward flows

The welcome page offers Portal Login and Request Access. Portal Login accepts an email and password. Request Access accepts an email, sends a single-use ownership challenge, and shows **Pending Steward Approval** after a successful verification. A pending applicant has no account session and cannot access protected dashboard functions.

An authenticated Steward opens the approval queue from the dashboard. The notification email contains a Camrui page link with a request identifier only. Opening the link never decides the request: the visitor must authenticate as a Steward and choose Deny or Approve. Approval records a role (Viewer, Operator, or explicitly assigned Steward), grant type, expiry where applicable, approving Steward, and audit time. The applicant receives an outcome email. Failure to deliver a notification is recorded and does not change the decision.

Available grants are one-time, 90 days, one year, and permanent. One-time means at most one authenticated session can ever be created under that grant. That session expires no later than 24 hours after issue; no second session can be created even if the first expires or logs out. Grant expiration, explicit revocation, account disablement, or role removal invalidates active sessions on the next protected request. 90-day and one-year grants expire at their stored UTC timestamp; permanent grants have no grant expiry but remain revocable.

## Authority boundary

Viewer, Operator, and Steward are website roles stored in the dedicated `riverview_accounts` schema. They govern website access only. An Operator or Steward login does not create an institutional principal, AuthorityRegistry grant, assignment capability, or permission to execute engineering work. Existing Grace and objective operations retain their independent exact-grant checks. The protected dashboard bearer remains an administrative recovery mechanism throughout commissioning.

Only an authenticated Steward can review requests, assign roles, configure email, disable an account, change roles, or revoke grants/sessions. Public enrollment never grants a role. The server validates every permission; browser controls are not authority.

## Persistence and session security

Additive migrations under `src/riverview_core/account_auth/migrations/` create account, verified-email, enrollment, role, challenge, session, audit, grant and email-provider records in the dedicated schema. The checksum-pinned migration runner is explicit; application startup never creates tables. Challenge and session verifiers are high-entropy random values stored only as hashes. Challenges are single-use, expire after 15 minutes, and are rate-limited. Passwords use salted scrypt hashes; minimum length is 12 characters. Password reset requires a verified email challenge and revokes existing sessions.

Sessions use random server-checked verifiers stored only as hashes. Standard session duration is 30 days, capped by grant expiry. Cookies are Secure, HttpOnly, SameSite=Lax, host-only; state-changing cookie requests require a session-bound CSRF token. Session fixation is prevented by issuing a fresh verifier after authentication. The account, session, grant expiry/revocation and role are checked on every protected request. Session revocation and grant expiry therefore deny the next request, not merely the next login.

Audit rows record decision/action, subject, actor, role/grant metadata and timestamp, never credentials, challenge values, session verifiers, SMTP secrets or message contents. Rate limits and generic public responses reduce enumeration. Email-link opening performs no state-changing approval action.

## Email provider configuration

Steward-only settings UI supports SMTP host and port, TLS mode, sender address and display name, administrator notification address, reply-to, username, password update, test message, and delivery/test status. Password is never returned to the browser. It is encrypted in PostgreSQL using a Fernet key held in a root-controlled local key file and supplied to the service through a systemd credential. The local-only `scripts/configure_account_email_provider.py` wizard creates/uses this key and stores settings without printing the password. Blank password on update retains the existing encrypted value.

The provider is a reusable transport abstraction. Only account authentication uses it in this campaign; no autonomous Grace or Riverview email workflows are enabled. Real sending remains disabled until the SMTP key and database settings are commissioned. Delivery acceptance must be followed by receipt verification; a configured host or successful test API response alone is not proof of mailbox delivery. Test failures and delivery outcomes are stored without credentials or message bodies.

CueMastery public DNS currently advertises `mx.stackmail.com` and SPF `include:spf.stackmail.com`; this indicates existing 20i/Stackmail email hosting, but mailbox access and credentials have not been confirmed. 20i documentation identifies `smtp.stackmail.com` with port 465 implicit TLS or port 587 STARTTLS. These are candidate settings, not prefilled credentials or proof that the administrator mailbox is usable. Configure the administrator notification inbox during commissioning (initial requested destination: `social@cuemastery.com`) without hard-coding it. Do not create a mail server or purchase a provider for this work.

## Steward bootstrap and recovery

The existing institutional `steward:camrui` identity can be linked only through `scripts/bootstrap_account_steward.py`, an explicitly authorized local root console process. It checks the active principal, rejects SSH/non-TTY use, requires an exact confirmation phrase, and sends a single-use verification challenge to the supplied email. It never grants Steward to a public applicant and creates no default password. After challenge verification, set a password through the emailed setup link. Do not disable the dashboard bearer recovery path until the new Steward has signed in and demonstrated account administration.

## API surface

| Method and route | Authority | Purpose |
| --- | --- | --- |
| `POST /api/v1/auth/enrollment`, `/enrollment/verify` | Public request; single-use challenge | Request access and verify email; verified request becomes pending |
| `POST /api/v1/auth/login` or `/api/v1/auth/session` | Public, rate-limited | Email/password login and session issuance |
| `POST /api/v1/auth/password-reset`, `/password-set` | Public, single-use challenge | Reset or establish password; revoke prior sessions on reset |
| `GET` / `DELETE /api/v1/auth/session` | Account session; CSRF for delete | Read identity or log out |
| `GET /api/v1/account/enrollments`, `GET /api/v1/account/users` | Steward | Review queue and account/grant listing |
| `POST /api/v1/account/enrollments/{id}/decision` | Steward plus CSRF | Deny or grant role and duration |
| `POST /api/v1/account/users/{id}/disable`, `/roles`, `/sessions`, `/grant` | Steward plus CSRF | Disable, change role, revoke sessions or revoke a grant |
| `GET/PUT /api/v1/account/email-settings`, `POST .../email-settings/test` | Steward; CSRF for mutations | Configure reusable SMTP provider and test delivery |
| `POST /api/v1/auth/steward-bootstrap/verify` | Single-use challenge from local bootstrap only | Verify pre-authorized existing Steward identity |

The dashboard bearer remains accepted for recovery. Account auth does not weaken existing dashboard authentication, Grace authorization, engineering action approval, or API visibility constraints.

## Commissioning boundary

No account schema migration, provider configuration, Steward bootstrap, or application deployment has been applied to Camrui. Isolated PostgreSQL, HTTP and browser checks establish source behavior only. Real applicant email, administrator notification, applicant outcome delivery, live login, and deployed authorization remain blocked until the migration and provider are configured, actual delivery is confirmed, a Steward is bootstrapped, and the verified release is commissioned. See `ACCOUNT_AUTHENTICATION_COOKBOOK.md`.
