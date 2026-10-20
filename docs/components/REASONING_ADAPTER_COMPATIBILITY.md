<!--
Riverview~ Controlled Document
File: docs/components/REASONING_ADAPTER_COMPATIBILITY.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Describe assignment-defined artifact sets instead of a generated fixed filename
Purpose: Record verified response-format boundaries across reasoning transports
Authority: Provider output is data; only institutional contracts authorize actions
Execution Model: Fixture-backed source and test compatibility audit
Observability: Sanitized classifications and test outcomes; no private prompt bodies
Dependencies: LocalReasoningProvider; CodexCLIAdapter; external reasoning MCP exchange
Changed: 2026-10-18 UTC | RV-REASONING-ADAPTER-COMPAT-001 | Preserve provider-specific response semantics in the integrated reasoning path
Contracts: docs/components/RESIDENT_REASONING.md; docs/components/EXTERNAL_REASONING_EXCHANGE.md
Tests: tests/test_local_reasoning_provider.py; tests/test_codex_cli_adapter.py; tests/test_external_reasoning_mcp.py
History: Git; source-file predecessor backups are recorded in .riverview-backups/manifest.jsonl
-->
# Reasoning adapter compatibility matrix

## Scope and findings

This audit distinguishes transport parsing, provider protocol validation,
response normalization, and institutional authorization. It used source
inspection and synthetic disposable fixtures; it made no live model or external
reasoning request.

The narrow format behavior is **not systemic in one shared parser**. Codex CLI,
external reasoning, and local inference have separate protocols. Local
conversation parsing had one proven lossy case: tool-call fields were ignored
when a response also contained text, allowing the text to appear complete. It
also rejected text-only content-block arrays instead of preserving their text.
The local adapter now normalizes ordered text blocks and classifies tool calls
as unsupported. No tool is executed. The separate Codex artifact schema and
the external MCP advisory schema remain intentionally narrow contracts.

## Compatibility matrix

Legend: **Accepted** means validated by the inspected implementation and
synthetic tests; **Rejected** means safely fails closed; **Not parsed** means
that provider format is outside the adapter's input protocol.

The local conversation adapter accepts exactly one completed choice. It rejects
multiple choices instead of selecting the first and silently dropping the
others. In streaming mode, each nonempty choice frame must likewise contain
exactly one choice.

| Response form | Codex CLI execution adapter | External reasoning MCP exchange | Local OpenAI-compatible proposal | Local OpenAI-compatible conversation |
|---|---|---|---|---|
| Plain text | Not parsed as general output; deliverable file is separately checked | Accepted only as nonempty `advisory` string in the exact correlated submission envelope | Rejected; proposal must be exact JSON schema encoded in message content | Accepted as nonempty `message.content` string |
| Structured JSON | Strict task-result JSON schema in `--output-last-message`; authored artifact separately verified | Unknown fields/envelopes rejected; exact IDs, provider, schema version and advisory required | JSON content parsed as strict typed proposal; unknown plan keys rejected | Text-block contents may contain JSON characters as ordinary text; not separately parsed |
| Multiple content blocks | Not applicable; stdout is discarded, artifact/result files used | Not accepted as inbound ChatGPT output; MCP tool arguments contain contract fields | Not applicable to structured proposal content | Ordered `type=text` blocks joined; any non-text block rejected |
| Tool-call / tool-result messages | No tool-call envelope parsed; CLI action is separately sandboxed and artifact constrained | MCP tool calls are the transport operations; tool results are server-produced JSON text blocks, not model response normalization | Not accepted as proposal fields | Tool calls rejected even when text is present; tool results are not automatically executed or treated as content |
| Streaming / partial output | No event stream parsing; stdout/stderr are sent to DEVNULL and final/result files are checked | MCP JSON/SSE framing is handled by MCP transport, not arbitrary provider token streams | No streaming proposal parser | SSE `data:` JSON events parsed; text deltas are emitted, only complete `stop` returns success; truncation remains `response_incomplete` |
| Reasoning metadata | Not captured | Not accepted as advisory contract fields | Extra schema fields invalidate proposal | Provider `reasoning` / `reasoning_content` is not exposed as user-facing content; valid visible content remains accepted |
| Empty / incomplete | Missing or invalid result/artifact rejected; timeout/nonzero classified separately | Empty advisory rejected; pending/expired exchange remains typed state | Empty/malformed/incomplete proposal rejected (`None` / invalid proposal path) | Empty or incomplete output rejected; streamed partial text does not become completed turn |
| Provider errors / timeout | Nonzero process and timeout have sanitized execution errors | Exchange records bounded transport, claim, expiry and contract outcomes | Transport failures become sanitized unavailable; malformed output is not reinterpreted | HTTP/timeout/network errors have safe codes; invalid envelope is `response_contract_invalid`; non-stop finish is `response_incomplete` |
| Unexpected valid fields | Only strict final result schema accepted; extra keys invalid | Extra submission keys rejected by institutional contract | Extra proposal keys rejected | Unknown outer/message metadata is ignored if required fields remain valid; unknown content-block types are rejected |

## Evidence by boundary

### Codex CLI

`src/riverview_core/resident_execution/codex_cli.py` starts `codex exec` with a
strict JSON output schema and output-last-message file. It routes process
stdout/stderr to `DEVNULL`; it does not capture terminal text or parse Codex
event-stream records. It separately verifies that each contract-named output,
its declared media type, and the complete bounded changed-path set match the
persisted assignment, as well as process status. Tests in
`tests/test_codex_cli_adapter.py` cover schema/artifact validation, failure,
timeout, and workspace boundaries. This contract is task-specific; it is not a
general reasoning response parser.

### External reasoning

`src/riverview_core/resident_execution/external_reasoning.py` defines the
durable correlated exchange. The MCP server in
`external_reasoning_mcp.py` serializes its own result as a JSON text content
block. Submission validation accepts only the exact versioned advisory
envelope, matching provider and request/correlation identity. It does not
receive or parse arbitrary ChatGPT assistant-response envelopes. Authorization
is checked before exchange persistence and again on consumption; the returned
response remains unverified advice. Correlation, authorization, persistence,
restart-recovery, and idempotency are covered by
`tests/test_external_reasoning_exchange.py` under the isolated PostgreSQL
configuration, using synthetic provider fixtures and no live external request.

### Local inference

`LocalReasoningProvider.propose()` requires the strict `PlanProposal` schema in
`choices[0].message.content`; extra plan keys are rejected. Its conversational
`complete_chat()` and `stream_chat()` have a plain-text lifecycle contract.
Before this audit, non-streaming parsing read only `message.content` and
silently ignored adjacent `tool_calls` or `function_call`; the new tests prove
the mixed text-plus-tool-call case is rejected. Ordered text blocks are joined
without loss; unsupported image/audio/other blocks fail with the safe contract
error. Streamed tool calls and refusal deltas fail closed. Private reasoning
metadata is intentionally not returned to the conversation. Unknown metadata
outside response content is safely ignored.

Conversation persistence in `resident_execution/conversation.py` stores the
validated `ChatCompletion.content`; the stream lifecycle commits completion
only for a complete provider result. This audit adds provider-fixture coverage,
not a new persistence behavior or authorization path.

## Change and remaining verification

The correction is confined to local conversational normalization. The Codex
CLI adapter and MCP exchange contracts were not changed. Synthetic fixtures
cover text, text blocks, unknown metadata, tool calls, refusal, multimodal
content, reasoning metadata, streaming, and incomplete output. Tests do not
prove compatibility with every server implementation or future protocol
extension. Commissioning still requires authorized live verification for each
configured local provider and the external reasoning transport; no live request
was made for this audit.

Grace retains decision authority. No provider output, including external
advisory content, is executed or grants institutional permission.
