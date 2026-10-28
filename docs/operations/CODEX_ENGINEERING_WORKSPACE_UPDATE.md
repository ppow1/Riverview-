<!-- Riverview Controlled Document
File: docs/operations/CODEX_ENGINEERING_WORKSPACE_UPDATE.md
Component: WINDOWS-CODEX-COMMS5
File Revision: 1.0.3
Changed: 2026-10-28 UTC | RV-CODEX-ENGINEERING-WRITE
-->
# Correct the Codex launcher for Engineering source work

## Status and authorization

The Steward explicitly instructed correction of the read-only launcher.
Do not request the same permission again. Existing seven-day unlimited host
grants remain unchanged. This is a launcher correction, not a new grant, key,
dispatcher or service.

Current status:
- Corrected source and rollback-capable Camrui operator updater: INSTALLED.
- Offline regression suite: 16/16 PASS, exit 0.
- Staged Windows package SHA-256:
  `0be897dbf8815aa4345c8cb1c17cc1ddbc08db04580bc340c4651ccf5eb08717`.
- Operator PowerShell script native parser: PASS, zero errors.
- Windows helper: INSTALLED under Gateway LOCALAPPDATA.
- Windows effective Codex turn policy: workspace-write; native MXC selected.
  Real source creation and exact-thread second edit: PASS using cmd.exe shell.
  Independent Node tests through Comms5 PowerShell: PASS after both edits.
  Codex-internal Node startup and apply_patch still fail; retain that limitation.
- Camrui helper/entry update: INSTALLED; direct Comms5 source editing, Python
  tests and exact-thread second edit/test now PASS (October 28, 2026).

The Camrui launcher correction passed direct file-edit/test/exact-thread-resume
acceptance. The full Grace autonomous Engineering workflow remains separate. Codex exit 0 alone is
insufficient: it can mean the model merely reported a denied operation.

## Corrected invocation and workspace

`scripts/riverview_codex_session.py` revision 1.0.3 now constructs:

```text
codex --ask-for-approval never exec --sandbox workspace-write --cd <workspace> [resume] --json --model gpt-6-luna ... -
```

The exec subcommand owns its sandbox/CD flags. Keep them before resume.
Noninteractive attempts outside the workspace fail rather than waiting invisibly
for terminal approval. No danger-full-access or sandbox-bypass flag is used.
The Windows Limited Gateway account additionally selects the documented native
MXC implementation with `-c windows.sandbox="mxc"`.
See [official Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox).
This per-invocation option changes neither accounts nor global Codex config.

Camrui's existing typed entry changes its working root from /home/admin1 to:

```text
/home/admin1/.local/share/riverview/engineering/Riverview
```

The updater creates a separate local Git clone from the existing verified
source checkout /tmp/riverview-grace-worker-diagnostics and checks out exact
`9f56cb72f3bd2961babf2527a26bd843526e18ce`. It preserves that source checkout,
production releases, existing sessions and all SSH key entries. An existing
Engineering clone is not reset or cleaned; its edits survive a repeated update.

## Install on Camrui through the already-working operator SSH connection

The final package is extracted and verified at:

```text
C:\Users\Public\Documents\Riverview\CodexWorkspaceUpdate
```

Run this once in the established desktop-ja3rpnq\wille PowerShell window:

```powershell
Clear-Host
& 'C:\Users\Public\Documents\Riverview\CodexWorkspaceUpdate\Update-RiverviewCamruiCodexWorkspace.ps1'
```

The script captures and displays the entire report and copies it to clipboard.
It uses the existing operator alias camrui, strict host checking and admin1
login. It stages three public Python sources, runs dry-run validation, then
applies the already-authorized correction. No Git fetch, credential copying,
authorized_keys edit, sudo or service restart occurs.

The existing Gateway key invokes a read-only Codex process and cannot rewrite
its own installed wrapper outside the sandbox. Therefore this installation uses
the operator connection that originally installed the wrapper. This is an
execution prerequisite, not a request for new authorization.

Expected final output: INSTALL_EXIT_CODE=0 and WORKSPACE_WRITE_INSTALLED.
Return that report to the active continuation for independent Comms5 acceptance.
Unexpected installed hashes cause refusal, not silent overwrite.

## Updater preservation and rollback

`scripts/upgrade_camrui_codex_workspace.py` validates exact installed
predecessors:
- ssh_codex_entry.py:
  `ac91f7474a0916e0d3d8529f91353b8eb72421eb7e69202abb954b7efd55db90`
- riverview_codex_session.py:
  `9eee1d0dce6916ff8f85b8b693f7de078013112ea6a68b5a81f36a64effc6231`

Before replacing either file, it saves both actual predecessors and their hashes
under /home/admin1/.local/state/riverview/gateway-codex-upgrades/<timestamp>.
It compiles candidate source, verifies backup readback, replaces files using
temporary files/rename, verifies installed bytes and restores originals on a
partial replacement failure. It accepts an identical already-updated candidate
for repeat installation, but refuses an unexpected predecessor. It refuses
symlink/unsafe ownership paths. No private key is read.

Rollback: inspect the returned backup manifest, verify predecessor hashes, then
atomically restore the two saved wrapper files to the manifest root with admin1
ownership and mode 0700. Preserve the Engineering clone and session state.
Restoring these wrappers restores the prior read-only behavior. No production
release pointer or database rollback is involved.

Source predecessors are retained in Git at:
- docs/history/ssh_codex_entry_rev1.0.0.py
- docs/history/riverview_codex_session_rev1.0.1.py
- docs/history/test_ssh_codex_entry_rev1.0.0.py
- docs/history/test_riverview_codex_session_helper_rev1.0.0.py
- docs/history/CAMRUI_GATEWAY_CODEX_COMMISSIONING_rev1.0.1.md
- docs/history/CODEX_DUAL_HOST_CONTROL_RUNBOOK_rev1.0.3.md

Their tree entries reuse exact predecessor Git blobs, not reconstructed bytes.

## Independent Camrui acceptance after installation

1. Submit identity through the existing typed rv-codex-session command. Require
   sandbox=workspace-write, correct Engineering cwd, workspace_ready=true,
   admin1 and the existing host marker.
2. Resume exact existing Camrui thread
   `01a17fdf-6d58-7050-92cc-1762ac986518` with a NEW run ID. Ask Codex to create a
   small source module and test in a disposable subdirectory of the Engineering
   clone and actually execute the test. Do not edit service releases.
3. Retrieve durable Comms5 terminal status and fixed run result. Require actual
   tool events and test output, not just a model assertion. Ask for concise
   replies because fixed artifact retrieval bounds agent-message length.
4. Resume that exact thread with a separate new run ID, make a second bounded
   edit and rerun tests. Preserve actual UUID, files, hashes, exit codes, task
   digests and audit references.
5. Continue Grace recovery on an isolated branch of the exact deployed source.
   Existing institutional criteria, source scope and deployment approval remain
   enforced; this launcher does not authorize arbitrary production changes.

Current Camrui executor:
`grant:8327c8d7a74b4bf78e5529e53057fe69`.
Caller:
`grant:6422d222eca74cb3b328bf3a80384a59`.
No new grants are needed for the commissioned host command path.

## Windows historical failures and current verified editing route

Installed helper:
`%LOCALAPPDATA%\Riverview\CodexControl\workspace-write-v1\riverview_codex_session.py`.
Working root:
`%LOCALAPPDATA%\Riverview\Engineering\write-acceptance`.
Run artifacts:
`%LOCALAPPDATA%\Riverview\CodexControl\workspace-write-v1\state\<run_id>`.

Initial resumed/fresh tests with only the write flag still recorded read-only
turn contexts on Windows. Adding the native Windows sandbox selection produced
an effective workspace-write turn. Exact new thread:
`01a18064-a577-72c3-b907-d26424113128`; older Windows thread
`01a17fb8-8ab0-7993-a547-7f576d8571d4` is preserved.

Run windows-write-acceptance-20261028-04:
- execution e40df6a4-0a24-4ccb-a9a4-7c2c9f4f5bfe, Codex wrapper exit 0;
- terminal audit f82735dc-532d-4af9-ade1-6dc5839d9839;
- actual command_execution failed with -1073741502 (0xC0000142), no output;
- model incorrectly claimed files were created; independent Gateway inspection
  found none. Do not accept that assertion.

Run windows-write-acceptance-20261028-05 resumed that exact thread and attempted
the available apply_patch tool. Its file_change event explicitly failed, and an
independent file check again found no files. Execution
9b22222d-7987-4699-b8ff-cbbf566a6354; terminal audit
0f467fbd-52e3-404c-a5ca-16e3fe650b49.

Independent final check and final package validation:
execution 63f99f38-5415-4373-954b-5e25db3920f9;
audit 3f4d898b-42d1-4e7d-a108-84457244e3ef; exit 0;
package SHA matched and operator script parser errors=0.
This is a verification PASS for package integrity, NOT Windows Engineering PASS.

Next Windows action: diagnose native sandbox startup/ACL/logon compatibility
under RiverviewCmdAgent; retain workspace boundaries and the actual Limited OS
identity. Do not mask this by removing the sandbox or silently using wille's
identity. Ordinary Comms5 PowerShell execution remains working.

## October 28 continuation — Windows source editing verified

MXC is supported on this actual device (build 26340.9596). Probe execution
c9577909-f36c-49de-991d-ba0e1dc33b2d returned MXC_OK, exit 0, audit
9f16c038-c5c2-49f1-ad1a-919b5dee3b82. A separate native MXC cmd.exe workspace-write
probe created/read mxc_probe.txt, exit 0, execution
6bbf2a62-a2db-450c-b0b7-a08c77eaebaf, audit
0e6c028e-aa63-43a8-9665-bee354589962.

Helper revision 1.0.3 selects windows.sandbox="mxc" only on Windows.
It is installed and independently hash-read as:
`2bae3eec74d40b1de090e2f7d566667bcc53a74b31ead04bc76902d56b5ac46b`.
The pre-MXC helper is retained beside it as riverview_codex_session.py.pre-mxc.py.
No account creation, administrator setup, sandbox bypass, credentials or grants
were used. The 16 offline regression tests pass after this change.

Codex apply_patch remains a failing tool on this path. The working supported
route is the shell tool with `C:\Windows\System32\cmd.exe` selected as its
shell, instead of the automatically selected x86 PowerShell. This route retains
the native MXC workspace sandbox.

- Same exact thread: 01a18064-a577-72c3-b907-d26424113128.
- Run windows-write-acceptance-20261028-07, execution
  3e4b5590-29a4-4b23-bf27-8db9905d7a37, final audit
  e6da71f5-47f1-4d9a-9da9-076dffeb91e9: actual cmd.exe tool events created
  sum.cjs and test_sum.cjs and read back both files.
- Codex-internal Node launch still returned -1073741502; no internal test PASS
  is claimed. Independent authorized Gateway PowerShell launched the actual
  test file with Node, exit 0, execution
  6c66bb70-f7aa-4265-b2fb-b4d3e6cdfa5c, audit
  fcc3e44e-b100-4554-ae4d-b3f54d62b5b3.
- Run windows-write-acceptance-20261028-08 resumed the exact same thread and
  appended an additional negative-input assertion using cmd.exe, then read back
  the changed file. Execution 4f37528e-7e8b-4ed9-985f-a833d554b1e6, exit 0,
  audit 897bb9a2-7a56-4298-8f12-3e8fba78d1f4.
- Independent resumed-file Node verification: exit 0, execution
  1f7785ce-9efc-4965-8022-5ac302021b21, audit
  15b6c5d3-8f34-4ba8-8ac4-5731f52b6510.

Thus Windows Codex can actually edit files and preserve editing continuity.
Tests run through the separately authorized existing PowerShell Gateway.
This does not claim that Node now starts inside Codex's native sandbox or that
the full Grace Engineering milestone has completed.

The staged operator package was rebuilt from the verified installed helper and
the three unchanged updater sources; its current SHA-256 is the updated value
at the top of this document. It contains only those four public code files.

Fresh Camrui identity read at 04:42 UTC still reports cwd=/home/admin1 and no
workspace-write metadata, proving the installed correction is still PENDING.
Execution dd1902b9-d724-4080-827a-07fc7b812c28, audit
6ec0c4b3-4b2c-466a-9c89-333fa35550f6. Use the one operator installation command
above; after it returns INSTALL_EXIT_CODE=0, ChatGPT independently verifies
Camrui edits, actual tests and exact-thread resume through Comms5.

Source predecessor revision 1.0.2 is retained at
docs/history/riverview_codex_session_rev1.0.2.py.
Predecessor of this procedure (1.0.0) is retained at
docs/history/CODEX_ENGINEERING_WORKSPACE_UPDATE_rev1.0.0.md.

## Installer revision 1.0.1 — existing private-group ancestry

The first operator dry run stopped before installing anything because the updater
rejected /home/admin1/.local/lib/riverview mode 0775. Read-only inspection through
the existing Camrui thread confirmed:
home 0750, .local 0700, .local/lib 0775, .local/lib/riverview 0775, and
gateway-codex 0700; all admin1:admin1. Admin1's primary group contains only admin1.

The corrected updater accepts group-write access ONLY for the operator's own
private primary group. It checks both supplementary group members and primary
group accounts, and still rejects other-user ownership, world-write, shared
group-write, symlinks and paths outside the operator home. It performs no chmod
on existing directories.

19 offline tests pass (exit 0), including the reported 0775 case, unchanged
directory modes, shared/world-writable/symlink rejection, and both kinds of
additional group membership. Exact replacement validation was executed read-only
on Camrui in Python memory: PATH_VALIDATION_OK and GIT_OBJECT_OK.
Validation run workspace-installer-path-validate-20261028-01,
execution a26192b0-962d-4e46-a03c-a5bdd795fa76,
terminal audit d938efb6-fb3d-4bd2-b9f4-43d672ba4e81.
Result read execution 25c3d14d-56e4-491c-827a-78b734beae3f,
audit 6a90e57e-0e7a-4532-b2d7-9ffbd89e7319.

The corrected updater is re-staged in the SAME Windows directory. Its SHA-256:
e443cb9b515a6534a54653ebc37ef1be7901a92a175d4872991c83e29c72f645.
The current package hash at the top supersedes the earlier packages. Staging
execution e71f4437-ff06-4a8b-91e5-ac43e5d519dc, exit 0,
audit 5fb162a0-1dfd-4396-9525-aa380a15fa72.
The unchanged operator PowerShell command above now copies this corrected file.

Camrui installation remains pending the operator rerun; this validation did not
rewrite the installed entry, helpers, SSH keys, permissions, grants or services.
Preserved exact predecessors:
docs/history/upgrade_camrui_codex_workspace_rev1.0.0.py,
docs/history/test_codex_workspace_upgrade_rev1.0.0.py,
docs/history/CODEX_ENGINEERING_WORKSPACE_UPDATE_rev1.0.1.md.

## Installed Camrui acceptance — October 28, 2026, 08:24–08:27 EDT

The established wille operator installer returned INSTALL_EXIT_CODE=0. Actual
backup: /home/admin1/.local/state/riverview/gateway-codex-upgrades/20261028T122349793352Z.
The operator report records:
- predecessor entry SHA256 ac91f7474a0916e0d3d8529f91353b8eb72421eb7e69202abb954b7efd55db90;
- predecessor helper SHA256 9eee1d0dce6916ff8f85b8b693f7de078013112ea6a68b5a81f36a64effc6231;
- installed entry SHA256 d1217d4a13ae81136aeb54eafcbc81090905eb38e1a5032a40ff15a89f022d1d;
- installed helper SHA256 2bae3eec74d40b1de090e2f7d566667bcc53a74b31ead04bc76902d56b5ac46b.
Authorized_keys was unchanged. The new independent clone is pinned to
9f56cb72f3bd2961babf2527a26bd843526e18ce.

ChatGPT then independently made all acceptance calls through Comms5:
1. identity confirmed admin1, workspace_ready=true, sandbox=workspace-write, cwd
   /home/admin1/.local/share/riverview/engineering/Riverview. Execution
   647f8ccf-a187-4d44-a193-f959df4f3da2, exit 0,
   audit 60662ad2-c9d5-4a10-898a-30e23f88c501.
2. Run camrui-write-acceptance-20261028-01 resumed existing exact Codex thread
   01a17fdf-6d58-7050-92cc-1762ac986518. Initial RUNNING receipt, later terminal
   completed exit 0. Execution 02d4631b-e6db-454d-9e48-678cf02cc3e4,
   final audit e6657832-4785-4ec8-ad50-e573b322f227.
   Codex created .riverview-write-acceptance/sum.py and test_sum.py, verified cwd
   and HEAD, and reported actual Python3 unittest output: Ran 1 test, OK, exit 0.
   Fixed-result retrieval a8aa360b-204b-4e42-a2b1-4e505d0a371f, audit
   3fd2287d-7056-4f19-b20e-85e98172f0db.
3. A separate new run camrui-write-acceptance-20261028-02 resumed that same exact
   thread, read the existing files, added a separate negative-input test, and ran
   verbose unittest. Result: 2 tests, OK, exit 0. Execution
   b24222b3-3a36-4b32-8d7c-cc4f545b5512, final audit
   d8a8bbea-b4a6-40cd-908a-b7261f8176d3. Result retrieval
   1c7ca01a-1cae-435e-a287-3871993979fe, audit
   72196130-3bfe-4c14-9688-a0e5d58b8fc3.
   Reported SHA256:
   sum.py ba1a531f581d2e6094e978ed6f7aca7a8d92eeb62c6e7ad73ee692f7f18bc772;
   test_sum.py 5a61fbe9e585a5a521148496a72eef400e4b57698fc45b94f17891c3413d94ce.

All accepted runs use the existing OS account, Codex login, caller grant and
unlimited executor grant. No operator relayed the acceptance commands. The fixed
result projection exposes bounded Codex messages and CLI metadata; complete tool
events remain in each account-local events.jsonl. The test counts and file hashes
above are from those retrieved Codex result messages, not a new independent
institutional verifier decision. Do not infer Grace objective completion.

Durable acceptance receipts and command digests are retained at
evidence/checkouts/WINDOWS-CODEX-COMMS5/20261028T1226Z/camrui-workspace-write.md.
The former read-only blocker for source editing is resolved. Ordinary commands
within the Codex workspace now run through the same typed launcher; the SSH
entry itself still accepts its documented typed protocol.

Predecessor of this runbook (1.0.2):
docs/history/CODEX_ENGINEERING_WORKSPACE_UPDATE_rev1.0.2.md.
