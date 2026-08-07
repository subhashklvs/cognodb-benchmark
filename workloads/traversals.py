"""
1-hop / 2-hop / 3-hop traversal latency workload.

Usage:
    python workloads/traversals.py --platform COGNODB

Picks a random set of start nodes (fixed seed for cross-platform
comparability), runs each hop-depth query READ_ITERATIONS times after
WARMUP_ITERATIONS warm-up runs, and reports p50/p95 per hop depth.
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

HOP_QUERIES = {
    1: "MATCH (a:Person {id: $id})-[:KNOWS]->(b) RETURN count(b) AS c",
    2: "MATCH (a:Person {id: $id})-[:KNOWS]->()-[:KNOWS]->(b) RETURN count(DISTINCT b) AS c",
    3: "MATCH (a:Person {id: $id})-[:KNOWS]->()-[:KNOWS]->()-[:KNOWS]->(b) RETURN count(DISTINCT b) AS c",
}


def get_sample_node_ids(driver, n=50, seed=7):
    rows = run_cypher(driver, "MATCH (p:Person) RETURN p.id AS id LIMIT 5000")
    all_ids = [r["id"] for r in rows]
    random.seed(seed)
    return random.sample(all_ids, min(n, len(all_ids)))


def run_hop_workload(driver, hop, node_ids, iterations, warmup):
    cypher = HOP_QUERIES[hop]

    for i in range(warmup):
        run_cypher(driver, cypher, {"id": node_ids[i % len(node_ids)]})

    latencies = []
    for i in range(iterations):
        node_id = node_ids[i % len(node_ids)]
        t0 = time.perf_counter()
        run_cypher(driver, cypher, {"id": node_id})
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

    results = {"platform": platform.display_name, "iterations": args.iterations,
               "warmup": args.warmup, "hops": {}}
    try:
        node_ids = get_sample_node_ids(driver)
        for hop in (1, 2, 3):
            print(f"[{platform.key}] running {hop}-hop workload ...")
            latencies = run_hop_workload(driver, hop, node_ids, args.iterations, args.warmup)
            results["hops"][str(hop)] = summarize(latencies)
    finally:
        driver.close()

    print(results)
    path = save_result(platform.key, "traversals", results, RESULTS_DIR)
    print(f"Saved -> {path}")
