# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_account_commissioning_tty.py
# Component: WEBSITE-ACCOUNT-AUTH
# Revision: 1.2.0
# Purpose: Verify secure local and SSH TTY gates for account commissioning
# Execution Model: Mocked unit tests; no database, filesystem credentials, or network access
# Observability: unittest assertions and exit status
# Dependencies: Python 3.10+; account-auth source dependencies
# Authority: None; no persistent or external state is changed
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SSH-COMMISSION | Cover TTY acceptance, denial and hidden-input fallback
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SMTP-PREFILL | Verify only confirmation and hidden password are prompted
# Changed: 2026-10-13 UTC | RV-ACCOUNT-AUTH-SMTP-PREFILL-TEST-FIX | Match the exact visible confirmation prompt
# Contracts: docs/components/ACCOUNT_AUTHENTICATION.md
# Tests: This file
# History: Git and revision/backup manifest
# =============================================================================
"""Non-network checks for the protected email and Steward bootstrap prompts."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import warnings
from unittest import TestCase, main
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


configure = load_script("configure_account_email_provider")
bootstrap = load_script("bootstrap_account_steward")


class FakeTTY:
    def __init__(self, interactive=True):
        self.interactive = interactive

    def isatty(self):
        return self.interactive

    def fileno(self):
        return 7


class CommissioningTTYTests(TestCase):
    def assert_ssh_tty_accepted(self, module, check):
        with patch.object(module.sys, "stdin", FakeTTY()), \
             patch.object(module.sys, "stdout", FakeTTY()), \
             patch.object(module.os, "ttyname", return_value="/dev/pts/5"), \
             patch.object(module.os, "geteuid", return_value=0), \
             patch.dict(module.os.environ, {"SSH_CONNECTION": "client server 12345 22"}, clear=False):
            self.assertTrue(check())

    def test_email_configurator_accepts_root_ssh_tty(self):
        self.assert_ssh_tty_accepted(configure, configure._local_console)

    def test_steward_bootstrap_accepts_root_ssh_tty(self):
        self.assert_ssh_tty_accepted(bootstrap, bootstrap._interactive_root_tty)

    def test_both_reject_missing_tty(self):
        for module, check in ((configure, configure._local_console),
                              (bootstrap, bootstrap._interactive_root_tty)):
            with self.subTest(module=module.__name__), \
                 patch.object(module.sys, "stdin", FakeTTY(interactive=False)), \
                 patch.object(module.sys, "stdout", FakeTTY()), \
                 patch.object(module.os, "ttyname", return_value="/dev/pts/5"), \
                 patch.object(module.os, "geteuid", return_value=0):
                self.assertFalse(check())

    def test_both_reject_non_root_terminal(self):
        for module, check in ((configure, configure._local_console),
                              (bootstrap, bootstrap._interactive_root_tty)):
            with self.subTest(module=module.__name__), \
                 patch.object(module.sys, "stdin", FakeTTY()), \
                 patch.object(module.sys, "stdout", FakeTTY()), \
                 patch.object(module.os, "ttyname", return_value="/dev/pts/5"), \
                 patch.object(module.os, "geteuid", return_value=1000):
                self.assertFalse(check())

    def test_hidden_input_fails_closed_on_getpass_echo_fallback(self):
        for module in (configure, bootstrap):
            def warn_if_echo_fallback(_prompt):
                warnings.warn("terminal echo cannot be disabled", module.getpass.GetPassWarning)

            with self.subTest(module=module.__name__), \
                 patch.object(module.getpass, "getpass", side_effect=warn_if_echo_fallback), \
                 self.assertRaises(module.getpass.GetPassWarning):
                module._hidden_input("secret prompt: ")

    def test_smtp_wizard_uses_approved_values_and_only_prompts_confirmation_and_password(self):
        secret = "synthetic-mailbox-password"
        output = io.StringIO()
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("0002_password_grants_and_email_provider",)
        with patch.object(configure, "_local_console", return_value=True), \
             patch("builtins.input", return_value="CONFIGURE RIVERVIEW EMAIL") as visible_input, \
             patch.object(configure, "_hidden_input", return_value=secret) as hidden_input, \
             patch.object(configure, "_key", return_value=b"test-key"), \
             patch.object(configure.ConfiguredEmailTransport, "encrypt_password", return_value=b"ciphertext"), \
             patch("psycopg.connect") as connect, redirect_stdout(output):
            connect.return_value.__enter__.return_value = connection
            result = configure.main()

        self.assertEqual(result, 0)
        visible_input.assert_called_once_with(
            "Type CONFIGURE RIVERVIEW EMAIL to save these settings: ")
        hidden_input.assert_called_once_with("SMTP mailbox password (input hidden): ")
        self.assertIn("SMTP host: smtp.stackmail.com", output.getvalue())
        self.assertIn("SMTP port: 465", output.getvalue())
        self.assertIn("TLS mode: implicit", output.getvalue())
        self.assertIn("Sender: Riverview <social@cuemastery.com>", output.getvalue())
        self.assertIn("Administrator inbox: social@cuemastery.com", output.getvalue())
        self.assertIn("Reply-to: social@cuemastery.com", output.getvalue())
        self.assertNotIn(secret, output.getvalue())
        params = cursor.execute.call_args_list[-1].args[1]
        self.assertEqual(params, (
            "smtp.stackmail.com", 465, "implicit", "social@cuemastery.com",
            "Riverview", "social@cuemastery.com", "social@cuemastery.com",
            "social@cuemastery.com", b"ciphertext",
        ))
        self.assertNotIn(secret, params)


if __name__ == "__main__":
    main()
