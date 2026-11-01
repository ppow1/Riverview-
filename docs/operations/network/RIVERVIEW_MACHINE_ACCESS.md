<!-- Riverview Controlled Document
File: docs/operations/network/RIVERVIEW_MACHINE_ACCESS.md
Component: OPERATIONS-MACHINE-ACCESS
File Revision: 1.0.2
Changed: 2026-11-01 | SSH-WRAPPER-001 | Add canonical PowerShell and Bash invocation guidance
Predecessor Blob SHA: cdd606dca2e442c03afb3098d27fe70c1693fe65
-->
# Riverview machine access — canonical quick reference

**Start here from [AI_HINTS.md](../../../AI_HINTS.md).** These are LAN addresses supplied by the Steward; verify reachability and SSH identity against the existing Windows OpenSSH configuration before making changes. No passwords or private-key contents belong here.

| Machine | LAN IPv4 | Windows SSH alias | Login / identity notes |
| --- | --- | --- | --- |
| Camrui Ubuntu controller | `192.168.1.155` | `camrui` | `admin1`; existing Windows OpenSSH identity |
| OctoMiner1 | `192.168.1.160` | `octo1` | Historical configuration: `root`, identity `C:\Users\wille\.ssh\octominer1_nopass`; confirm against Windows config |
| OctoMiner2 | `192.168.1.162` | **Not yet independently verified** | Do not assume `octo2` is configured until checked |
| Windows development workstation | `192.168.1.88` (last observed source IP; confirm if changed) | Local machine | Checkout `A:\Riverview-New-Core` |

## Windows access

```powershell
Clear-Host
ssh.exe -o BatchMode=yes camrui "hostname; whoami; pwd"
ssh.exe -o BatchMode=yes octo1 "hostname; whoami; pwd"
```

To inspect an existing alias safely (including the eventual OctoMiner2 alias), run `ssh.exe -G <alias> | Select-String '^(hostname|user|identityfile) '` from Windows PowerShell. This prints the identity **path**, not its contents. Never guess an alias, username, or key. A raw-IP SSH call may bypass configured alias-specific settings.

## Related operational and recovery records

- [Windows SSH standard (documented on the recovery branch)](https://github.com/ppow1/Riverview-/blob/codex/grace-camrui-local-recovery/docs/operations/network/RIVERVIEW_SSH_STANDARD.md)
- [Camrui / machine connections and Comms5 recovery (recovery branch)](https://github.com/ppow1/Riverview-/blob/codex/grace-camrui-local-recovery/docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md)
- [Camrui local Grace recovery (recovery branch)](https://github.com/ppow1/Riverview-/blob/codex/grace-camrui-local-recovery/docs/operations/GRACE_CAMRUI_LOCAL_EXECUTION_RECOVERY_2026-10-17.md)

**OctoMiner1 BIOS recovery record:** previously discussed and reportedly documented in the BIOS project; its canonical file path has not yet been verified in this repository. Add a direct link once identified rather than inventing one.

## Outstanding inventory verification

1. Confirm OctoMiner2's actual configured SSH alias and identity.
2. Reconfirm the development workstation's last observed LAN IPv4 `192.168.1.88` if its DHCP lease has changed.
3. Link the verified OctoMiner1 BIOS recovery procedure.

## Canonical cross-host shell wrappers (SSH-WRAPPER-001)

Use the checked-in wrappers instead of embedding expandable Bash scripts inside PowerShell here-strings. Both accept a **local Bash script file** and an existing SSH alias; neither embeds credentials or machine addresses. Scripts must use the appropriate interpreter and are not interchangeable.

**From Windows PowerShell:**

```powershell
Clear-Host
& .\scripts\operations\Invoke-RiverviewSsh.ps1 -Alias camrui -ScriptPath .\diagnostics.sh -CopyToClipboard
```

**From a Linux Bash shell:**

```bash
clear
bash ./scripts/operations/invoke-riverview-ssh.sh camrui ./diagnostics.sh --clipboard
```

Use the SSH alias **as configured on the invoking host**. The documented Windows `camrui` and `octo1` aliases are not automatically available on Linux. Verify with `ssh -G ALIAS` before using a new host or alias. Do not assume an OctoMiner2 alias exists.

Both wrappers normalize CRLF to LF before sending a Bash script through standard input, capture remote stdout/stderr, and propagate the SSH exit code. The PowerShell wrapper can copy output with `Set-Clipboard`; the Bash wrapper uses an available `wl-copy`, `xclip`, `xsel`, or `pbcopy`. Clipboard copying is optional and should not change command success status. A nonzero SSH exit code may represent transport failure **or** a nonzero remote command exit; inspect the output.

**Status:** Initial source committed on `engineering/canonical-shell-wrappers-20261101`; host-level verification and promotion remain pending. Do not label either wrapper operationally verified until tested on its respective host.
