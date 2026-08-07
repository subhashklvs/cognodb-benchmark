"""
Point lookup (by unique id, indexed via the constraint created at load
time) and a filtered/range lookup workload.

Usage:
    python workloads/lookups.py --platform COGNODB
"""
import argparse
import random
import sys
import time

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import PLATFORMS, READ_ITERATIONS, WARMUP_ITERATIONS, RESULTS_DIR
from harness.driver import get_driver, run_cypher
from harness.stats import summarize, save_result

POINT_LOOKUP = "MATCH (p:Person {id: $id}) RETURN p"
# id has a uniqueness constraint (created in loaders/load_data.py), so
# this is the "indexed lookup" case. Filtered/range lookup below scans a
# bucket of ids -- still index-assisted via the range predicate on id.
FILTERED_LOOKUP = "MATCH (p:Person) WHERE p.id >= $lo AND p.id < $hi RETURN count(p) AS c"


def get_id_range(driver):
    rows = run_cypher(driver, "MATCH (p:Person) RETURN min(p.id) AS lo, max(p.id) AS hi")
    return rows[0]["lo"], rows[0]["hi"]


def run_point_lookup(driver, ids, iterations, warmup):
    for i in range(warmup):
        run_cypher(driver, POINT_LOOKUP, {"id": ids[i % len(ids)]})
    latencies = []
    for i in range(iterations):
        t0 = time.perf_counter()
        run_cypher(driver, POINT_LOOKUP, {"id": ids[i % len(ids)]})
        latencies.append((time.perf_counter() - t0) * 1000.0)
    return latencies


def run_filtered_lookup(driver, lo, hi, iterations, warmup, bucket_width=1000):
    def rand_bucket():
        start = random.randint(lo, max(lo, hi - bucket_width))
        return start, start + bucket_width

    for _ in range(warmup):
        a, b = rand_bucket()
        run_cypher(driver, FILTERED_LOOKUP, {"lo": a, "hi": b})
    latencies = []
    for _ in range(iterations):
        a, b = rand_bucket()
        t0 = time.perf_counter()
        run_cypher(driver, FILTERED_LOOKUP, {"lo": a, "hi": b})
        latencies.append((time.perf_counter() - t0) * 1000.0)
    return latencies


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=[p.key for p in PLATFORMS])
    ap.add_argument("--iterations", type=int, default=READ_ITERATIONS)
    ap.add_argument("--warmup", type=int, default=WARMUP_ITERATIONS)
    args = ap.parse_args()

    platform = next(p for p in PLATFORMS if p.key == args.platform)
    driver = get_driver(platform)
    random.seed(11)

    try:
        lo, hi = get_id_range(driver)
        sample_ids = random.sample(range(lo, hi + 1), min(200, hi - lo + 1))

        print(f"[{platform.key}] running point lookup workload ...")
        point_latencies = run_point_lookup(driver, sample_ids, args.iterations, args.warmup)

        print(f"[{platform.key}] running filtered/range lookup workload ...")
        filtered_latencies = run_filtered_lookup(driver, lo, hi, args.iterations, args.warmup)
    finally:
        driver.close()

    results = {
        "platform": platform.display_name,
        "iterations": args.iterations,
        "warmup": args.warmup,
        "indexed_property": "Person.id (UNIQUE constraint)",
        "point_lookup": summarize(point_latencies),
        "filtered_lookup": summarize(filtered_latencies),
    }
    print(results)
    path = save_result(platform.key, "lookups", results, RESULTS_DIR)
    print(f"Saved -> {path}")
