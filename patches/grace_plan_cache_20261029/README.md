# Grace lossless plan cache patch series

Apply 01 then 02, as a single reviewed change; 01 alone is not accepted. Runtime predecessors are the exact db-state-boundary-r1 files. Test predecessor is the retained Engineering test checkout (test_grace_execution1.0.92), not every GitHub/base checkout. The operator helper overlays only the two reviewed runtime files and does not apply test patches to the service release.

01 SHA256 b387316e81ccabc815664fda5912b09874181c4842dfadcfdda06ef54de08cdc
02 SHA256 ff41208cb3a0a19689121f4a898d62480aaf1a25f5661a88af37112c3bed92de

Expected final runtime: reasoning1.0.36 aa8fbd39c18d413ff814d89cb63cbdcbe8680b92bdc42d637f166e1f025cd56c; service1.0.66 73b5085d53645b1e9be20a12590e02071c0cc3fe75c51cbdf00dcf18045ad2be.

The remote full cumulative patch has SHA256 d18c8f3fb5d376ace3ab285a157d4c74cbcb1ed3871462d8156287247418ca56. Root retrieved and reviewed the equivalent original+incremental series, not that separately generated cumulative file. Helper bytes reconstructed from reviewed predecessor+diff and checked against remote full helper SHA25649de4332235f82fc60de302714a60216a9eb160212690f4c76dc1b2853163d65.

22focused tests passed,0skipped,0failed. No live PG integration or capacity acceptance yet. See GRACE_LOSSLESS_PLAN_CACHE_RUNBOOK.md.
