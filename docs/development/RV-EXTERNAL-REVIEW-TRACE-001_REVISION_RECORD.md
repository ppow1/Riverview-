<!--
Riverview~ Controlled Document
File: docs/development/RV-EXTERNAL-REVIEW-TRACE-001_REVISION_RECORD.md
Component: EXTERNAL-REVIEW-OBSERVABILITY
File Revision: 1.0.0
Purpose: Record W1 integration alignment with published C3 exact-review events
Authority: Read-only metadata projection; no runtime or provider authorization
Changed: 2026-10-18 UTC | RV-P0-W1-INTEGRATION-EVIDENCE | Initial integration revision record
Tests: tests/test_external_review_trace.py
History: Git and .riverview-backups/manifest.jsonl
-->

# External review trace integration revision record

## Change

W1 aligns the trace projector with C3's published source at
`5c4a00512e5acd6f72aa766ea866a8828184b151` and the shared event contract in
issue #120 comment 6254500089. Grace reviewed/blocked events must match the
current request, correlation, subject ID, revision, and digest. A revised
event's subject fields describe its successor; `proposal_sha256` remains a
separate content digest. The next trace round must match both successor request
IDs and the successor subject version/digest. Grace events must be emitted by
an `office:` actor. C2 receipt attribution remains an exact comparison against
the injected worker `owner_id`.

## Predecessors

Three prior files were preserved before this revision from source commit
`a5343630ab6b5c292691daea7c3b72a53297d950` under
`.riverview-backups/20261018T201346199444Z/`; the append-only backup manifest
records their prior `1.0.0` revision, SHA-256, source commit, and restoration
instruction. Each backup is verified by digest:

- `docs/components/EXTERNAL_REVIEW_TRACE.md` —
  `64f8a7b3d81901c235a1c841d91eec92968a1dee1a97182f93dd5d3d873cee4b`
- `src/riverview_core/resident_execution/external_review_trace.py` —
  `d061e1cf73874d74cbf674b9ceceef46fee365889564eb3514926d4fcc77f108`
- `tests/test_external_review_trace.py` —
  `12f09df3f48d56bfc9ca0f20a300e5023685b7e248ec2633669318d05e321eaf`

The shared generated revision index and process graphs were not regenerated;
W3 owns the final integration projection after the component branches are
assembled.

## Verification

`PYTHONPATH=src python -m unittest discover -s tests -p
test_external_review_trace.py` — 22 tests passed. Python compilation and
`git diff --check` passed. The exact W3 integration run is pending publication;
these tests are focused W1 projection tests and are not presented as end-to-end
acceptance.

## Limits

The report consumes an explicitly supplied, bounded snapshot. No source adapter,
database client, live owner ID, browser wake, or ChatGPT request is included.
Do not claim live readiness from this component evidence.
