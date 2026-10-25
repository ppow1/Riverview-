# Riverview~ RV-ENG-REV-004 metadata disposition

**Document Revision:** 1.0.0
**Task:** RV-ENG-REV-004-BASELINE-METADATA
**Date:** 2026-10-25 UTC
**Status:** Metadata-only baseline migration
**Source commit:** `21cbecec4e92981143991842e4a4fa9e6c47a443`

The controlled checkout found 19 files without recognized revisions. All 19 were byte-for-byte present in deployed source `07e0ab008796dc2dd75b12d84204261627c25fde`, and none changed between that source and the pre-migration PR head. No historical revision is claimed: text files start at 1.0.0; the three PNG assets are registered at 1.0.0 with exact size and SHA-256 in `.riverview-revisions.json`.

Exact predecessor bytes for all 19 targets, `.riverview-revisions.json`, and `.riverview-backups/manifest.jsonl` were preserved and verified. The append-only backup manifest records predecessor revision, SHA-256, backup path, and task. Binary assets were not modified; other file contents are unchanged apart from the added revision comment.

| Path | Predecessor SHA-256 | Backup |
| `deploy/systemd-user/riverview-chatgpt-doorbell-browser.service` | `a886f4d773eed0dba1150ef9fab5ceeef56186f896697a1f97a6aacc53bdc351` | `.riverview-backups/20261025T125101224835Z/deploy/systemd-user/riverview-chatgpt-doorbell-browser.service` |
| `docs/development/PROPOSAL_ORIGIN_REWORK_20261024.md` | `b2af9c58614d456c13c29b857adbb198ef2ae03f876e36be87b23c7ef80cb6f8` | `.riverview-backups/20261025T125101228396Z/docs/development/PROPOSAL_ORIGIN_REWORK_20261024.md` |
| `scripts/Invoke-RiverviewDoorbell.ps1` | `3f0a64ef3bed689a118ef7ed2173690506ad05b30c0f16593f210a8550ed961a` | `.riverview-backups/20261025T125101231078Z/scripts/Invoke-RiverviewDoorbell.ps1` |
| `src/riverview_core/institutional_authority/migrations/0010_grace_autonomy_experiment_grant.sql` | `cc40b9a1e77f15e6a0a2f11660c524737af24fb08ebd745ae9bfafd8264d4133` | `.riverview-backups/20261025T125101233182Z/src/riverview_core/institutional_authority/migrations/0010_grace_autonomy_experiment_grant.sql` |
| `src/riverview_core/institutional_authority/migrations/0011_exact_grace_luna_escalation_check.sql` | `a27f04574c336d947942a19c8949cb6db0243a958fb9d97e376dff1dfbb33fef` | `.riverview-backups/20261025T125101241032Z/src/riverview_core/institutional_authority/migrations/0011_exact_grace_luna_escalation_check.sql` |
| `src/riverview_core/institutional_authority/migrations/0012_grace_supervisory_authority.sql` | `cabe26852ba4ab7119bba1cc43b63d7bb5a5803e3974cafe2023c361df443ac1` | `.riverview-backups/20261025T125101254067Z/src/riverview_core/institutional_authority/migrations/0012_grace_supervisory_authority.sql` |
| `src/riverview_core/notifications/migrations/0008_grace_recovery_decisions.sql` | `f39bcd54a55f99b051af4a61a887b255e037013ac4da44fa19872a7b970d92ee` | `.riverview-backups/20261025T125101265683Z/src/riverview_core/notifications/migrations/0008_grace_recovery_decisions.sql` |
| `src/riverview_core/notifications/migrations/0009_notification_settings.sql` | `ec39314aef896987d91d2c4dc279bf958dcb0083a5c393d1c4f15d8b7a7c238f` | `.riverview-backups/20261025T125101268737Z/src/riverview_core/notifications/migrations/0009_notification_settings.sql` |
| `src/riverview_core/notifications/migrations/0010_notification_phone_delivery.sql` | `73c9d0e85bf670f7ff2a701acdd48506c56b193a3b374cf6ffe12107713dead1` | `.riverview-backups/20261025T125101271278Z/src/riverview_core/notifications/migrations/0010_notification_phone_delivery.sql` |
| `src/riverview_core/resident_execution/grace_experiment_authorization.py` | `bc42b0912de0ae5edaaa11e5fc56341b9f28b23021e798aeb83e29b95c1b6921` | `.riverview-backups/20261025T125101274274Z/src/riverview_core/resident_execution/grace_experiment_authorization.py` |
| `src/riverview_core/resident_execution/migrations/0019_grace_autonomy_experiment_authorization.sql` | `0c9aa74e3d9e55441dbeabf8e7ea8321ab303c097641d50f494f40aae2f9db5a` | `.riverview-backups/20261025T125101296316Z/src/riverview_core/resident_execution/migrations/0019_grace_autonomy_experiment_authorization.sql` |
| `src/riverview_core/resident_execution/migrations/0021_grace_experiment_authorization_amendment.sql` | `fdf8d8b3f992944fd55ab9e20c58e7a924c8b1cf3fac8090762610c8685e7ddc` | `.riverview-backups/20261025T125101299123Z/src/riverview_core/resident_execution/migrations/0021_grace_experiment_authorization_amendment.sql` |
| `src/riverview_core/resident_execution/migrations/0022_grace_supervisory_luna_budget.sql` | `3b38664b21ebb1c87a599db81ccce31ffa2f600bc02d0d4148412832846a49b4` | `.riverview-backups/20261025T125101301737Z/src/riverview_core/resident_execution/migrations/0022_grace_supervisory_luna_budget.sql` |
| `tests/test_direct_luna_budget.py` | `442ff9cb1752e617c24928ce1db07691a13f499531dea4d0b2041d1bcda3e56c` | `.riverview-backups/20261025T125101304130Z/tests/test_direct_luna_budget.py` |
| `website/v2/deployed/assets/notification-settings.css` | `57bf75eff2b70b2454e3163582bb7182162cfb30d75357dafd7b74182304ed5d` | `.riverview-backups/20261025T125101307384Z/website/v2/deployed/assets/notification-settings.css` |
| `website/v2/deployed/assets/notification-settings.js` | `0b4e30971dfd41d2a051ff40c7a980b7831d9c4b4b4c5e391f2deaca58e53c93` | `.riverview-backups/20261025T125101309869Z/website/v2/deployed/assets/notification-settings.js` |
| `website/v2/deployed/assets/octominer/controller-feature-reference.png` | `1bb72f98c40228ef9ccaa35133e16adeac6e5c639da3ab82f54b35a2882177dc` | `.riverview-backups/20261025T125101315267Z/website/v2/deployed/assets/octominer/controller-feature-reference.png` |
| `website/v2/deployed/assets/octominer/smart-watchdog-fan-controller-reference.png` | `d8e243a5fae87fd7d969033dc6b00476d3b5c5892852ac42b552441dac535299` | `.riverview-backups/20261025T125101336337Z/website/v2/deployed/assets/octominer/smart-watchdog-fan-controller-reference.png` |
| `website/v2/deployed/assets/octominer/x12ultra-front-open-chassis-reference.png` | `66ccabf2b0300fa386c667870c43325b3a4eb4b7d27e9e4739681ce1dc029268` | `.riverview-backups/20261025T125101359742Z/website/v2/deployed/assets/octominer/x12ultra-front-open-chassis-reference.png` |
| `.riverview-revisions.json` | `26de56bae723297bd0575cc788e8592bf183dc49b171fe66dd4c906cb7762ef0` | `.riverview-backups/20261025T125101389935Z/.riverview-revisions.json` |
| `.riverview-backups/manifest.jsonl` | `f0668c0d8f3c2b696cc528d56c2f58c6305e3ea5f3a128615d8f51289a13da4d` | `.riverview-backups/RV-ENG-REV-004-BASELINE-METADATA/.riverview-backups/manifest.jsonl` |
