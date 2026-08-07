"""
Single entry point: run the full benchmark suite (load -> traversals ->
lookups -> aggregations -> mixed workload) for one platform, or every
configured platform in sequence.

Usage:
    python harness/run_all.py --platform COGNODB
    python harness/run_all.py --all
"""
import argparse
import subprocess
import sys

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import PLATFORMS

STEPS = [
("workloads.traversals", []),
("workloads.lookups", []),
("workloads.aggregations", []),
("workloads.mixed_workload", []),
]


def run_platform(platform_key):
    platform = next(p for p in PLATFORMS if p.key == platform_key)
    if not platform.uri:
        print(f"SKIPPING {platform_key}: no URI configured in .env")
        return
    print(f"\n=== Running full suite for {platform.display_name} ({platform_key}) ===")
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for script, extra_args in STEPS:
        cmd = [sys.executable, "-m", script, "--platform", platform_key] + extra_args
        print(f"\n--- {' '.join(cmd)} ---")
        result = subprocess.run(cmd, cwd=root_dir)
        if result.returncode != 0:
            print(f"!! Step failed: {' '.join(cmd)} (exit {result.returncode}). "
                  f"Continuing with remaining steps and recording this as a caveat.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--platform", choices=[p.key for p in PLATFORMS])
    group.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        for p in PLATFORMS:
            run_platform(p.key)
    else:
        run_platform(args.platform)

    print("\nDone. Now run: python harness/build_report.py")
