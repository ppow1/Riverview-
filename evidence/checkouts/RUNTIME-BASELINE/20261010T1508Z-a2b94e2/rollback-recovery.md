# RV-M1.1-011 rollback and recovery evidence

**Document Revision:** 1.0.0
**Task:** RV-M1.1-011
**Component:** RUNTIME-BASELINE
**Source commit:** a2b94e24715a670262859e1af31a0ea417ed37cb
**Host:** Camrui / Ubuntu 24.04.3 / admin1

The installer-created rollback directory `/var/backups/riverview-baseline.QIWAaHji`
was root-owned mode 0700. `previous.service` matched its recorded SHA-256. The
rollback script was run against this exact record and restored the recorded
`b40c77fdca48c556af9d25a8cd25e7ca192b9748` release symlink and previous unit.
Starting that predecessor reproduced its known `DATABASE_IDENTITY_MISMATCH`;
this expected failure is retained in `predecessor-start.log` and baseline JSON.

The exact verified a2b94e2 package was rerun from root-owned staging. Installation
passed and restored the active release to a2b94e2. The service returned systemd
`Result=success`, `ExecMainStatus=0`, ran as `riverview`, and emitted a current
`baseline_ready` report. The post-recovery acceptance collector then captured two
fresh distinct ready observations. No PostgreSQL objects or credential bytes
were modified. The recovery transaction leaves the corrected release active
and healthy.
