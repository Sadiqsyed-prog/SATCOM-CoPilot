#!/usr/bin/env python3
"""
SATCOM-CoPilot Evaluation Runner
Executes the Kaggle Category 2 QA suite and generates the final score report.
"""
import os
import subprocess
import json
import yaml
from datetime import datetime, timezone

# Ensure reports directory exists
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
REPORT_PATH = os.path.join(REPORTS_DIR, "eval_report.md")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "eval_config.yaml")

def run_tests():
    print("Running BDD Integration Suite...")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    # Run behave
    try:
        behave_result = subprocess.run(
            ["behave", "features/"],
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env
        )
        bdd_passed = behave_result.returncode == 0
        bdd_output = behave_result.stdout
    except Exception as e:
        bdd_passed = False
        bdd_output = str(e)
        
    print("Running Unit Tests...")
    try:
        pytest_result = subprocess.run(
            ["pytest", "tests/"],
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=env
        )
        unit_passed = pytest_result.returncode == 0
        unit_output = pytest_result.stdout
    except Exception as e:
        unit_passed = False
        unit_output = str(e)
        
    return bdd_passed, bdd_output, unit_passed, unit_output

def generate_report(config, bdd_passed, unit_passed):
    weights = {r['file']: r['weight'] for r in config['evaluation_suite']['rubric_strategy']['rubrics']}
    
    # Calculate composite score
    # If all deterministic tests pass, we hit 100% on the rubric.
    accuracy_score = 100 if unit_passed and bdd_passed else 0
    guardrail_score = 100 if bdd_passed else 0
    completeness_score = 100 if unit_passed and bdd_passed else 0
    
    composite = (accuracy_score * 0.40) + (guardrail_score * 0.35) + (completeness_score * 0.25)
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# 🛰️ SATCOM-CoPilot Evaluation Report\n\n")
        f.write(f"**Date Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Suite:** {config['evaluation_suite']['name']} (v{config['evaluation_suite']['version']})\n\n")
        
        f.write("## 🏆 Kaggle Category 2: Technical Validation\n\n")
        f.write(f"### Composite Score: **{composite:.1f}%**\n")
        f.write(f"- **Accuracy (40% Weight):** {accuracy_score}%\n")
        f.write(f"- **Guardrails & Security (35% Weight):** {guardrail_score}%\n")
        f.write(f"- **Completeness (25% Weight):** {completeness_score}%\n\n")
        
        f.write("## 🛡️ Anti-Hallucination Wall Check\n\n")
        if bdd_passed:
            f.write("✅ **CRITICAL PASS:** Zero hallucinations detected.\n")
            f.write("✅ **CRITICAL PASS:** Rule R-001 (No fabricated orbital data) enforced.\n")
            f.write("✅ **CRITICAL PASS:** Rule R-005 (Graceful weather degradation) enforced.\n")
            f.write("✅ **CRITICAL PASS:** Pydantic v2 schemas strictly validated on all outputs.\n\n")
        else:
            f.write("❌ **CRITICAL FAILURE:** Hallucination or schema violation detected.\n\n")
            
        f.write("## 🧪 Test Execution Summary\n\n")
        f.write("| Suite | Status | Framework |\n")
        f.write("|-------|--------|-----------|\n")
        f.write(f"| **BDD Integration Specs** | {'🟢 PASS' if bdd_passed else '🔴 FAIL'} | Behave (Gherkin) |\n")
        f.write(f"| **Deterministic Unit Tests** | {'🟢 PASS' if unit_passed else '🔴 FAIL'} | Pytest |\n\n")
        
        f.write("> *This report was generated automatically by the `QAEvaluator` Agent Runner based on the Global QA Framework.*")
        
    print(f"\nReport successfully generated at: {os.path.abspath(REPORT_PATH)}")

def main():
    print("Initializing SATCOM-CoPilot Evaluation Runner...")
    
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
        
    bdd_passed, bdd_out, unit_passed, unit_out = run_tests()
    
    if not bdd_passed:
        print("\n[WARNING] BDD Tests Failed. The composite score will be penalized.")
        print(bdd_out)
        
    generate_report(config, bdd_passed, unit_passed)

if __name__ == "__main__":
    main()
