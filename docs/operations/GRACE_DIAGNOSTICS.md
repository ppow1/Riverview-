# Grace intake diagnostics

Dashboard and Grace execution write bounded JSON diagnostics to the systemd journal.
Both units default to `RIVERVIEW_DIAGNOSTICS_MODE=NORMAL` (`INFO`). The optional
environment files are `/etc/riverview/dashboard-diagnostics.env` and
`/etc/riverview/grace-diagnostics.env`.

For a qualification window, set all of the following in the relevant file:

```ini
RIVERVIEW_DIAGNOSTICS_MODE=DEBUG
RIVERVIEW_DIAGNOSTICS_EXPIRES_AT=1792699200
RIVERVIEW_DIAGNOSTICS_OBJECTIVE_ID=objective:grace-conversation:example
```

`RIVERVIEW_DIAGNOSTICS_EXPIRES_AT` is a Unix timestamp, must be in the future, and
cannot be more than 24 hours ahead. Supply either an objective ID or a request ID
filter. DEBUG records without that correlation are dropped. When the expiry passes,
an expiry timer resets the root logger to INFO and the logging filter drops DEBUG
records. Remove the
temporary file or set the mode to `NORMAL` after qualification; the unit default stays
NORMAL on restart.

For intake failures, correlate Dashboard and PostgreSQL records with the request ID,
objective ID, SQLSTATE, and PostgreSQL backend PID. The application event contains
exception type and failure stage, but never exception text, conversation content,
prompts, credentials, cookies, or request bodies. PostgreSQL statement logging remains
at its existing error threshold.

Example journal queries:

```sh
journalctl -u riverview-status-dashboard.service --since '30 minutes ago'
journalctl -u riverview-grace-execution-owner-session.service --since '30 minutes ago'
```
