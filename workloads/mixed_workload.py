"""
Mixed concurrent read/write workload -- sustained queries/second under a
stated client concurrency and read/write mix, swept across concurrency
levels (e.g. 10/20/40 clients) per the assignment's "stand out" criteria.

Usage:
    python workloads/mixed_workload.py --platform COGNODB
    python workloads/mixed_workload.py --platform COGNODB --concurrency 10,20,40 --seconds 60 --write-ratio 0.2
"""
import argparse
import random
import sys
import threading
import time

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import PLATFORMS, MIXED_WORKLOAD_SECONDS, MIXED_WORKLOAD_CONCURRENCY, RESULTS_DIR
from harness.driver import get_driver, run_cypher
from harness.stats import summarize, save_result

READ_QUERY = "MATCH (p:Person {id: $id})-[:KNOWS]->(b) RETURN count(b) AS c"
WRITE_QUERY = """
MATCH (a:Person {id: $id})
MERGE (a)-[:VISITED {ts: timestamp()}]->(a)
"""  # self-loop write chosen so the mixed workload never depends on / mutates
     # the read dataset's topology -- keeps read latencies comparable across runs


def worker(driver, ids, write_ratio, stop_event, latencies, errors, lock):
    local_lat = []
    local_err = 0
    rng = random.Random()
    while not stop_event.is_set():
        node_id = rng.choice(ids)
        is_write = rng.random() < write_ratio
        cypher = WRITE_QUERY if is_write else READ_QUERY
        t0 = time.perf_counter()
        try:
            run_cypher(driver, cypher, {"id": node_id})
            local_lat.append((time.perf_counter() - t0) * 1000.0)
        except Exception:
            local_err += 1
    with lock:
        latencies.extend(local_lat)
        errors[0] += local_err


def run_concurrency_level(platform, ids, concurrency, seconds, write_ratio):
    drivers = [get_driver(platform) for _ in range(concurrency)]
    latencies, errors, lock = [], [0], threading.Lock()
    stop_event = threading.Event()

    threads = [
        threading.Thread(target=worker, args=(d, ids, write_ratio, stop_event, latencies, errors, lock))
        for d in drivers
    ]
    for t in threads:
        t.start()
    time.sleep(seconds)
    stop_event.set()
    for t in threads:
        t.join()
    for d in drivers:
        d.close()

    stats = summarize(latencies)
    stats["throughput_qps"] = round(len(latencies) / seconds, 2)
    stats["errors"] = errors[0]
    stats["concurrency"] = concurrency
    stats["write_ratio"] = write_ratio
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=[p.key for p in PLATFORMS])
    ap.add_argument("--concurrency", default=",".join(str(c) for c in MIXED_WORKLOAD_CONCURRENCY),
                     help="Comma-separated list, e.g. 10,20,40")
    ap.add_argument("--seconds", type=int, default=MIXED_WORKLOAD_SECONDS)
    ap.add_argument("--write-ratio", type=float, default=0.2, help="Fraction of ops that are writes")
    args = ap.parse_args()

    platform = next(p for p in PLATFORMS if p.key == args.platform)
    concurrency_levels = [int(x) for x in args.concurrency.split(",")]

    seed_driver = get_driver(platform)
    rows = run_cypher(seed_driver, "MATCH (p:Person) RETURN p.id AS id LIMIT 5000")
    ids = [r["id"] for r in rows]
    seed_driver.close()

    sweep_results = []
    for c in concurrency_levels:
        print(f"[{platform.key}] mixed workload @ concurrency={c}, "
              f"{args.seconds}s, write_ratio={args.write_ratio} ...")
        sweep_results.append(run_concurrency_level(platform, ids, c, args.seconds, args.write_ratio))

    results = {"platform": platform.display_name, "seconds_per_level": args.seconds,
               "write_ratio": args.write_ratio, "sweep": sweep_results}
    print(results)
    path = save_result(platform.key, "mixed_workload", results, RESULTS_DIR)
    print(f"Saved -> {path}")
