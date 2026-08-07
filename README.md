# Graph Database Cloud Benchmark: CognoDB vs. Neo4j AuraDB, Memgraph Cloud, FalkorDB, and self-hosted Neo4j

Reproducible benchmark suite comparing [CognoDB Cloud](https://console.cognodb.com)
against four other managed/self-hosted graph databases on identical
hardware tiers, identical data, and identical query workloads.

> **Status:** this repo ships a complete, runnable harness. The results
> tables below are placeholders (`TODO`) until each platform's free-tier
> account is provisioned and `harness/run_all.py --all` is executed --
> see [Reproducing this benchmark](#reproducing-this-benchmark).

## Why these five platforms

| Platform | Why it's in scope |
|---|---|
| **CognoDB Cloud** | Platform under test. |
| **Neo4j AuraDB Free** | The reference implementation of the Bolt/Cypher protocol CognoDB itself uses -- the most direct apples-to-apples comparison available. |
| **Memgraph Cloud** | In-memory-first graph engine with a Bolt/Cypher-compatible interface; useful contrast on latency-sensitive workloads against disk-backed engines. |
| **FalkorDB Cloud** | Sparse-matrix/GraphBLAS-backed engine, also Bolt-compatible; a different internal architecture again for contrast. |
| **Self-hosted Neo4j (docker, resource-capped)** | A transparent, fully-controlled baseline -- rules out "mystery managed-service overhead" as an explanation for any gap, since we can inspect and cap its resources directly. |

All five speak Bolt / openCypher, so this repo uses **one** generic
driver-based loader and workload set (`loaders/`, `workloads/`) against
every platform -- no per-platform query rewriting, which removes a whole
class of "did we write the query fairly" bias. If you swap in a
non-Bolt platform (e.g. ArangoDB/AQL, Amazon Neptune/Gremlin), you'll
need to write an adapter with the same interface as `harness/driver.py`;
`harness/config.py` has notes on where that plugs in.

## Resource parity

Every platform is provisioned at its smallest/free tier, sized to match
CognoDB's advertised free (`c0`) instance: **burstable 0.5 vCPU / 256 MB
RAM / 1 GB disk**. Verify each provider's current free-tier specs before
running (they change) and record what you actually got here:

| Platform | vCPU | RAM | Disk | Notes |
|---|---|---|---|---|
| CognoDB Cloud (c0 free) | 0.5 vCPU (burstable) | 256 MB | 1 GB | |
| Neo4j AuraDB Free | TODO | TODO | TODO | confirm at neo4j.com/pricing |
| Memgraph Cloud (free) | TODO | TODO | TODO | confirm at memgraph.com/pricing |
| FalkorDB Cloud (free) | TODO | TODO | TODO | confirm at falkordb.com/pricing |
| Self-hosted Neo4j (docker) | 0.5 vCPU (cgroup capped) | 256 MB | 1 GB | see `docker-compose.yml` |

This table is also generated automatically into `results/report.md` by
`harness/build_report.py`, sourced from `harness/config.py` -- keep that
file as the single source of truth and this section in sync with it.

## Dataset

[SNAP soc-Pokec social network](https://snap.stanford.edu/data/soc-Pokec.html),
sampled down to **TODO_NODES nodes / TODO_EDGES relationships**
(target range: 100k-500k relationships, per the assignment, so it fits
every platform's free tier). `data/download_dataset.py` downloads the
full edge list and takes a seeded random sample so the run is
reproducible; node ids are remapped to a dense 0..N-1 range.

Schema loaded into every platform:
- `(:Person {id: int})` -- unique constraint on `id` (see `loaders/load_data.py`)
- `(:Person)-[:KNOWS]->(:Person)` -- directed edges from the sample

## Repo layout

```
harness/            shared config, driver connection helper, stats, orchestration, report builder
  config.py            platform list + connection info (reads .env) + resource specs
  driver.py             thin neo4j-driver wrapper with connect retries
  stats.py               percentile calc + result save/load
  run_all.py            runs load -> all workloads for one platform or --all
  build_report.py    turns results/*.json into results/report.md (markdown tables)
data/
  download_dataset.py    fetches + samples the SNAP dataset -> data/dataset.csv
loaders/
  load_data.py           UNWIND-batched Cypher loader; measures ingest throughput
workloads/
  traversals.py           1/2/3-hop latency, p50/p95, over a fixed random node sample
  lookups.py                point lookup (indexed) + filtered/range lookup, p50/p95
  aggregations.py         count + group-by aggregation, p50/p95
  mixed_workload.py     concurrent read/write throughput, swept across concurrency levels
charts/
  plot_results.py         bar charts from results/combined.json -> charts/output/*.png
results/                   raw JSON per platform/workload + generated report.md (gitignored except .gitkeep)
docker-compose.yml          resource-capped self-hosted Neo4j control platform
```

## Reproducing this benchmark

**Prerequisites:** Python 3.10+, Docker (for the self-hosted control
platform), and free-tier accounts on CognoDB Cloud, Neo4j AuraDB,
Memgraph Cloud, and FalkorDB Cloud.

1. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Provision each platform's free instance** and note its connection
   URI + password (each provider shows the password once at creation --
   save it immediately). For CognoDB specifically: sign up at
   console.cognodb.com, create a free `c0` instance, and use the
   `bolt+s://...` URI it gives you with user `cognodb`.

3. **Configure secrets** -- copy `.env.example` to `.env` and fill in
   every platform's URI/user/password. `.env` is gitignored; nothing in
   this repo ever reads credentials from anywhere else.
   ```bash
   cp .env.example .env
   ```

4. **Bring up the self-hosted control platform**
   ```bash
   docker compose up -d
   ```

5. **Download and sample the dataset**
   ```bash
   python data/download_dataset.py --target-edges 250000
   ```

6. **Run the full suite** (load + all workloads) against every platform:
   ```bash
   python harness/run_all.py --all
   # or one at a time, e.g.:
   python harness/run_all.py --platform COGNODB
   ```
   Each workload script can also be run standalone with
   `--iterations`/`--warmup`/etc. overrides -- see the docstring at the
   top of each file in `workloads/`.

7. **Build the results tables and charts**
   ```bash
   python harness/build_report.py     # -> results/report.md, results/combined.json
   python charts/plot_results.py       # -> charts/output/*.png
   ```
   Paste the tables from `results/report.md` into the sections below,
   replacing the `TODO` placeholders.

Total one-command re-run time: expect roughly 20-40 minutes per platform
for the default settings (100 iterations/workload, 60s x 3 concurrency
levels for the mixed workload); free-tier instances can also be slow to
wake from an idle/sleep state on the first request.

---

## Results

_Generated by `harness/build_report.py` from `results/*.json`. Run the
steps above, then replace this section with the contents of
`results/report.md`._

### Data loading

| Platform | Nodes | Relationships | Nodes/sec | Rels/sec |
|---|---|---|---|---|
| CognoDB Cloud | TODO | TODO | TODO | TODO |
| Neo4j AuraDB Free | TODO | TODO | TODO | TODO |
| Memgraph Cloud | TODO | TODO | TODO | TODO |
| FalkorDB Cloud | TODO | TODO | TODO | TODO |
| Self-hosted Neo4j | TODO | TODO | TODO | TODO |

### Traversals (p50 / p95, ms)

| Platform | 1-hop | 2-hop | 3-hop |
|---|---|---|---|
| CognoDB Cloud | TODO / TODO | TODO / TODO | TODO / TODO |
| Neo4j AuraDB Free | TODO / TODO | TODO / TODO | TODO / TODO |
| Memgraph Cloud | TODO / TODO | TODO / TODO | TODO / TODO |
| FalkorDB Cloud | TODO / TODO | TODO / TODO | TODO / TODO |
| Self-hosted Neo4j | TODO / TODO | TODO / TODO | TODO / TODO |

### Lookups (p50 / p95, ms)

| Platform | Point (indexed) | Filtered/range |
|---|---|---|
| CognoDB Cloud | TODO / TODO | TODO / TODO |
| Neo4j AuraDB Free | TODO / TODO | TODO / TODO |
| Memgraph Cloud | TODO / TODO | TODO / TODO |
| FalkorDB Cloud | TODO / TODO | TODO / TODO |
| Self-hosted Neo4j | TODO / TODO | TODO / TODO |

### Aggregations (p50 / p95, ms)

| Platform | Count | Group-by |
|---|---|---|
| CognoDB Cloud | TODO / TODO | TODO / TODO |
| Neo4j AuraDB Free | TODO / TODO | TODO / TODO |
| Memgraph Cloud | TODO / TODO | TODO / TODO |
| FalkorDB Cloud | TODO / TODO | TODO / TODO |
| Self-hosted Neo4j | TODO / TODO | TODO / TODO |

### Mixed read/write workload (80% read / 20% write)

| Platform | Concurrency | QPS | p50 (ms) | p95 (ms) | Errors |
|---|---|---|---|---|---|
| CognoDB Cloud | 10 | TODO | TODO | TODO | TODO |
| CognoDB Cloud | 20 | TODO | TODO | TODO | TODO |
| CognoDB Cloud | 40 | TODO | TODO | TODO | TODO |
| _...repeat per platform..._ | | | | | |

### Footprint

| Platform | Stored data size | Memory usage | Notes |
|---|---|---|---|
| CognoDB Cloud | TODO or "not observable" | TODO or "not observable" | |
| Neo4j AuraDB Free | TODO | TODO | |
| Memgraph Cloud | TODO | TODO | |
| FalkorDB Cloud | TODO | TODO | |
| Self-hosted Neo4j | TODO (`docker system df` / container stats) | TODO | fully observable since we control the host |

---

## Methodology notes and caveats

_Fill in honestly as you run this -- this section is worth real credit
per the assignment's grading rubric. Things to record here:_

- Free-tier throttling or rate limiting encountered on any platform.
- Network variance -- what region/client machine was used, and whether
  latency to each provider's region was comparable.
- Any query-language / feature differences that forced a workaround
  (e.g. a platform lacking `MERGE`, a different constraint syntax).
- Timeouts or failed runs, and how they were handled (retried? excluded?
  reported as errors in the mixed-workload table?).
- Cold-start numbers if you captured them separately from warm numbers
  (the harness as shipped only reports warm numbers -- see
  `WARMUP_ITERATIONS` in `.env`; add a `--no-warmup` cold-start pass if
  you want to report both).
- Whether Docker's `storage_opt` disk-size limit was actually enforced
  by your storage driver for the self-hosted control platform (it isn't
  on all drivers/OSes) -- note this explicitly if the 1GB cap wasn't
  really enforced.

## Analysis

_TODO after running: what do the numbers show, and where you can, why._
Things worth speculating about with evidence from the results above:
in-memory-first architectures (Memgraph) vs. disk-backed (Neo4j-family)
on traversal latency; managed-service network hop overhead vs.
self-hosted; how each platform's free-tier burst/throttle behavior shows
up in the mixed-workload p95 as concurrency increases.

## Security note

No credentials are committed to this repository. All connection URIs
and passwords are read from environment variables via `.env` (gitignored,
see `.env.example` for the required keys).

## License

MIT (see `LICENSE`).
