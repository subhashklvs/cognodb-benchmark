"""
Aggregation workload: count + group-by-style query over the relationship
type / label, per the assignment's "Aggregations" metric requirement.

Usage:
    python workloads/aggregations.py --platform COGNODB
"""
import argparse
import sys
import time

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import PLATFORMS, READ_ITERATIONS, WARMUP_ITERATIONS, RESULTS_DIR
from harness.driver import get_driver, run_cypher
from harness.stats import summarize, save_result

# Simple count aggregation.
COUNT_QUERY = "MATCH (:Person)-[r:KNOWS]->() RETURN count(r) AS c"

# Group-by-style aggregation: out-degree distribution bucketed, a
# reasonably heavy aggregation that exercises the query planner's
# grouping/sorting path rather than a trivial count.
GROUPBY_QUERY = """
MATCH (p:Person)-[:KNOWS]->()
WITH p, count(*) AS out_degree
RETURN out_degree, count(p) AS num_people
ORDER BY out_degree
"""


def run_workload(driver, cypher, iterations, warmup):
    for _ in range(warmup):
        run_cypher(driver, cypher)
    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        run_cypher(driver, cypher)
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

    try:
        print(f"[{platform.key}] running count aggregation ...")
        count_latencies = run_workload(driver, COUNT_QUERY, args.iterations, args.warmup)

        print(f"[{platform.key}] running group-by aggregation ...")
        groupby_latencies = run_workload(driver, GROUPBY_QUERY, args.iterations, args.warmup)
    finally:
        driver.close()

    results = {
        "platform": platform.display_name,
        "iterations": args.iterations,
        "warmup": args.warmup,
        "count_aggregation": summarize(count_latencies),
        "groupby_aggregation": summarize(groupby_latencies),
    }
    print(results)
    path = save_result(platform.key, "aggregations", results, RESULTS_DIR)
    print(f"Saved -> {path}")
