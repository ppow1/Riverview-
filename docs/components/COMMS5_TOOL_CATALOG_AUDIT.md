<!--
Riverview Controlled Document
File: docs/components/COMMS5_TOOL_CATALOG_AUDIT.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.0
Status: Historical contract inventory and migration audit
Date: 2026-10-17
History: New file; no predecessor existed.
-->

# Comms5 historical tool contract audit

Historical source: `ppow1/Riverview` Comms5 catalog captured from PR #15 head `048787f574d42ff073a9f94f571dc79943d60fa4`; immutable Camrui release catalog: [`tool_catalog.json`](../../src/riverview_core/comms5/tool_catalog.json). The companion [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md) records each current implementation status, authority classification, and remaining backend dependency.

**Schema evidence:** the captured catalog preserves each historical MCP `inputSchema`, description, annotations, and security metadata. It contains no formal MCP `outputSchema` for any tool. Where available, the historical operation description records its response semantics; the ordinary MCP tool result is therefore the only formally captured output envelope. This audit does not invent a stronger schema than the source provides.

## `comms5_contract_info`

**Original purpose/description:** Return the versioned Comms5 contract identity.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_contract_info` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_contract_infoArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_help`

**Original purpose/description:** Return machine-readable Comms5 discovery and safe-use guidance.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_help` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_helpArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_capabilities`

**Original purpose/description:** List Comms5 operations, limits, and authorization classes.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_capabilities` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_capabilitiesArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_describe_operation`

**Original purpose/description:** Describe one Comms5 operation.

**Original authorization classification:** `not separately recorded in describe payload`

**Historical response semantics:** No per-operation response description is present in the captured historical payload.

**Current status:** See the `comms5_describe_operation` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "operation": {
      "title": "Operation",
      "type": "string"
    }
  },
  "required": [
    "operation"
  ],
  "title": "comms5_describe_operationArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_examples`

**Original purpose/description:** Return bounded examples for public operations.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_examples` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_examplesArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_submit_steward_seed`

**Original purpose/description:** Submit a bounded draft; this never promotes or creates work.

**Original authorization classification:** `DRAFT_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_submit_steward_seed` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "authenticated_principal": {
      "title": "Authenticated Principal",
      "type": "string"
    },
    "causation_id": {
      "default": "",
      "title": "Causation Id",
      "type": "string"
    },
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "idempotency_key": {
      "title": "Idempotency Key",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "seed_text": {
      "title": "Seed Text",
      "type": "string"
    },
    "specification_id": {
      "default": "",
      "title": "Specification Id",
      "type": "string"
    }
  },
  "required": [
    "seed_text",
    "idempotency_key",
    "client_id",
    "client_type",
    "client_name",
    "authenticated_principal"
  ],
  "title": "comms5_submit_steward_seedArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_store_specification`

**Original purpose/description:** Store a bounded specification and optional typed non-shell formation contract.

**Original authorization classification:** `DRAFT_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_store_specification` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "$defs": {
    "FormationContractInput": {
      "additionalProperties": false,
      "description": "Bounded schema carrier; authority validation remains server-side.",
      "properties": {
        "acceptance_criteria": {
          "items": {
            "type": "string"
          },
          "title": "Acceptance Criteria",
          "type": "array"
        },
        "action_type": {
          "default": "",
          "title": "Action Type",
          "type": "string"
        },
        "allowed_paths": {
          "items": {
            "type": "string"
          },
          "title": "Allowed Paths",
          "type": "array"
        },
        "bounded_instruction": {
          "default": "",
          "title": "Bounded Instruction",
          "type": "string"
        },
        "capability_name": {
          "default": "",
          "title": "Capability Name",
          "type": "string"
        },
        "evidence_requirements": {
          "items": {
            "type": "string"
          },
          "title": "Evidence Requirements",
          "type": "array"
        },
        "expected_base_sha": {
          "default": "",
          "title": "Expected Base Sha",
          "type": "string"
        },
        "repository_identity": {
          "default": "",
          "title": "Repository Identity",
          "type": "string"
        },
        "repository_root": {
          "default": "",
          "title": "Repository Root",
          "type": "string"
        },
        "timeout_seconds": {
          "default": 0,
          "title": "Timeout Seconds",
          "type": "integer"
        },
        "write_policy": {
          "default": "",
          "title": "Write Policy",
          "type": "string"
        }
      },
      "title": "FormationContractInput",
      "type": "object"
    }
  },
  "properties": {
    "authenticated_principal": {
      "title": "Authenticated Principal",
      "type": "string"
    },
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "content": {
      "title": "Content",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "formation_contract": {
      "$ref": "#/$defs/FormationContractInput",
      "default": {
        "acceptance_criteria": [],
        "action_type": "",
        "allowed_paths": [],
        "bounded_instruction": "",
        "capability_name": "",
        "evidence_requirements": [],
        "expected_base_sha": "",
        "repository_identity": "",
        "repository_root": "",
        "timeout_seconds": 0,
        "write_policy": ""
      }
    },
    "idempotency_key": {
      "title": "Idempotency Key",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "summary": {
      "title": "Summary",
      "type": "string"
    }
  },
  "required": [
    "content",
    "summary",
    "idempotency_key",
    "client_id",
    "client_type",
    "client_name",
    "authenticated_principal"
  ],
  "title": "comms5_store_specificationArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_seed_status`

**Original purpose/description:** Return bounded seed, specification, objective linkage, and promotion status metadata.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_seed_status` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "seed_id": {
      "title": "Seed Id",
      "type": "string"
    }
  },
  "required": [
    "seed_id"
  ],
  "title": "comms5_seed_statusArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_seed_lineage`

**Original purpose/description:** Return authoritative bounded seed lineage.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_seed_lineage` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "seed_id": {
      "title": "Seed Id",
      "type": "string"
    }
  },
  "required": [
    "seed_id"
  ],
  "title": "comms5_seed_lineageArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_objective_status`

**Original purpose/description:** Return bounded objective, stages, authority, intent, and work metadata.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_objective_status` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "objective_id": {
      "title": "Objective Id",
      "type": "string"
    }
  },
  "required": [
    "objective_id"
  ],
  "title": "comms5_objective_statusArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_cme_status`

**Original purpose/description:** Return the authoritative CME runtime projection.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_cme_status` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_cme_statusArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_recent_steward_submissions`

**Original purpose/description:** Return bounded recent submission metadata.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_recent_steward_submissions` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "limit": {
      "default": 20,
      "title": "Limit",
      "type": "integer"
    }
  },
  "title": "comms5_recent_steward_submissionsArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_transport_probe`

**Original purpose/description:** Run one read-only end-to-end transport correlation probe.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_transport_probe` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "probe_id": {
      "title": "Probe Id",
      "type": "string"
    }
  },
  "required": [
    "probe_id"
  ],
  "title": "comms5_transport_probeArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_resource_policy_status`

**Original purpose/description:** Return the durable Codex resource policy and its audit projection.

**Original authorization classification:** `READ_ONLY`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_resource_policy_status` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {},
  "title": "comms5_resource_policy_statusArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": true
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_set_resource_policy`

**Original purpose/description:** Set policy only from authenticated Steward transport attestation.

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_set_resource_policy` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "$defs": {
    "ResourcePolicyParameters": {
      "additionalProperties": false,
      "description": "Closed schema for the existing resource-policy parameter contract.",
      "properties": {
        "consume_reset": {
          "default": false,
          "title": "Consume Reset",
          "type": "boolean"
        },
        "fallback": {
          "default": true,
          "title": "Fallback",
          "type": "boolean"
        },
        "priority_order": {
          "items": {
            "type": "string"
          },
          "title": "Priority Order",
          "type": "array"
        },
        "target_seat": {
          "default": "",
          "title": "Target Seat",
          "type": "string"
        }
      },
      "title": "ResourcePolicyParameters",
      "type": "object"
    }
  },
  "properties": {
    "expected_revision": {
      "default": -1,
      "title": "Expected Revision",
      "type": "integer"
    },
    "explicit_steward_confirmation": {
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "mode": {
      "title": "Mode",
      "type": "string"
    },
    "parameters": {
      "$ref": "#/$defs/ResourcePolicyParameters"
    },
    "rationale": {
      "default": "",
      "title": "Rationale",
      "type": "string"
    }
  },
  "required": [
    "mode",
    "parameters",
    "explicit_steward_confirmation"
  ],
  "title": "comms5_set_resource_policyArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_set_resource_policy_lock`

**Original purpose/description:** Lock or unlock policy only from authenticated Steward transport attestation.

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_set_resource_policy_lock` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "explicit_steward_confirmation": {
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "locked": {
      "title": "Locked",
      "type": "boolean"
    },
    "rationale": {
      "default": "",
      "title": "Rationale",
      "type": "string"
    }
  },
  "required": [
    "locked",
    "explicit_steward_confirmation"
  ],
  "title": "comms5_set_resource_policy_lockArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_confirm_and_promote_seed`

**Original purpose/description:** Record Pat's approval and atomically materialize one exact draft objective.

    This governed write verifies transport-attested Steward authority, explicit
    confirmation, the eligible specification ID/version/hash, and idempotency,
    then records bounded authority and creates the canonical objective record.
    It does not execute Codex or other work, run shell commands, cancel or
    supersede work, grant arbitrary authority, or bypass Grace, Relay,
    capability, or reconciliation gates. Client identity is provenance only.
    

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_confirm_and_promote_seed` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "explicit_steward_confirmation": {
      "description": "Pat's explicit approval of this exact draft; must be true.",
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "idempotency_key": {
      "description": "Stable retry key for this one approval transition.",
      "title": "Idempotency Key",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "seed_id": {
      "description": "Exact eligible specification-backed draft ID to approve.",
      "title": "Seed Id",
      "type": "string"
    }
  },
  "required": [
    "seed_id",
    "idempotency_key",
    "explicit_steward_confirmation",
    "client_id",
    "client_type",
    "client_name"
  ],
  "title": "comms5_confirm_and_promote_seedArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_form_and_queue_work`

**Original purpose/description:** Form the approved typed intent and enqueue exactly one work order.

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_form_and_queue_work` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "authority_id": {
      "description": "Exact active Steward authority grant ID bound to the objective and stage.",
      "title": "Authority Id",
      "type": "string"
    },
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "explicit_steward_confirmation": {
      "description": "Explicit Steward approval to form and enqueue this existing approved lineage; must be true.",
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "idempotency_key": {
      "description": "Stable retry key for this one formation and enqueue operation.",
      "title": "Idempotency Key",
      "type": "string"
    },
    "objective_id": {
      "description": "Exact already-promoted objective ID; scope is derived server-side.",
      "title": "Objective Id",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "stage_id": {
      "description": "Exact ready stage ID bound to the objective.",
      "title": "Stage Id",
      "type": "string"
    }
  },
  "required": [
    "objective_id",
    "stage_id",
    "authority_id",
    "idempotency_key",
    "explicit_steward_confirmation",
    "client_id",
    "client_type",
    "client_name"
  ],
  "title": "comms5_form_and_queue_workArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_revalidate_and_queue_work`

**Original purpose/description:** Revalidate one stale approved base and queue one bounded successor.

    This preserves the original failed attempt and exact authority scope. It
    never widens paths, changes the capability, or executes Codex; material
    repository drift fails closed for renewed specification approval.
    

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_revalidate_and_queue_work` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "description": "Calling client provenance; not an authority claim.",
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "explicit_steward_confirmation": {
      "description": "Pat's narrow confirmation of the verified new base binding; must be true.",
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "idempotency_key": {
      "description": "Stable retry key for this one base revalidation and successor attempt.",
      "title": "Idempotency Key",
      "type": "string"
    },
    "infrastructure_repair_evidence": {
      "default": [],
      "items": {
        "type": "string"
      },
      "title": "Infrastructure Repair Evidence",
      "type": "array"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "work_order_id": {
      "description": "Exact preserved failed work order with RIV-EXE-0008 stale-base evidence.",
      "title": "Work Order Id",
      "type": "string"
    }
  },
  "required": [
    "work_order_id",
    "idempotency_key",
    "explicit_steward_confirmation",
    "client_id",
    "client_type",
    "client_name"
  ],
  "title": "comms5_revalidate_and_queue_workArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_cancel_draft`

**Original purpose/description:** Append-only cancel of a draft; never cancels an objective or work order.

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_cancel_draft` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "authenticated_principal": {
      "title": "Authenticated Principal",
      "type": "string"
    },
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "explicit_steward_confirmation": {
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "idempotency_key": {
      "title": "Idempotency Key",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "reason": {
      "title": "Reason",
      "type": "string"
    },
    "seed_id": {
      "title": "Seed Id",
      "type": "string"
    }
  },
  "required": [
    "seed_id",
    "reason",
    "idempotency_key",
    "explicit_steward_confirmation",
    "client_id",
    "client_type",
    "client_name",
    "authenticated_principal"
  ],
  "title": "comms5_cancel_draftArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## `comms5_supersede_seed`

**Original purpose/description:** Append an old-draft-to-new-draft replacement relation.

**Original authorization classification:** `STEWARD-GATED_WRITE`

**Historical response semantics:** bounded JSON metadata; protected payloads are omitted

**Current status:** See the `comms5_supersede_seed` row in [`COMMS5_CAMRUI_MIGRATION.md`](COMMS5_CAMRUI_MIGRATION.md#comms5-camrui-migration-matrix).

**Original input schema:**

```json
{
  "properties": {
    "authenticated_principal": {
      "title": "Authenticated Principal",
      "type": "string"
    },
    "classification": {
      "default": "river",
      "title": "Classification",
      "type": "string"
    },
    "client_id": {
      "title": "Client Id",
      "type": "string"
    },
    "client_name": {
      "title": "Client Name",
      "type": "string"
    },
    "client_type": {
      "title": "Client Type",
      "type": "string"
    },
    "client_version": {
      "default": "",
      "title": "Client Version",
      "type": "string"
    },
    "correlation_id": {
      "default": "",
      "title": "Correlation Id",
      "type": "string"
    },
    "explicit_steward_confirmation": {
      "title": "Explicit Steward Confirmation",
      "type": "boolean"
    },
    "idempotency_key": {
      "title": "Idempotency Key",
      "type": "string"
    },
    "protocol_version": {
      "default": "riverview-comms-contract:5.0",
      "title": "Protocol Version",
      "type": "string"
    },
    "reason": {
      "title": "Reason",
      "type": "string"
    },
    "replacement_seed_id": {
      "title": "Replacement Seed Id",
      "type": "string"
    },
    "seed_id": {
      "title": "Seed Id",
      "type": "string"
    }
  },
  "required": [
    "seed_id",
    "replacement_seed_id",
    "reason",
    "idempotency_key",
    "explicit_steward_confirmation",
    "client_id",
    "client_type",
    "client_name",
    "authenticated_principal"
  ],
  "title": "comms5_supersede_seedArguments",
  "type": "object"
}
```

**Original annotations and authentication metadata:**

```json
{
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false,
    "readOnlyHint": false
  },
  "securitySchemes": [
    {
      "scopes": [
        "comms5"
      ],
      "type": "oauth2"
    }
  ]
}
```

## Migration disposition

- The 21 original tool names, descriptions, and input schemas remain discoverable in the Camrui adapter.
- The five static contract/discovery operations are implemented. The other 16 remain explicit MCP tool errors with `NOT_IMPLEMENTED` and `executed=false`; the current migration matrix names their absent/unequal Camrui dependencies.
- A contract being discoverable does not imply its historical backend is available. The adapter does not connect to legacy Windows tables or perform unverified writes.
- Any future operation implementation must preserve the original input schema and use current Riverview authorization and data interfaces. Unsupported or unauthorized calls must remain non-executing tool errors.
