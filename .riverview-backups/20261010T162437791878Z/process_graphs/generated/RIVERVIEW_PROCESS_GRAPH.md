# Riverview aggregate process graph

**Document Revision:** 1.0.0  
**Generated from:** canonical workflow JSON; do not edit this projection by hand.  
**Source:** `python3 scripts/process_graph.py generate`  

The graph is complete across registered workflows. Use focused component flow documents for detailed reading. Unimplemented roadmap integration points are explicitly labeled planned.

```mermaid
flowchart LR
  subgraph g_rv_postgres_ledger_assignment_lifecycle["POSTGRES-LEDGER / assignment-lifecycle.v1"]
    n0(["Assignment intake<br/>rv:postgres-ledger:assignment-lifecycle:intake"])
    n1["queued<br/>rv:postgres-ledger:assignment-lifecycle:queued"]
    n2["ready<br/>rv:postgres-ledger:assignment-lifecycle:ready"]
    n3["running<br/>rv:postgres-ledger:assignment-lifecycle:running"]
    n4["awaiting_verification<br/>rv:postgres-ledger:assignment-lifecycle:awaiting-verification"]
    n5["rework_required<br/>rv:postgres-ledger:assignment-lifecycle:rework"]
    n6[["blocked<br/>rv:postgres-ledger:assignment-lifecycle:blocked"]]
    n7[["awaiting_steward<br/>rv:postgres-ledger:assignment-lifecycle:awaiting-steward"]]
    n8(["completed (caller verification flag is only a claim)<br/>rv:postgres-ledger:assignment-lifecycle:completed"])
    n9(["cancelled<br/>rv:postgres-ledger:assignment-lifecycle:cancelled"])
  end
  subgraph g_rv_postgres_ledger_migration["POSTGRES-LEDGER / postgres-migration.v1"]
    n10["Confirm live host, database, schema owner/access, empty target and compatibility<br/>rv:postgres-ledger:migration:preflight"]
    n11{"Preflight safe to proceed?<br/>rv:postgres-ledger:migration:preflight-clear"}
    n12[["Stop on identity, compatibility or safety mismatch<br/>rv:postgres-ledger:migration:stop"]]
    n13["Protected full database backup; checksum and restore drill<br/>rv:postgres-ledger:migration:backup"]
    n14["Recoverable backup independently restored and verified<br/>rv:postgres-ledger:migration:backup-verified"]
    n15(["Explicit migration request for selected schema<br/>rv:postgres-ledger:migration:apply"])
    n16{"Stored checksum matches source?<br/>rv:postgres-ledger:migration:check"}
    n17[["Checksum mismatch; stop without schema changes<br/>rv:postgres-ledger:migration:drift"]]
    n18["Identical applied migration is a no-op<br/>rv:postgres-ledger:migration:noop"]
    n19["Apply versioned SQL and checksum atomically<br/>rv:postgres-ledger:migration:sql"]
    n20["PostgresLedger requires migrated target schema<br/>rv:postgres-ledger:migration:require-schema"]
    n21["Caller requests assignment create or transition<br/>rv:postgres-ledger:migration:caller"]
    n22["Begin PostgreSQL transaction<br/>rv:postgres-ledger:migration:transaction"]
    n23["Advisory lock on idempotency key<br/>rv:postgres-ledger:migration:lock"]
    n24{"Existing event key?<br/>rv:postgres-ledger:migration:key-exists"}
    n25["Exact semantic replay returns current assignment<br/>rv:postgres-ledger:migration:replay"]
    n26[["Conflicting key reuse is rejected<br/>rv:postgres-ledger:migration:collision"]]
    n27{"Create or transition?<br/>rv:postgres-ledger:migration:operation"}
    n28["Insert assignment metadata<br/>rv:postgres-ledger:migration:create"]
    n29["Lock assignment row FOR UPDATE<br/>rv:postgres-ledger:migration:row-lock"]
    n30{"Legal state transition?<br/>rv:postgres-ledger:migration:legal"}
    n31[["Reject illegal transition<br/>rv:postgres-ledger:migration:illegal"]]
    n32["Update state and workflow step<br/>rv:postgres-ledger:migration:update"]
    n33["Append event with authority and causality<br/>rv:postgres-ledger:migration:event"]
    n34["Commit assignment and event atomically<br/>rv:postgres-ledger:migration:commit"]
    n35["Read assignment and ordered events<br/>rv:postgres-ledger:migration:read"]
    n36["On-demand status snapshot<br/>rv:postgres-ledger:migration:snapshot"]
    n37["M3.1 live dashboard (planned; not implemented)<br/>rv:postgres-ledger:migration:dashboard-jump"]
  end
  subgraph g_rv_runtime_baseline_commissioning["RUNTIME-BASELINE / runtime-baseline.v1"]
    n38(["Committed source revision<br/>rv:runtime-baseline:commissioning:source"])
    n39["Build and verify package<br/>rv:runtime-baseline:commissioning:package"]
    n40{"Archive digest, commit, manifest and safe members valid?<br/>rv:runtime-baseline:commissioning:package-valid"}
    n41[["Preserve failed package; rebuild corrected source<br/>rv:runtime-baseline:commissioning:package-failure"]]
    n42["Extract verified archive into protected staging<br/>rv:runtime-baseline:commissioning:stage"]
    n43["Preserve predecessor; run fixed installer<br/>rv:runtime-baseline:commissioning:install"]
    n44{"Protected credential source exists?<br/>rv:runtime-baseline:commissioning:credential-present"}
    n45(["Prompt on controlling TTY with echo disabled<br/>rv:runtime-baseline:commissioning:credential-entry"])
    n46[["Fail closed; passfile remains absent<br/>rv:runtime-baseline:commissioning:tty-failure"]]
    n47["Check partial ownership, retry corrected installer<br/>rv:runtime-baseline:commissioning:retry-install"]
    n48["systemd starts unprivileged probe with LoadCredential<br/>rv:runtime-baseline:commissioning:systemd"]
    n49["Validate source; copy to private mode-0600 runtime passfile<br/>rv:runtime-baseline:commissioning:credential-copy"]
    n50{"Correct non-login service identity?<br/>rv:runtime-baseline:commissioning:identity"}
    n51{"Private service-owned state directory?<br/>rv:runtime-baseline:commissioning:storage"}
    n52{"Safe credential file and no ambient override?<br/>rv:runtime-baseline:commissioning:credential-check"}
    n53["Read-only PostgreSQL identity and privilege check<br/>rv:runtime-baseline:commissioning:database"]
    n54{"riverview_dev owner and access match?<br/>rv:runtime-baseline:commissioning:schema"}
    n55[["Report accountable blocker and preserve diagnostics<br/>rv:runtime-baseline:commissioning:blocked"]]
    n56["Diagnose and repair using cookbook; retry probe<br/>rv:runtime-baseline:commissioning:diagnose"]
    n57(["Ready: baseline verified; wider institution not verified<br/>rv:runtime-baseline:commissioning:ready"])
    n58["Independent observer validates revision and timestamp<br/>rv:runtime-baseline:commissioning:observe"]
    n59{"Observation fresh and valid?<br/>rv:runtime-baseline:commissioning:fresh"}
    n60[["Stale, missing or invalid observation is not ready<br/>rv:runtime-baseline:commissioning:stale"]]
    n61{"Steward accepts scoped M1.1 evidence and sequencing?<br/>rv:runtime-baseline:commissioning:accept-decision"}
    n62[["Record acceptance hold; independent M1.2 engineering may continue<br/>rv:runtime-baseline:commissioning:accept-hold"]]
    n63["Record scoped M1.1 technical acceptance; full DoD remains open<br/>rv:runtime-baseline:commissioning:acceptance"]
    n64["M1.2 shared-schema migration workflow<br/>rv:runtime-baseline:commissioning:m12-jump"]
  end
  subgraph g_rv_steward_dashboard_status["STEWARD-DASHBOARD / status-projection.v1"]
    n65(["Reserved M3.1 live-state projection target (planned; not implemented)<br/>rv:steward-dashboard:status:ingest"])
  end
  n0 --> n1
  n1 --> n2
  n1 --> n6
  n1 --> n9
  n2 --> n3
  n2 --> n6
  n2 --> n9
  n3 --> n4
  n3 --> n6
  n3 --> n7
  n4 -->|verified claim required; not independent proof| n8
  n4 --> n5
  n4 --> n6
  n5 --> n2
  n5 --> n6
  n5 --> n9
  n6 --> n2
  n6 --> n9
  n6 --> n7
  n7 --> n2
  n7 --> n9
  n10 -->|verification| n11
  n11 -->|diagnostic_branch: No| n12
  n11 -->|Yes| n13
  n13 -->|verification| n14
  n14 --> n15
  n15 --> n16
  n16 -->|diagnostic_branch: Mismatch| n17
  n16 -->|Already applied, identical| n18
  n16 -->|New version| n19
  n18 --> n20
  n19 --> n20
  n20 -->|prerequisite: Verified schema contract; not a runtime call| n21
  n21 --> n22
  n22 --> n23
  n23 --> n24
  n24 -->|Exact replay| n25
  n24 -->|diagnostic_branch: Conflict| n26
  n24 -->|New key| n27
  n27 -->|Create| n28
  n27 -->|Transition| n29
  n29 --> n30
  n30 -->|diagnostic_branch: No| n31
  n30 -->|Yes| n32
  n28 --> n33
  n32 --> n33
  n33 --> n34
  n34 --> n35
  n25 --> n35
  n35 --> n36
  n36 --> n37
  n37 -->|jump| n65
  n38 --> n39
  n39 --> n40
  n40 -->|diagnostic_branch: No| n41
  n41 -->|recovery_route| n39
  n40 -->|Yes| n42
  n42 --> n43
  n43 --> n44
  n44 -->|No| n45
  n45 -->|diagnostic_branch: TTY failure| n46
  n46 -->|recovery_route| n47
  n47 -->|recovery_route| n42
  n44 -->|Yes| n48
  n45 -->|Captured| n48
  n48 --> n49
  n49 --> n50
  n50 -->|diagnostic_branch: No| n55
  n50 -->|Yes| n51
  n51 -->|diagnostic_branch: No| n55
  n51 -->|Yes| n52
  n52 -->|diagnostic_branch: No| n55
  n52 -->|Yes| n53
  n53 --> n54
  n54 -->|diagnostic_branch: No| n55
  n54 -->|Yes| n57
  n55 -->|recovery_route| n56
  n56 -->|recovery_route| n48
  n57 -->|verification| n58
  n58 --> n59
  n59 -->|diagnostic_branch: Expired/missing| n60
  n60 -->|recovery_route| n48
  n59 -->|verification: Fresh| n61
  n61 -->|escalation: No| n62
  n61 -->|verification: Yes| n63
  n63 -->|prerequisite| n64
  n64 -->|jump| n15
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
