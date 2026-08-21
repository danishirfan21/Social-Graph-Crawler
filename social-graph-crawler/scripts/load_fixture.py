#!/usr/bin/env python3
"""Submit deterministic fixture jobs and report API-side completion time.

Run only after the Compose stack is healthy; it does not claim a benchmark by
itself. Example: python3 scripts/load_fixture.py --jobs 100
"""
import argparse
import json
import time
from urllib.request import Request, urlopen


def request(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    headers = {"Content-Type": "application/json"} if data else {}
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=int, default=100)
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    started = time.monotonic()
    job_ids = []
    for index in range(args.jobs):
        job = request(f"{args.url}/api/v1/crawl/start", {"source": "fixture", "start_entity": f"load-{index}", "depth": 2, "max_entities": 10})
        job_ids.append(job["id"])
    pending = set(job_ids)
    while pending:
        for job_id in tuple(pending):
            status = request(f"{args.url}/api/v1/crawl/jobs/{job_id}")["status"]
            if status in {"completed", "failed", "cancelled"}:
                pending.remove(job_id)
        time.sleep(0.1)
    elapsed = time.monotonic() - started
    print(json.dumps({"jobs": args.jobs, "seconds": round(elapsed, 3), "jobs_per_second": round(args.jobs / elapsed, 3)}))


if __name__ == "__main__":
    main()
