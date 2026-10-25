# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_capability_declaration_gate.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Verify website backend operations carry registry declarations or explicit exclusions
# Execution Model: Pure unit tests against added route-diff examples
# Authority: No database or production access
# =============================================================================
import unittest

from scripts.validate_capability_declaration_changes import validate_added_dispatches


class CapabilityDeclarationGateTests(unittest.TestCase):
    def test_added_api_operation_must_name_a_registered_operation(self):
        diff = '''diff --git a/server.py b/server.py
@@ -1,0 +2 @@
+                elif parsed.path == "/api/v1/new-operation":  # capability-operation: feature.read
'''
        self.assertEqual(validate_added_dispatches(
            diff, {"feature.read"}, 'NEW_ROUTE = "/api/v1/new-operation"'), [])
        errors = validate_added_dispatches(
            diff, set(), 'NEW_ROUTE = "/api/v1/new-operation"')
        self.assertIn("undeclared operation feature.read", errors[0])

    def test_unsupported_operation_requires_documented_exclusion_reason(self):
        diff = '''+                elif parsed.path == "/api/v1/session-only":  # capability-exclusion: Requires a Steward account session and has no compatible capability executor.
'''
        self.assertEqual(validate_added_dispatches(diff, set()), [])

    def test_missing_marker_or_short_exclusion_fails(self):
        missing = '+                elif parsed.path == "/api/v1/new-operation":\n'
        short = ('+                elif parsed.path == "/api/v1/new-operation":  '
                 '# capability-exclusion: no\n')
        self.assertIn("needs exactly one", validate_added_dispatches(missing, set())[0])
        self.assertIn("no meaningful exclusion", validate_added_dispatches(short, set())[0])

    def test_screen_route_is_not_an_executable_api_operation(self):
        diff = '+                elif parsed.path == "/v2/":\n'
        self.assertEqual(validate_added_dispatches(diff, set()), [])

    def test_dispatch_using_existing_api_path_constant_is_checked(self):
        diff = ('+                elif parsed.path == _NEW_API_ROUTE:  '
                '# capability-operation: feature.read\n')
        source = '_NEW_API_ROUTE = "/api/v1/new-operation"\n'
        self.assertEqual(validate_added_dispatches(diff, {"feature.read"}, source), [])


if __name__ == "__main__":
    unittest.main()
