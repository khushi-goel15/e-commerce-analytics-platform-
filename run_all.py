"""
E-COMMERCE ANALYTICS PLATFORM — Master Orchestrator

Runs the entire pipeline end-to-end:
  1. Generate synthetic dataset
  2. Run ETL pipeline
  3. Run Python analytics
  4. Export for Power BI
  5. Export for Tableau

Usage:
  python run_all.py          # full pipeline
  python run_all.py --step data   # only generate data
  python run_all.py --step etl    # only transform + load
  python run_all.py --step analytics  # only analytics/export
"""
import sys
import os
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(label, script_path, step_name):
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {label}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"  ERROR: {step_name} failed (exit code {result.returncode})")
        sys.exit(1)
    print(f"  Done.")


if __name__ == "__main__":
    step = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("--step="):
        step = sys.argv[1].split("=")[1]

    steps = {
        "data":      ("Generating synthetic data...",        "scripts/generate_data.py"),
        "etl":       ("Running ETL pipeline...",             "scripts/etl_pipeline.py"),
        "analytics": ("Running Python analytics...",         "analytics/python_analytics.py"),
        "powerbi":   ("Exporting Power BI datasets...",      "scripts/export_for_powerbi.py"),
        "tableau":   ("Exporting Tableau datasets...",       "scripts/export_for_tableau.py"),
    }

    order = ["data", "etl", "analytics", "powerbi", "tableau"]

    if step:
        if step in steps:
            run_script(steps[step][0], steps[step][1], step)
        else:
            print(f"Unknown step: {step}")
            print(f"Available: {', '.join(steps.keys())}")
            sys.exit(1)
    else:
        print("=" * 60)
        print("  E-COMMERCE ANALYTICS PLATFORM")
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        for s in order:
            run_script(steps[s][0], steps[s][1], s)
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE")
        print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
