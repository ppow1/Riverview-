<!-- Riverview Controlled Document
File: docs/operations/network/RESOURCE_TELEMETRY_HOST_SETUP.md
Component: OPERATIONS-RESOURCE-TELEMETRY
File Revision: 1.0.0
Changed: 2026-10-22 | ISSUE-231 | Document optional host collector commissioning
Authority: Read-only telemetry commissioning; no host or production changes are authorized by this document
-->
# Windows and OCTO2 telemetry commissioning

The Dashboard reads telemetry through `GET /api/v1/resources/telemetry`. The V2 page does not call hosts directly. Until credentials and pinned host keys are installed, the Windows and OCTO2 cards report unavailable without attempting SSH.

## Dashboard credentials

The collector accepts these systemd credentials. Each value must be provisioned as a separate protected file and exposed using `LoadCredential=` in the Dashboard service drop-in:

| Credential | Content |
| --- | --- |
| `resource-telemetry-octo2-key` | Dedicated private key for OCTO2's restricted telemetry account |
| `resource-telemetry-octo2-known-hosts` | Independently verified OCTO2 SSH host key |
| `resource-telemetry-octo2-user` | Restricted OCTO2 telemetry account name |
| `resource-telemetry-windows-key` | Dedicated private key for Windows OpenSSH's restricted telemetry account |
| `resource-telemetry-windows-known-hosts` | Independently verified Windows SSH host key |
| `resource-telemetry-windows-user` | Restricted Windows telemetry account name |

The current source allowlist uses OCTO2's documented `192.168.1.162` address and the Windows workstation's last recorded address `192.168.1.88`. The Windows address must be reconfirmed before commissioning. Both targets use strict host-key checking and a dedicated username; do not add guessed aliases, identities, usernames, or host keys.

## Host-side command

For OCTO2, first verify the hostname and operating system when the machine is reachable. If it is a Linux NVIDIA host, install `scripts/rv_gpu_telemetry_command.py` behind the dedicated forced command `resource-telemetry`, with no shell, forwarding, PTY, or arbitrary command access. This is the same JSON contract and collector used by the existing NVIDIA telemetry source. Do not provision it while OCTO2 is offline or before verifying machine identity.

For Windows, install `scripts/rv_windows_resource_telemetry.ps1` at a protected path and configure the dedicated OpenSSH account/key to force `powershell.exe -NoProfile -NonInteractive -File <protected-script-path>`. The collector accepts only `SSH_ORIGINAL_COMMAND=rv-windows-resource-telemetry`. Limit the account to this read-only collector; do not grant an interactive shell or forwarding.

## Verification

Before enabling either credential set, verify the presented host key out of band, then run the Dashboard telemetry parser and the V2 browser checks with recorded or synthetic payloads. Confirm absent GPU/RAM/storage measurements remain unavailable, stale timestamps are labeled stale, and duplicate mounted filesystems are counted once. Live Windows verification requires an available Windows machine and verified SSH identity. OCTO2 live verification remains deferred while it is offline.

These steps describe a future commissioning procedure. They do not provision credentials, change an SSH server, restart the Dashboard, or deploy the V2 website.
