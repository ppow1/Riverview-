<!--
Riverview~ Controlled Document
File: docs/operations/GRACE_CAMRUI_LOCAL_EXECUTION_RECOVERY_2026-10-17.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Purpose: Recover a Grace release runner that is already executing on Camrui
Authority: Existing controlled release and exact Steward authorization procedures
Changed: 2026-10-17 UTC | RV-GRACE-CAMRUI-LOCAL-RECOVERY | Record verified host-local recovery and live release provenance
History: Git and .riverview-backups/manifest.jsonl
-->
# Grace Camrui local execution recovery

## Failure signature and decision

Before attempting network access, run `hostname`, `whoami`, `pwd`, and
`ip -br addr`. On the verified Camrui execution environment they identify
`admin1-Default-string`, `admin1`, `/home/admin1`, and `192.168.1.155/24` on
`eno1`. This is the target host itself. Run local deployment commands there;
do not try SSH to the host's own LAN address.

The observed `ssh camrui` failure was alias/name resolution in a Linux shell
that did not carry the Windows SSH alias. A later direct SSH attempt to
`admin1@192.168.1.155` also failed because the runner was already on that
machine. Neither failure demonstrated a Camrui network or sshd outage. The
Windows-specific alias and authorized remote path are documented in
[`network/RIVERVIEW_SSH_STANDARD.md`](network/RIVERVIEW_SSH_STANDARD.md) and
[`RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md`](RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md).

## Release safeguards

Use the established local package verification and controlled deployment
procedure. Confirm the package manifest, source commit, checksum, installed
release pointer, and predecessor before switching anything. If the expected
predecessor does not match, stop before writes and identify the newer active
release. Never downgrade a current release to an older verified archive when
the live release contains later merged work.

For the 2026-10-17 recovery, PR #101's accepted package was sourced from
`9697a593e0c5a3f6d070696c51e3a9f8c91dfca7`. Before it could be installed, the
Grace and dashboard `current` pointers advanced to
`6b44b39ae474e6389f26c97a2c70200f09f33e55`, the merge commit for PR #100 with
PR #101 as first parent. The installed 6b44 release includes the persisted
acceptance-criteria resolver and PR #100 Comms5 changes. The predecessor guard
refused the stale 9697 package before staging or switching a release. Its
`PACKAGE_SHA256SUMS` file has SHA-256
`f19b64970be8364f159f7a24d3c35dc89c0ff73002efd3a6f85a2c4604438efd`, and all
entries passed `sha256sum -c` from the release directory. The stale 9697
archive checksum is
`199bd6131f96b99596c37163a8b13e56a42d86cd099490c21340664cf3ee28d4`. Keep the
6b44 release and the active Comms5 configuration intact.

## Live state and remaining acceptance boundary

At 2026-10-17 19:59 EDT, local Camrui checks found
`riverview-grace-execution-owner-session.service` and
`riverview-status-dashboard.service` active. The authenticated Comms5 CME
projection reported `healthy`, 7 registered workers, 3 enabled workers, and a
fresh heartbeat. The deployed Grace file contained the PR #101 acceptance
criteria resolver.

A fresh work objective must still enter through the established authenticated
Steward flow, which records the exact immutable criteria and checks the exact
`objective.submit` grant. The shell had the protected authority-manager and
service credentials but no authenticated Steward account session. Those
manager and service credentials cannot substitute for a Steward session.
Therefore no fresh objective was created during this recovery, and no complete
objective-to-next-action cycle is claimed. Resume with an authenticated
Steward session; then inspect durable objective, work-order, execution,
verification, Grace evaluation, and next-action records in PostgreSQL, and
perform the controlled restart/recovery check against that actual objective.

For Grace service health and objective troubleshooting, see
[`../components/GRACE_EXECUTION_COOKBOOK.md`](../components/GRACE_EXECUTION_COOKBOOK.md).
