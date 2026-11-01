# Deploy-R3 — help

Revision: 1.0.0

Deploys R3 website to Camrui; may restart the service. **Do not run for a smoke test.**

## Syntax

`Run.bat Deploy-R3 <commit-sha>`

## Example (illustrative; triggers deployment)

`Run.bat Deploy-R3 c8420b88803cd5b725d4dba5d633352690c5d5ec`

## Parameters

`commit-sha`: required, 7–40 hexadecimal characters. Passed as PowerShell `-Commit`.

## Discovery

`Run.bat list` and `Run.bat help Deploy-R3` are non-deploying operations.

## Source and status

Source: `A:\AI\Temp\tmp\Deploy-R3.ps1` version 1.0.3. Target: `A:\AI\Scripts\Riverview\Deploy-R3.ps1`. Installation not yet verified. Exit code from batch wrapper should propagate the PowerShell exit code.
