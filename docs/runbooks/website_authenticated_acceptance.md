# Riverview authenticated website acceptance

Document Revision: 1.0.0

## Personas and authority

`scripts/seed_website_test_personas.py --apply` creates reserved `@riverview.invalid` accounts using Riverview's normal password hash and `viewer`, `operator`, or `steward` roles. `engineering` is a distinct test identity with the existing `operator` website role; it receives no InstitutionalAuthority grant. The test Steward is not linked to `steward:camrui`. The script runs as root, writes generated passwords once to `/etc/riverview/website-acceptance/personas.json` mode 0600, and refuses to reset or adopt an existing unmarked account. Account creation is audited. Do not print or copy the credential file.

An unlinked test Steward can test authenticated notification preferences. It cannot open Grace conversations, exercise cancellation, or receive new engineering grants. Those require an independently approved test principal/grant and disposable objectives. Linux sudo and the website role do not provide those authorities.

## Running checks

`run_website_acceptance.py light` checks actual LAN HTTPS V2 availability. `run_website_acceptance.py full` uses Firefox/geckodriver against `/v2/`, signs into each seeded account through the normal account API, verifies role enforcement and logout, reads notification preferences through the live API and page, and writes the same stored values back for persistence readback. It never submits a Grace message or cancels a production objective.

The installed `riverview-website-acceptance-light.timer` runs every 15 minutes. `riverview-website-acceptance-full.timer` runs every four hours. Timestamped results are in `/var/lib/riverview-website-acceptance/latest.json` and are exposed in the V2 overview and at `/v2/verification/latest.json`. Reports contain check names and statuses only, not credentials, settings values, conversation content, or topic identifiers.

Failures are queued once per incident as `monitor_failed` in the existing `riverview_dev.cme_monitor_events` table. The current notification dispatcher applies its normal policy and NTFY transport. A recovery clears the active deduplication incident; a later failure opens a new incident.

## Deployment and rollback

Run unit tests and candidate-bundle checks before switching the existing Nginx V2 release alias. Keep the current release path and Nginx snippet backup. After switching, run full authenticated acceptance and inspect its result; if a required live check fails, restore the previous alias from the protected backup and reload Nginx. Do not replace the Dashboard `current` symlink or restart Grace/CME services for a static V2 release. Any check that requires InstitutionalAuthority or disposable objective creation remains `SKIPPED` until a purpose-built, separately authorized test principal and isolated test objective mechanism are available.
