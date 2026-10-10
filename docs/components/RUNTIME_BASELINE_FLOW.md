# Riverview~ runtime baseline process map

**Document Revision:** 1.0.7
**Component:** RUNTIME-BASELINE
**Repair task:** RV-M1.1-011
**Workflow:** runtime-baseline.v1
**Task:** RV-M1.1-001
**Status:** credential and loopback identity corrections implemented; live acceptance in progress

```mermaid
flowchart LR
  subgraph g_rv_runtime_baseline_commissioning["RUNTIME-BASELINE / runtime-baseline.v1"]
    g_rv_runtime_baseline_commissioning_source_140689b5(["Committed source revision"])
    g_rv_runtime_baseline_commissioning_package_3cd1d388["Build and verify package"]
    g_rv_runtime_baseline_commissioning_package_valid_6bba7611{"Archive digest, commit, manifest and safe members valid?"}
    g_rv_runtime_baseline_commissioning_package_failure_60e040f5[["Preserve failed package; rebuild corrected source"]]
    g_rv_runtime_baseline_commissioning_stage_a440a82c["Extract verified archive into protected staging"]
    g_rv_runtime_baseline_commissioning_install_eb630d88["Preserve predecessor; run fixed installer"]
    g_rv_runtime_baseline_commissioning_credential_present_2a998cb6{"Protected credential source exists?"}
    g_rv_runtime_baseline_commissioning_credential_entry_69efc5a8(["Prompt on controlling TTY with echo disabled"])
    g_rv_runtime_baseline_commissioning_tty_failure_9f7ff773[["Fail closed; passfile remains absent"]]
    g_rv_runtime_baseline_commissioning_retry_install_b5c16e8f["Check partial ownership, retry corrected installer"]
    g_rv_runtime_baseline_commissioning_systemd_94650c30["systemd starts unprivileged probe with LoadCredential"]
    g_rv_runtime_baseline_commissioning_credential_copy_0e7104be["Validate source; copy to private mode-0600 runtime passfile"]
    g_rv_runtime_baseline_commissioning_identity_f18d12d8{"Correct non-login service identity?"}
    g_rv_runtime_baseline_commissioning_storage_55ff245b{"Private service-owned state directory?"}
    g_rv_runtime_baseline_commissioning_credential_check_4afa1b6b{"Safe credential file and no ambient override?"}
    g_rv_runtime_baseline_commissioning_database_af2ea5fc["Read-only PostgreSQL identity and privilege check"]
    g_rv_runtime_baseline_commissioning_schema_4b3917f9{"riverview_dev owner and access match?"}
    g_rv_runtime_baseline_commissioning_blocked_f632b2f4[["Report accountable blocker and preserve diagnostics"]]
    g_rv_runtime_baseline_commissioning_diagnose_3ea935df["Diagnose and repair using cookbook; retry probe"]
    g_rv_runtime_baseline_commissioning_ready_1e7806fe(["Ready: baseline verified; wider institution not verified"])
    g_rv_runtime_baseline_commissioning_observe_de37d88a["Independent observer validates revision and timestamp"]
    g_rv_runtime_baseline_commissioning_fresh_13eb70ab{"Observation fresh and valid?"}
    g_rv_runtime_baseline_commissioning_stale_cf5d29be[["Stale, missing or invalid observation is not ready"]]
    g_rv_runtime_baseline_commissioning_accept_decision_b7391255{"Steward accepts scoped M1.1 evidence and sequencing?"}
    g_rv_runtime_baseline_commissioning_accept_hold_47cf9721[["Record acceptance hold; independent M1.2 engineering may continue"]]
    g_rv_runtime_baseline_commissioning_acceptance_e02b3dea["Record scoped M1.1 technical acceptance; full DoD remains open"]
    g_rv_runtime_baseline_commissioning_m12_jump_d59d1f04["M1.2 shared-schema migration workflow"]
  end
  g_rv_postgres_ledger_migration_apply_0f7d74d6["Registered target<br/>rv:postgres-ledger:migration"]
  g_rv_runtime_baseline_commissioning_source_140689b5 --> g_rv_runtime_baseline_commissioning_package_3cd1d388
  g_rv_runtime_baseline_commissioning_package_3cd1d388 --> g_rv_runtime_baseline_commissioning_package_valid_6bba7611
  g_rv_runtime_baseline_commissioning_package_valid_6bba7611 -->|diagnostic_branch: No| g_rv_runtime_baseline_commissioning_package_failure_60e040f5
  g_rv_runtime_baseline_commissioning_package_failure_60e040f5 -->|recovery_route| g_rv_runtime_baseline_commissioning_package_3cd1d388
  g_rv_runtime_baseline_commissioning_package_valid_6bba7611 -->|Yes| g_rv_runtime_baseline_commissioning_stage_a440a82c
  g_rv_runtime_baseline_commissioning_stage_a440a82c --> g_rv_runtime_baseline_commissioning_install_eb630d88
  g_rv_runtime_baseline_commissioning_install_eb630d88 --> g_rv_runtime_baseline_commissioning_credential_present_2a998cb6
  g_rv_runtime_baseline_commissioning_credential_present_2a998cb6 -->|No| g_rv_runtime_baseline_commissioning_credential_entry_69efc5a8
  g_rv_runtime_baseline_commissioning_credential_entry_69efc5a8 -->|diagnostic_branch: TTY failure| g_rv_runtime_baseline_commissioning_tty_failure_9f7ff773
  g_rv_runtime_baseline_commissioning_tty_failure_9f7ff773 -->|recovery_route| g_rv_runtime_baseline_commissioning_retry_install_b5c16e8f
  g_rv_runtime_baseline_commissioning_retry_install_b5c16e8f -->|recovery_route| g_rv_runtime_baseline_commissioning_stage_a440a82c
  g_rv_runtime_baseline_commissioning_credential_present_2a998cb6 -->|Yes| g_rv_runtime_baseline_commissioning_systemd_94650c30
  g_rv_runtime_baseline_commissioning_credential_entry_69efc5a8 -->|Captured| g_rv_runtime_baseline_commissioning_systemd_94650c30
  g_rv_runtime_baseline_commissioning_systemd_94650c30 --> g_rv_runtime_baseline_commissioning_credential_copy_0e7104be
  g_rv_runtime_baseline_commissioning_credential_copy_0e7104be --> g_rv_runtime_baseline_commissioning_identity_f18d12d8
  g_rv_runtime_baseline_commissioning_identity_f18d12d8 -->|diagnostic_branch: No| g_rv_runtime_baseline_commissioning_blocked_f632b2f4
  g_rv_runtime_baseline_commissioning_identity_f18d12d8 -->|Yes| g_rv_runtime_baseline_commissioning_storage_55ff245b
  g_rv_runtime_baseline_commissioning_storage_55ff245b -->|diagnostic_branch: No| g_rv_runtime_baseline_commissioning_blocked_f632b2f4
  g_rv_runtime_baseline_commissioning_storage_55ff245b -->|Yes| g_rv_runtime_baseline_commissioning_credential_check_4afa1b6b
  g_rv_runtime_baseline_commissioning_credential_check_4afa1b6b -->|diagnostic_branch: No| g_rv_runtime_baseline_commissioning_blocked_f632b2f4
  g_rv_runtime_baseline_commissioning_credential_check_4afa1b6b -->|Yes| g_rv_runtime_baseline_commissioning_database_af2ea5fc
  g_rv_runtime_baseline_commissioning_database_af2ea5fc --> g_rv_runtime_baseline_commissioning_schema_4b3917f9
  g_rv_runtime_baseline_commissioning_schema_4b3917f9 -->|diagnostic_branch: No| g_rv_runtime_baseline_commissioning_blocked_f632b2f4
  g_rv_runtime_baseline_commissioning_schema_4b3917f9 -->|Yes| g_rv_runtime_baseline_commissioning_ready_1e7806fe
  g_rv_runtime_baseline_commissioning_blocked_f632b2f4 -->|recovery_route| g_rv_runtime_baseline_commissioning_diagnose_3ea935df
  g_rv_runtime_baseline_commissioning_diagnose_3ea935df -->|recovery_route| g_rv_runtime_baseline_commissioning_systemd_94650c30
  g_rv_runtime_baseline_commissioning_ready_1e7806fe -->|verification| g_rv_runtime_baseline_commissioning_observe_de37d88a
  g_rv_runtime_baseline_commissioning_observe_de37d88a --> g_rv_runtime_baseline_commissioning_fresh_13eb70ab
  g_rv_runtime_baseline_commissioning_fresh_13eb70ab -->|diagnostic_branch: Expired/missing| g_rv_runtime_baseline_commissioning_stale_cf5d29be
  g_rv_runtime_baseline_commissioning_stale_cf5d29be -->|recovery_route| g_rv_runtime_baseline_commissioning_systemd_94650c30
  g_rv_runtime_baseline_commissioning_fresh_13eb70ab -->|verification: Fresh| g_rv_runtime_baseline_commissioning_accept_decision_b7391255
  g_rv_runtime_baseline_commissioning_accept_decision_b7391255 -->|escalation: No| g_rv_runtime_baseline_commissioning_accept_hold_47cf9721
  g_rv_runtime_baseline_commissioning_accept_decision_b7391255 -->|verification: Yes| g_rv_runtime_baseline_commissioning_acceptance_e02b3dea
  g_rv_runtime_baseline_commissioning_acceptance_e02b3dea -->|prerequisite| g_rv_runtime_baseline_commissioning_m12_jump_d59d1f04
  g_rv_runtime_baseline_commissioning_m12_jump_d59d1f04 -->|jump| g_rv_postgres_ledger_migration_apply_0f7d74d6
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

Package verification checks the exact archive digest, source commit, checksum
manifest, Linux shell compatibility, and safe archive members before host
installation. Camrui's owner-authorized administrator performs the local
deployment; no project privilege broker is installed.

Stable probe step IDs `identity`, `storage`, `credential`, `database`, `schema`,
`ready` are emitted in JSON on failure/success and map directly to the
[cookbook](RUNTIME_BASELINE_COOKBOOK.md). The database/schema subchecks are
read-only; no assignment events, recovery authority, worker or CME loops are
claimed here. Notifications are operator-visible exit codes/reports; automated
durable notification remains M3.2. The acceptance hold governs engineering
sequencing, not ongoing authorized institutional execution. PID 1's root-owned
read-only credential mount is validated separately from runtime-owned state,
then copied to a private ephemeral mode-0600 file because libpq rejects mode
0440. systemd cleans that runtime directory after the oneshot stops.

Restart means a new systemd diagnostic invocation and fresh credential delivery;
the latest report is replaced and immutable acceptance artifacts remain retained.

## Revision history

- 1.0.3: Add hash-pinned broker flow and corrected systemd credential ownership contract; predecessor `.riverview-backups/20261010T142904684465Z/docs/components/RUNTIME_BASELINE_FLOW.md`.
- 1.0.4: Add private runtime passfile copy required by libpq; predecessor is recorded under RV-M1.1-010 in `.riverview-backups/manifest.jsonl`.
- 1.0.5: Retire the broker flow and record the corrected PostgreSQL inet host check; predecessor recorded under RV-M1.1-011.

- 1.0.2: Add hidden-TTY credential capture and safe retained-release retry branches; predecessor under docs/history/RV-M1.1-007/rev1.0.1/docs/components/RUNTIME_BASELINE_FLOW.md.

- 1.0.1: Add actual archive-byte preflight and failed-package rebuild path; preserved predecessor under docs/history/RV-M1.1-002/rev1.0.0.
- 1.0.0: Initial flow with errors, repeat invocation, rollback and acceptance hold.
