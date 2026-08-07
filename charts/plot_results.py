"""
Generate PNG bar charts from results/combined.json (run
harness/build_report.py first). Saves into charts/output/.

Usage:
    python charts/plot_results.py
"""
import json
import os
import sys

import matplotlib.pyplot as plt

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from harness.config import RESULTS_DIR, PLATFORMS

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def load_combined():
    with open(f"{RESULTS_DIR}/combined.json") as f:
        return json.load(f)


def bar_chart(labels, values, title, ylabel, filename):
    os.makedirs(OUT_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    path = os.path.join(OUT_DIR, filename)
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Wrote {path}")


def chart_load_throughput(all_results):
    labels, values = [], []
    for p in PLATFORMS:
        r = all_results.get(p.key, {}).get("load")
        if r:
            labels.append(p.display_name)
            values.append(r.get("relationships_per_second") or 0)
    if labels:
        bar_chart(labels, values, "Ingest throughput", "Relationships/sec", "load_throughput.png")


def chart_traversal_p95(all_results, hop="2"):
    labels, values = [], []
    for p in PLATFORMS:
        r = all_results.get(p.key, {}).get("traversals")
        if r:
            labels.append(p.display_name)
            values.append(r["hops"].get(hop, {}).get("p95") or 0)
    if labels:
        bar_chart(labels, values, f"{hop}-hop traversal latency (p95)", "ms", f"traversal_{hop}hop_p95.png")


def chart_mixed_qps(all_results, concurrency=10):
    labels, values = [], []
    for p in PLATFORMS:
        r = all_results.get(p.key, {}).get("mixed_workload")
        if not r:
            continue
        level = next((l for l in r["sweep"] if l["concurrency"] == concurrency), None)
        if level:
            labels.append(p.display_name)
            values.append(level.get("throughput_qps") or 0)
    if labels:
        bar_chart(labels, values, f"Mixed workload throughput @ concurrency={concurrency}",
                   "queries/sec", f"mixed_qps_c{concurrency}.png")


if __name__ == "__main__":
    all_results = load_combined()
    chart_load_throughput(all_results)
    for hop in ("1", "2", "3"):
        chart_traversal_p95(all_results, hop)
    chart_mixed_qps(all_results, concurrency=10)
