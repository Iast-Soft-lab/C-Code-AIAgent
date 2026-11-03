
import json

from backend.cppcheck_analyzer import (
    run_cppcheck_analysis,
    run_misra_analysis
)

file_path = "/home/rakesh/misra-agent-phase1/analysis_demo.c"

report = {
    "cppcheck": run_cppcheck_analysis(file_path),
    "misra": run_misra_analysis(file_path)
}

print(json.dumps(report, indent=4))
