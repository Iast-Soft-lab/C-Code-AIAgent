import json

from backend.clang_analyzer import run_clang_analysis


result = run_clang_analysis(
    "/home/rakesh/misra-agent-phase1/analysis_demo.c"
)

print(json.dumps(result, indent=4))
