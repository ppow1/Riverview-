# Grace artifact formation patch series

Apply 01 then 02 as one reviewed change. 01 alone is not accepted. Runtime predecessor is local_reasoning_provider1.3.32 SHA2569c78392cad50ea20adafa467a44533fbd1efe44160518010164ec19a9137a0b2 from exact lossless-cache-r2 release; final provider1.3.34 SHA2561811b1fc57c050e12817f703c9393a8b7b2b8484fdef12fa183bd33a52c4b440. Test predecessor is retained Engineering test_local_reasoning_provider1.1.38/c83d1b4fc3fc275833923ba3a4ff60d22d5bc0fc5713719bb6384e355a1c2daf, not every GitHub/current release test file. Operator helper overlays provider only, not tests.

01SHA2565ddd52e615961afa6d1a076c801c4889298d9852257aad70ada9df19fc34794e
02SHA256076ed37eec747cd25d3f9c7d855fa04ef2f2d66af230c7b99659dda9f036d09a
Helper1.0.1SHA2565fb725a600b3966356185f482a92d9901719384527cdd3ebaaf5ae725a715ba7, reconstructed from prior reviewed helper+two reviewed diffs and matched against remote hash.

Final focused6passed; fullproviderclass55passed/60, same5diagnosticassertionfailures as predecessor50passed/55. Do not claim whole suite passed or count focused subset additionally. No live inference yet. Raw report's patch_sha256 is historical01, not cumulative corrected patch. Use this ordered series and final runtime hash. Its claim of quoted bare extensionless support is overstated: actual filter still requires dot or slash and alphanumeric initial components. Root review/runbook records this recognition limit; final controller guard remains authoritative and unchanged.

See docs/operations/GRACE_ARTIFACT_FORMATION_RUNBOOK.md for exact operator command, rollback, tests and acceptance.
