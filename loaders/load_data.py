"""
Load data/dataset.csv into a target platform and measure ingest throughput.

Usage:
    python loaders/load_data.py --platform COGNODB
    python loaders/load_data.py --platform AURA --batch-size 2000

Loads with UNWIND-batched Cypher (the standard driver-batching approach --
document this choice in the README; a platform-specific bulk-import tool,
e.g. neo4j-admin import, would be faster but isn't apples-to-apples across
platforms, so batched driver writes keep the comparison fair).
"""
import argparse
import csv
import sys
import time

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import PLATFORMS, DATASET_PATH, RESULTS_DIR
from harness.driver import get_driver, run_cypher
from harness.stats import save_result

CONSTRAINT_CYPHER = "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE"

NODE_BATCH_CYPHER = """
UNWIND $ids AS id
MERGE (:Person {id: id})
"""

EDGE_BATCH_CYPHER = """
UNWIND $rows AS row
MATCH (a:Person {id: row.src})
MATCH (b:Person {id: row.dst})
MERGE (a)-[:KNOWS]->(b)
"""


def read_edges(path):
    edges = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            edges.append((int(row["src"]), int(row["dst"])))
    return edges


def load(platform, edges, batch_size, skip_index=False):
    driver = get_driver(platform)
    try:
        if not skip_index:
            run_cypher(driver, CONSTRAINT_CYPHER)

        node_ids = sorted({n for e in edges for n in e})

        t0 = time.perf_counter()
        for i in range(0, len(node_ids), batch_size):
            chunk = node_ids[i:i + batch_size]
            run_cypher(driver, NODE_BATCH_CYPHER, {"ids": chunk})
        node_time_s = time.perf_counter() - t0

        t1 = time.perf_counter()
        for i in range(0, len(edges), batch_size):
            chunk = [{"src": s, "dst": d} for s, d in edges[i:i + batch_size]]
            run_cypher(driver, EDGE_BATCH_CYPHER, {"rows": chunk})
        edge_time_s = time.perf_counter() - t1

        total_s = node_time_s + edge_time_s
        result = {
            "platform": platform.display_name,
            "node_count": len(node_ids),
            "edge_count": len(edges),
            "node_load_seconds": round(node_time_s, 3),
            "edge_load_seconds": round(edge_time_s, 3),
            "total_load_seconds": round(total_s, 3),
            "nodes_per_second": round(len(node_ids) / node_time_s, 2) if node_time_s > 0 else None,
            "relationships_per_second": round(len(edges) / edge_time_s, 2) if edge_time_s > 0 else None,
            "batch_size": batch_size,
        }
        return result
    finally:
        driver.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=[p.key for p in PLATFORMS])
    ap.add_argument("--dataset", default=DATASET_PATH)
    ap.add_argument("--batch-size", type=int, default=1000)
    args = ap.parse_args()

    platform = next(p for p in PLATFORMS if p.key == args.platform)
    if not platform.uri:
        raise SystemExit(f"No URI configured for {args.platform} -- check your .env")

    edges = read_edges(args.dataset)
    print(f"Loading {len(edges)} edges into {platform.display_name} ...")
    result = load(platform, edges, args.batch_size)
    print(result)
    path = save_result(platform.key, "load", result, RESULTS_DIR)
    print(f"Saved -> {path}")
