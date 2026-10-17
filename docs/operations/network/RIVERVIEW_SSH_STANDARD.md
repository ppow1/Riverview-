<!--
Riverview Controlled Document
File: docs/operations/network/RIVERVIEW_SSH_STANDARD.md
Component: OPERATIONS-SSH
File Revision: 1.0.0
Status: Verified Windows-to-Camrui access standard
Date: 2026-10-17
Authority: Existing operator-controlled OpenSSH configuration; this document creates no credentials or access.
Changed: 2026-10-17 UTC | RV-CAMRUI-SSH-ACCESS-DOCUMENTATION-001 | Record verified Windows alias and execution-environment boundary.
History: New file in this integration checkout.
-->

# Riverview SSH standard

## Verified Windows access path

The established Windows OpenSSH alias is `camrui`. The Steward verified it from Windows PowerShell with:

```powershell
ssh.exe -o BatchMode=yes camrui "hostname; whoami; pwd"
```

Verified output:

```text
admin1-Default-string
admin1
/home/admin1
ExitCode: 0
```

Authentication uses the identity selected by the existing Windows OpenSSH configuration. Inspect the effective non-secret mapping with:

```powershell
ssh.exe -G camrui | Select-String '^(hostname|user|identityfile) '
```

The identity file remains on the Windows development workstation. Its exact path was not exposed to the Camrui Linux execution environment, so this document does not guess it. Never copy its private-key contents into Riverview, GitHub, logs, or chat.

Use the alias for Windows operator tasks:

```powershell
ssh.exe -o BatchMode=yes camrui "hostname; whoami; pwd"
```

## Execution-environment distinction

The Codex Linux shell used for the 2026-10-17 Comms5 work was already running on Camrui as `admin1`, at `/home/admin1`. It can inspect Camrui's local services and files directly. It does not inherit the Windows OpenSSH configuration or Windows identity file. A Linux `ssh camrui` failure caused by an unresolved alias is therefore a client-configuration boundary, not evidence that the Camrui SSH server is down and not an authentication failure.

Do not retry the Windows-only alias from Linux. Use the local Camrui shell for authorized on-host work, or use the verified Windows PowerShell alias when a separate operator connection is required.

## Diagnosing failures safely

1. Run `ssh.exe -G camrui` in Windows PowerShell. This checks alias resolution and shows effective host, user, and identity-file path without reading a private key.
2. Run the headless command above. A successful hostname/user/path result with exit code 0 confirms the configured path.
3. If SSH reports `Could not resolve hostname camrui` or the alias is absent from `ssh.exe -G`, diagnose the Windows client alias/configuration. Do not change Camrui's SSH service.
4. If the connection reaches the host but reports `Permission denied (publickey)`, diagnose identity selection or server-side authorization through the approved operator process. Do not generate replacement keys as a first response.
5. If SSH reports an unknown or changed host key, stop and verify it against an independently trusted fingerprint. Never disable strict host-key checking or accept an unverified key.

The Windows alias/identity was verified by the Steward. The Linux shell's lack of that alias does not imply an access problem from Windows. The machine-specific record is maintained in `docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md`.
