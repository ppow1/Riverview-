# RV-M1.1-007 test harness correction

**Document Revision:** 1.0.0
**Task:** RV-M1.1-007

The first run of `test_password_prompt_reads_nonseekable_tty_without_echo` failed at its marker assertion. Captured PTY output ended in CRLF (`RV_PROMPT_MATCH\r\n`), while the assertion expected LF (`RV_PROMPT_MATCH\n`). The prompt had been displayed and no secret was present. The test now normalizes CRLF only for marker matching while checking the original output for the generated secret. Focused runtime tests subsequently passed (19 tests); the full suite on the committed tree passed (38 tests, 0 failures, 0 skips). This was a test harness line-ending mismatch, not a product defect.
