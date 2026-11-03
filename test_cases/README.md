# C Static Analysis Test Cases

These files are static-analysis test fixtures.
They are designed to exercise the analysis tools.
Do not execute the programs.

| File | Main test areas |
|---|---|
| demo_01_uninitialized.c | Uninitialized variables and undefined return values |
| demo_02_memory_safety.c | Array out-of-bounds and null pointer access |
| demo_03_arithmetic.c | Division and modulo by zero |
| demo_04_memory_management.c | Memory leak, use-after-free and double-free |
| demo_05_misra.c | Selected MISRA C:2012 rules and code quality |

Actual findings depend on the installed analyzer versions and enabled checks.
The test cases do not constitute a complete MISRA compliance test suite.
