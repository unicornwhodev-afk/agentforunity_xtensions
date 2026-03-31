---
description: "Run Unity tests and analyze results: execute EditMode/PlayMode tests, report failures, suggest fixes"
---
Run Unity tests and analyze results:

1. Call `run_tests` with testMode "EditMode"
2. If tests pass, also run "PlayMode" tests
3. For each failure, read the test script and the code under test
4. Suggest or apply fixes
5. Re-run tests to confirm all pass
