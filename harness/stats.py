"""Latency stats helpers -- p50/p95/p99 + basic throughput math."""
import json
import os
import time
from contextlib import contextmanager

import numpy as np


@contextmanager
def timer():
    """Context manager yielding elapsed wall-clock ms after the block exits."""
    t0 = time.perf_counter()
    result = {}
    yield result
    result["ms"] = (time.perf_counter() - t0) * 1000.0


def percentiles(latencies_ms, pcts=(50, 95, 99)):
    if not latencies_ms:
        return {f"p{p}": None for p in pcts}
    arr = np.array(latencies_ms)
    return {f"p{p}": round(float(np.percentile(arr, p)), 3) for p in pcts}


def summarize(latencies_ms):
    if not latencies_ms:
        return {"n": 0, "p50": None, "p95": None, "p99": None, "mean": None, "min": None, "max": None}
    arr = np.array(latencies_ms)
    out = {"n": len(arr), "mean": round(float(arr.mean()), 3),
           "min": round(float(arr.min()), 3), "max": round(float(arr.max()), 3)}
    out.update(percentiles(latencies_ms))
    return out


def save_result(platform_key, workload_name, payload, results_dir="./results"):
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"{platform_key}__{workload_name}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def load_all_results(results_dir="./results"):
    """Load every benchmark result file into {platform: {workload: payload}}."""
    out = {}

    if not os.path.isdir(results_dir):
        return out

    for fname in sorted(os.listdir(results_dir)):
        # Only process benchmark JSON files
        if not fname.endswith(".json"):
            continue

        # Skip files like combined.json
        if "__" not in fname:
            continue

        platform_key, workload_name = fname[:-5].split("__", 1)

        with open(os.path.join(results_dir, fname), "r") as f:
            out.setdefault(platform_key, {})[workload_name] = json.load(f)

    return out
