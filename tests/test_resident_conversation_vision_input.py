# Riverview~ Controlled Source
# File: tests/test_resident_conversation_vision_input.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.1
# Changed: 2026-10-26 UTC | RV-V2-CHAT-VISION-AUTHORITY-ORDER | Verify exact-grant declaration ordering and contracts.
# Purpose: Verify multimodal input, model routing, authorization declarations, and V2 controls
# Authority: Isolated tests only; no production identities or services are changed
"""Focused contracts for owner-chat multimodal routing and V2 input controls."""
from pathlib import Path
import json
import unittest

from riverview_core.local_reasoning_provider import LocalReasoningProvider, ProviderReadiness
from riverview_core.resident_execution.model_router import GraceModelRouter


class Provider:
    def __init__(self, model, ready="READY", vision=False):
        self.model=model; self.model_sha256="a"*64; self.state=ready
        self.supports_vision=vision; self.provider_id="test.provider"
    def readiness(self):
        return ProviderReadiness(self.state,self.model,"test")


class ConversationVisionInputTests(unittest.TestCase):
    def test_image_payload_is_constrained_to_one_text_and_bounded_image_data_urls(self):
        payload=[{"type":"text","text":"What is in this image?"},
            {"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgo="}}]
        self.assertTrue(LocalReasoningProvider._valid_multimodal_content(payload))
        self.assertFalse(LocalReasoningProvider._valid_multimodal_content([
            {"type":"text","text":"question"},
            {"type":"image_url","image_url":{"url":"https://example.invalid/image.png"}}]))
        self.assertFalse(LocalReasoningProvider._valid_multimodal_content([
            {"type":"text","text":"one"},{"type":"text","text":"two"},
            {"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgo="}}]))

    def test_image_turn_selects_vision_even_for_simple_prompt(self):
        router=GraceModelRouter(autonomic=Provider("small"),vision=Provider("vlm",vision=True),
            reasoning=Provider("large"))
        messages=[{"role":"system","content":"role"},{"role":"user","content":[
            {"type":"text","text":"What is in this image?"},
            {"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgo="}}]}]
        stage,provider=router.select(messages,image_required=True)
        self.assertEqual(stage,"vision")
        self.assertIs(provider,router.providers["vision"])

    def test_unavailable_vision_never_falls_back_to_text_provider(self):
        router=GraceModelRouter(autonomic=Provider("small"),vision=Provider("vlm","UNAVAILABLE",True),
            reasoning=Provider("large"))
        with self.assertRaises(Exception):
            router.select([{"role":"user","content":"describe"}],image_required=True)

    def test_v2_has_clip_drop_file_picker_and_authorized_history_attachment_route(self):
        base=Path(__file__).resolve().parents[1]
        html=(base/"website/v2/deployed/index.html").read_text()
        js=(base/"website/v2/deployed/assets/grace-chat.js").read_text()
        server=(base/"src/riverview_core/status_dashboard/server.py").read_text()
        self.assertIn('id="grace-image-picker"',html)
        self.assertIn('addEventListener("paste"',js)
        self.assertIn('addEventListener("drop"',js)
        self.assertIn('/attachments/',server)
        self.assertIn('completion_kwargs["image_required"]',
            (base/"src/riverview_core/resident_execution/conversation.py").read_text())

    def test_capability_declarations_describe_read_and_vision_send_without_grants(self):
        base=Path(__file__).resolve().parents[1]
        declarations=base/"src/riverview_core/institutional_authority/capability_declarations"
        read=json.loads((declarations/"resident_conversation_read.json").read_text())
        send=json.loads((declarations/"resident_conversation_send.json").read_text())
        self.assertEqual(read["authorization_contract"], {
            "mode":"exact_grant","action":"resident.conversation.read","scope_policy":"exact_scope"})
        self.assertEqual(send["authorization_contract"], {
            "mode":"exact_grant","action":"resident.conversation.send","scope_policy":"exact_scope"})
        self.assertIn("attachments",send["input_schema"]["properties"])
        migration=(base/"src/riverview_core/institutional_authority/migrations/0016_resident_conversation_workspace_capability.sql").read_text()
        self.assertNotIn("authority_grants",migration)
        self.assertIn("resident.conversation.read",migration)
        self.assertIn("resident.conversation.send",migration)
        self.assertIn("authorization_contract",migration)
        self.assertIn('"scope_policy":"exact_scope"',migration)

    def test_v2_settings_and_resident_entry_reach_chat_workspace(self):
        base=Path(__file__).resolve().parents[1]
        workspace=(base/"website/v2/deployed/assets/workspace.js").read_text()
        explorer=(base/"website/v2/deployed/assets/authority-explorer.js").read_text()
        html=(base/"website/v2/deployed/index.html").read_text()
        self.assertIn('getElementById("settings-workspace").hidden = !isSettings',workspace)
        self.assertIn('openGraceConversation',workspace)
        self.assertIn('openGraceConversation()',explorer)
        self.assertIn('rev=chat-navigation-settings-20261026',html)

    def test_conversation_switch_waits_for_inflight_history_before_reading_selection(self):
        base=Path(__file__).resolve().parents[1]
        chat=(base/"website/v2/deployed/assets/grace-chat.js").read_text()
        self.assertIn("async function openConversation(conversationId)",chat)
        self.assertIn("while (state.historyInFlight",chat)
        self.assertIn("await openConversation(item.conversation_id)",chat)


if __name__=="__main__":
    unittest.main()
