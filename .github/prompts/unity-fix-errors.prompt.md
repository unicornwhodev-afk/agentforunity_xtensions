---
description: "Fix all Unity compilation errors: read console, find broken scripts, apply fixes"
---
Fix all Unity compilation errors:

1. Call `get_console_logs` to read current errors
2. For each error, read the relevant script file
3. Fix the issue following project C# conventions
4. Call `recompile_scripts` after all fixes
5. Check console again to confirm zero errors
