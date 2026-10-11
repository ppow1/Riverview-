<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-CONVERSATION/20261011T230000Z-live-durability/checkout.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.0
Task: RV-M3.4-CHAT-DURABILITY-001
History: See artifacts.json and Git
-->
# Camrui Grace chat durability recommission

**Recorded:** 2026-10-11 23:00 UTC
**Host:** Camrui, Ubuntu 24.04.3
**Candidate source:** `30085f040d16c666ab8e715e2b9f8c384d1adf9c`
**Deployment ID:** `m3.4-camrui-chat-durable-30085f04`
**Dashboard:** systemd `riverview-status-dashboard.service`, loopback port 8766
**Evidence type:** Live Firefox browser + authoritative production PostgreSQL verification; no chat text or credentials retained.

## Predeployment safeguards

- Existing dashboard was healthy and served status, assignment, event, worker, attention and notification routes with HTTP 200 before switch.
- Prior active release: `/opt/riverview-status-dashboard/releases/8556598b19a7da4aa191a600c767d79d24432afe-docs-d2c145c`; original unit SHA-256 `91cf8ad088f794e763c594981398b881ecf2839cdaf6728eeed64aa4ab1815ca`. That immutable release remains available.
- Candidate package SHA-256 `ec4df447a87e4bafbe99bc6fc023d51e2cd545f412a17d0a07fb5dc3b8999e33`; package manifest and shell compatibility checks passed. Root-owned staged release contents matched the package manifest.
- A protected PostgreSQL custom-format backup was created before activation at `/var/lib/postgresql/backups/riverview/grace-chat-durability-20261011T224800Z/riverview.dump`, mode 0600, `postgres:postgres`. SHA-256: `5ec548fddc2030db0bf0da2cc4bcd724964093e780f2f0c880149c053ad52581`. `pg_restore --list` passed. A disposable restore passed and was dropped by exact unique database name after verification. Counts from the backup: 9 assignments, 1 conversation, 4 conversation events.
- Migration `0003_resident_conversation` was already applied; database checksum matched source `10597d1f0fb91814994ced2a0e3433a0e6aec97152416da3e493754f13033840`. No migration was run for this deployment.
- Existing protected resident/steward/database credentials were read-only. Existing exact Steward grants remain only `resident.conversation.read` and `resident.conversation.send` for `office:office:grace`; no objective or assignment grant was added.
- Candidate drop-in SHA-256 `9ae0e3ba10f6713ba03a71cf66f889cb00a84b90ad1812940bea0411ca01b0d1`; `systemd-analyze verify` passed before restart.

## Live browser and PostgreSQL results

The temporary CPU-only llama.cpp service served `qwen3-0.6b-q8_0-local`, context 4096, zero GPU layers, bound to `127.0.0.1:18796`. Model SHA-256 matched the already-bound Grace implementation revision `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`.

Firefox opened the existing dashboard and used the authorized conversation UI. Two model-backed turns completed. A polling verifier queried PostgreSQL through a fresh independent connection during each pending inference and observed the corresponding user event before the response completed. Following each browser acknowledgment, the authorized conversation API and a new independent PostgreSQL connection matched in sequence and event count:

| Checkpoint | API events | Independently committed PostgreSQL events | Result |
| --- | ---: | ---: | --- |
| First turn | 2 | 2 | PASS |
| Second turn after dashboard restart | 4 | 4 | PASS |

For both turns, browser rendered a nonempty Grace response; assistant model ID and implementation SHA matched the current office binding. Browser refresh restored history. Dashboard restart changed MainPID from 655174 to 656718; service returned active, API recovered, browser reloaded the same history and sent the second turn.

- Dashboard bearer without the office-scoped conversation grant: HTTP 403.
- `/api/v1/status`, `/assignments`, `/events`, `/workers`, `/attention`, `/notifications`, `/objectives`: HTTP 200 after deployment.
- After the initial two turns, PostgreSQL held 9 assignments, 2 conversations and 8 conversation events; `riverview_dev.grace_objectives` remained absent. The predeployment backup had 9 assignments and 1 conversation. Chat added no assignment/objective.
- PostgreSQL `pg_stat_activity`: zero `riverview-status-dashboard` sessions in `idle in transaction` after completed requests.
- Existing assignment intake, event processor, CME monitor, notification dispatcher, M3.3 worker and verifier, and dashboard units all remained active. No SSH, CME, worker, verifier, or notification unit was restarted.

## Interrupted-turn recovery

A third live Firefox session submitted a message. A fresh PostgreSQL connection observed its committed user event while the response was pending. The dashboard alone was restarted. Startup reconciliation wrote `response_interrupted` with `service_restarted`, and the response-status API returned `interrupted`. A subsequent message through the same browser conversation completed and was persisted. API and independent PostgreSQL history both showed the exact four-event sequence `user_message`, `response_interrupted`, `user_message`, `assistant_message`; a new Firefox history load displayed the interruption and assistant response. During the first run, an automation predicate expired at 30 seconds. The model journal showed 31.54 seconds for the follow-up completion; the API and PostgreSQL proved it had succeeded, and the later browser reload verified rendering. This timing out is preserved as a test-harness limitation, not counted as a passing live assertion. Final database state: 9 assignments, 3 conversations, 12 conversation events; no dashboard idle-in-transaction sessions. Detailed sanitized results are in `live-interruption.json`.

## Status and limitation

**Technical commissioning: PASS.** The dashboard is active on the candidate release. The old release and predeployment database backup are retained for rollback. The temporary CPU inference service is a transient systemd unit and does not auto-start after host reboot; host-reboot inference recovery is not claimed. Dashboard restart recovery was tested with the model unit active. This evidence is not formal Steward acceptance or completion of the full Component Definition of Done.
