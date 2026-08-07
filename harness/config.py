"""
Central config: which platforms to benchmark and how to connect to them.

Every platform here speaks the Bolt protocol / openCypher, so a single
driver-based loader and workload set (see loaders/load_data.py and
workloads/*.py) runs unmodified against all of them. If you add a
platform that does NOT speak Bolt (e.g. ArangoDB's AQL, Amazon Neptune's
Gremlin), write an adapter that implements the same run_query(tx, cypher,
params) interface used here and register it in PLATFORMS below.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Platform:
    key: str
    display_name: str
    uri: str
    user: str
    password: str
    # Advertised free-tier specs -- fill these in from each provider's
    # pricing page and keep them in sync with what you actually provisioned.
    vcpu: str
    ram_mb: int
    disk_gb: int
    notes: str = ""


def _platform(key, display_name, vcpu, ram_mb, disk_gb, notes=""):
    return Platform(
        key=key,
        display_name=display_name,
        uri=os.environ.get(f"{key}_URI", ""),
        user=os.environ.get(f"{key}_USER", ""),
        password=os.environ.get(f"{key}_PASSWORD", ""),
        vcpu=vcpu,
        ram_mb=ram_mb,
        disk_gb=disk_gb,
        notes=notes,
    )


# EDIT THIS LIST to reflect the databases you actually benchmark. The
# assignment requires CognoDB + at least 4 others, all at equivalent
# free-tier resource limits. Fill in real advertised specs here and
# double check they match what you provisioned -- this list becomes the
# resource-parity table in the README.
PLATFORMS = [
    _platform("COGNODB", "CognoDB Cloud (c0 free)", "0.5 vCPU (burstable)", 512, 1,
              "Baseline platform under test. Actual provisioned memory: 512 MB."),
    _platform("AURA", "Neo4j AuraDB Free", "shared/burstable", 256, 1,
              "Verify current free-tier specs on neo4j.com/pricing before running."),
    _platform("MEMGRAPH", "Memgraph Cloud (free tier)", "shared", 256, 1,
              "Verify current free-tier specs before running."),
    _platform("FALKORDB", "FalkorDB Cloud (free tier)", "shared", 256, 1,
              "Verify current free-tier specs before running."),
    _platform("SELFHOSTED", "Self-hosted Neo4j (docker, capped)", "0.5 vCPU (cgroup capped)", 256, 1,
              "Control platform: same container resource caps as CognoDB's "
              "advertised free tier, run via docker-compose.yml in this repo."),
]

DATASET_PATH = os.environ.get("DATASET_PATH", "./data/dataset.csv")
READ_ITERATIONS = int(os.environ.get("READ_ITERATIONS", 100))
WARMUP_ITERATIONS = int(os.environ.get("WARMUP_ITERATIONS", 20))
MIXED_WORKLOAD_SECONDS = int(os.environ.get("MIXED_WORKLOAD_SECONDS", 60))
MIXED_WORKLOAD_CONCURRENCY = [
    int(x) for x in os.environ.get("MIXED_WORKLOAD_CONCURRENCY", "10,20,40").split(",")
]
RESULTS_DIR = os.environ.get("RESULTS_DIR", "./results")
