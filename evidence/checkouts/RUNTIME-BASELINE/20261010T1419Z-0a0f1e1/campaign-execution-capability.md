# RV-M1.1-008 Codex campaign execution capability check

**Document Revision:** 1.0.0  
**Task:** RV-M1.1-008  
**Component:** ENG-EXECUTION  
**Date:** 2026-10-10 UTC

## Local capability inspection

Camrui has `codex-cli 0.162.1`. Its help exposes bounded noninteractive `codex exec`, saved-session continuation through `codex exec resume [SESSION_ID]` / `--last`, interactive `codex resume`, and an `--ephemeral` opt-out from session-file persistence. `codex exec-server` exists, but is for connected executor sessions and requires configured remote session/auth details. This environment has no exposed weekly account-usage measurement tool. The available goal API (if a goal is used) measures that goal's local token budget, not the account's weekly allowance.

## Engineering conclusion

A single `codex exec` can run a bounded task. Saved sessions can be resumed, and a local terminal supervisor can keep a process alive over SSH disconnection. Neither fact establishes an autonomous, quota-aware campaign supervisor. OpenAI's official Codex guidance distinguishes bounded `codex exec` for scripts/CI from the Codex SDK for programmatic start/resume/stream, and app-server for persistent conversations, streaming and approval handling ([Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform)).

No campaign daemon or restart loop was installed: the current API-driven Codex session is not this local CLI process, no weekly quota signal is available to enforce the requested 50% stop, and an auto-restarting recursive agent could consume usage without a valid stop signal. Repository journal, branch, commits and checkout evidence provide durable project checkpoints; they do not claim to keep this current session executing after the API turn ends. Reassess a supervised runner only when the quota signal and authorized invocation/authentication path are available.
