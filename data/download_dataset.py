"""
Download and prepare the benchmark dataset.

Default: a sampled slice of SNAP's soc-Pokec social network
(https://snap.stanford.edu/data/soc-Pokec.html), trimmed to land in the
100k-500k relationship range required by the assignment so it fits every
platform's free tier.

Usage:
    python data/download_dataset.py --target-edges 250000

Output: data/dataset.csv with columns: src,dst  (directed edges, 0-indexed
node ids). Node count is derived automatically from the max id seen.

NOTE: This script needs outbound internet access to snap.stanford.edu.
If your environment blocks that, download soc-Pokec-relationships.txt.gz
manually and place it at data/soc-Pokec-relationships.txt.gz, then re-run
this script -- it will skip the download step if the file already exists.
"""
import argparse
import gzip
import os
import random
import sys
import urllib.request

SNAP_URL = "https://snap.stanford.edu/data/soc-pokec-relationships.txt.gz"
RAW_PATH = os.path.join(os.path.dirname(__file__), "soc-Pokec-relationships.txt.gz")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dataset.csv")


def download():
    if os.path.exists(RAW_PATH):
        print(f"Raw file already present at {RAW_PATH}, skipping download.")
        return
    print(f"Downloading {SNAP_URL} ...")
    urllib.request.urlretrieve(SNAP_URL, RAW_PATH)
    print("Download complete.")


def sample_edges(target_edges, seed=42):
    random.seed(seed)

    edges = []
    adjacency = {}

    with gzip.open(RAW_PATH, "rt") as f:
        for line in f:
            src, dst = map(int, line.strip().split("\t"))

            edges.append((src, dst))

            adjacency.setdefault(src, []).append(dst)
            adjacency.setdefault(dst, []).append(src)

    print(f"Loaded {len(edges)} total edges from source file.")

    start = random.choice(list(adjacency.keys()))

    visited_nodes = set()
    visited_edges = set()
    sampled = []

    from collections import deque
    queue = deque([start])

    while queue and len(sampled) < target_edges:
        node = queue.popleft()

        if node in visited_nodes:
            continue

        visited_nodes.add(node)

        for nbr in adjacency.get(node, []):
            edge = (node, nbr)

            if edge not in visited_edges:
                visited_edges.add(edge)
                sampled.append(edge)

                if len(sampled) >= target_edges:
                    break

            if nbr not in visited_nodes:
                queue.append(nbr)

    node_ids = sorted({n for e in sampled for n in e})
    remap = {old: new for new, old in enumerate(node_ids)}

    with open(OUT_PATH, "w") as f:
        f.write("src,dst\n")
        for src, dst in sampled:
            f.write(f"{remap[src]},{remap[dst]}\n")

    print(f"Wrote {len(sampled)} edges / {len(node_ids)} nodes to {OUT_PATH}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--target-edges",
        type=int,
        default=250_000,
        help="Number of relationships to sample (100k-500k recommended).",
    )
    args = ap.parse_args()

    try:
        download()
    except Exception as e:
        print(
            f"Download failed ({e}). If network access is restricted in your "
            f"environment, fetch {SNAP_URL} manually and save it to {RAW_PATH}, "
            f"then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    sample_edges(args.target_edges)