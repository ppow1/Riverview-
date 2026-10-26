-- Revision: 1.0.0
-- Purpose: Register the existing owner-scoped resident conversation workspace operation.
-- Authority: Metadata only. This migration creates no resident grants or profiles.
INSERT INTO capability_catalog
    (capability_id,description,authority_action,owner_office,implementation_ref,dependencies,approval_default)
VALUES
    ('resident.conversation.send',
     'Send resident conversation messages, including bounded image attachments routed only to an authorized vision-capable model; manage conversations through the same Steward-scoped send authority.',
     'resident.conversation.send',
     'office:grace',
     'resident-conversation.api.v2',
     '["resident-conversation-ledger","exact-owner-check","vision-provider-allowlist"]'::jsonb,
     false);

INSERT INTO capability_resources(capability_id,resource_id,implementation_ref)
VALUES ('resident.conversation.send','office:office:grace','resident-conversation.api.v2');

INSERT INTO capability_catalog
    (capability_id,description,authority_action,owner_office,implementation_ref,dependencies,approval_default)
VALUES
    ('resident.conversation.read',
     'Read, search, switch, and retrieve owner-scoped resident conversation history and authorized image attachments.',
     'resident.conversation.read',
     'office:grace',
     'resident-conversation.api.v2',
     '["resident-conversation-ledger","exact-owner-check","protected-attachment-route"]'::jsonb,
     false);

INSERT INTO capability_resources(capability_id,resource_id,implementation_ref)
VALUES ('resident.conversation.read','office:office:grace','resident-conversation.api.v2');
