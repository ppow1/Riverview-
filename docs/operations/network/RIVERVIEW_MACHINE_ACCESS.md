<!-- Riverview Controlled Document
File: docs/operations/network/RIVERVIEW_MACHINE_ACCESS.md
Component: OPERATIONS-MACHINE-ACCESS
File Revision: 1.0.1
Changed: 2026-10-19 | Steward machine-access index
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
