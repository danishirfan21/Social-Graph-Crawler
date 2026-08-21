# Benchmark results

No benchmark has been run for V2 yet. This file intentionally contains no performance claim.

After a successful Codespaces V2 verification, run a controlled fixture workload, for example:

```bash
docker compose up -d --scale worker=3
python3 scripts/load_fixture.py --jobs 1000
```

Record the actual Codespaces machine type, worker count, elapsed time, terminal job counts, retries, and duplicate suppression here. The workload is synthetic fixture processing, not web-crawling throughput; do not extrapolate it to internet-scale claims.
