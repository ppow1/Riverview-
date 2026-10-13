# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_stackmail_tty_security.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.1.0
# Purpose: Verify secure interactive Stackmail test behavior without network access
# Execution Model: Mocked local unit tests; no provider, database, or service use
# Observability: unittest assertions and exit status; test credentials are synthetic
# Dependencies: Python 3.10+
# Authority: None; all network transports are mocked
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SSH-TTY | Cover SSH TTY, refusal and redacted failures
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SSH-COMMISSION | Avoid discovery name collision with standalone script
# Contracts: docs/components/ACCOUNT_AUTHENTICATION_COOKBOOK.md
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""Non-network tests for the isolated Stackmail mailbox tester."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import smtplib
import sys
from unittest import TestCase, main
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "test_stackmail_mailbox.py"
SPEC = importlib.util.spec_from_file_location("stackmail_mailbox_tested", SCRIPT)
mailbox_tester = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mailbox_tester)


class TTY:
    def isatty(self):
        return True


class NonTTY:
    def isatty(self):
        return False


class StackmailTesterTests(TestCase):
    def test_allocated_ssh_tty_is_accepted(self):
        with patch.object(mailbox_tester.sys, "stdin", TTY()), \
             patch.object(mailbox_tester.sys, "stdout", TTY()), \
             patch.dict(os.environ, {
                 "SSH_CONNECTION": "client server 12345 22",
                 "SSH_CLIENT": "client 12345 22",
                 "SSH_TTY": "/dev/pts/4",
             }, clear=False):
            self.assertTrue(mailbox_tester._local_tty())

    def test_missing_tty_is_rejected(self):
        with patch.object(mailbox_tester.sys, "stdin", NonTTY()), \
             patch.object(mailbox_tester.sys, "stdout", TTY()):
            self.assertFalse(mailbox_tester._local_tty())
        with patch.object(mailbox_tester.sys, "stdin", TTY()), \
             patch.object(mailbox_tester.sys, "stdout", NonTTY()):
            self.assertFalse(mailbox_tester._local_tty())

    def test_auth_failure_redacts_password_and_server_text(self):
        secret = "synthetic-password-must-never-appear"
        server_text = f"535 invalid credentials: {secret}"
        output = io.StringIO()
        with patch.object(mailbox_tester, "_local_tty", return_value=True), \
             patch("builtins.input", side_effect=["SEND ONE STACKMAIL TEST EMAIL", "social@example.test"]), \
             patch.object(mailbox_tester.getpass, "getpass", return_value=secret), \
             patch.object(mailbox_tester.smtplib, "SMTP_SSL",
                          side_effect=smtplib.SMTPAuthenticationError(535, server_text.encode())), \
             redirect_stdout(output):
            result = mailbox_tester.main()
        self.assertEqual(result, 1)
        self.assertIn("SMTP authentication: FAILED (server reply 535)", output.getvalue())
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn(server_text, output.getvalue())

    def test_connection_failure_redacts_exception_message(self):
        secret = "synthetic-password-must-never-appear"
        output = io.StringIO()
        error = OSError(f"connection failed with {secret}")
        with patch.object(mailbox_tester, "_local_tty", return_value=True), \
             patch("builtins.input", side_effect=["SEND ONE STACKMAIL TEST EMAIL", "social@example.test"]), \
             patch.object(mailbox_tester.getpass, "getpass", return_value=secret), \
             patch.object(mailbox_tester.smtplib, "SMTP_SSL", side_effect=error), \
             redirect_stdout(output):
            result = mailbox_tester.main()
        self.assertEqual(result, 1)
        self.assertIn("FAILED (OSError)", output.getvalue())
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn(str(error), output.getvalue())

    def test_non_tty_refuses_before_prompting_for_password(self):
        output = io.StringIO()
        errors = io.StringIO()
        with patch.object(mailbox_tester, "_local_tty", return_value=False), \
             patch.object(mailbox_tester.getpass, "getpass") as get_password, \
             redirect_stdout(output), redirect_stderr(errors):
            result = mailbox_tester.main()
        self.assertEqual(result, 2)
        get_password.assert_not_called()
        self.assertIn("allocate a TTY", errors.getvalue())

    def test_confirmation_refusal_sends_nothing(self):
        with patch.object(mailbox_tester, "_local_tty", return_value=True), \
             patch("builtins.input", return_value="no"), \
             patch.object(mailbox_tester.getpass, "getpass") as get_password, \
             patch.object(mailbox_tester.smtplib, "SMTP_SSL") as smtp, \
             patch("builtins.print") as print_output:
            result = mailbox_tester.main()
        self.assertEqual(result, 2)
        get_password.assert_not_called()
        smtp.assert_not_called()
        print_output.assert_any_call("No test email sent.")


if __name__ == "__main__":
    main()
