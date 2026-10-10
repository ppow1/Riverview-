# Riverview~ M1.1 systemd template verification

**Document Revision:** 1.0.0
**Task:** RV-M1.1-004
**Component:** RUNTIME-BASELINE
**Timestamp UTC:** 2026-10-10T03:54:16Z
**Source commit:** `b15b093642f65f6de36c1b977571ae2b79f04850`
**Host:** Camrui, Ubuntu 24.04.3; systemd 255

Command: `systemd-analyze verify deploy/systemd/riverview-baseline.service`

Exit code: 1

```text
riverview-baseline.service: Command /opt/riverview-core/.venv/bin/python is not executable: No such file or directory
```

Interpretation: the unit is not installed (`LoadState=not-found`) and its declared release path does not exist. systemd 255 exceeds the documented 250 minimum. This check does not establish runtime validity or a successful service start. No service or configuration was changed.
