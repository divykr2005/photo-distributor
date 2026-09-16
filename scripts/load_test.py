"""Small dependency-light concurrent HTTP smoke/load test.

Example:
    python scripts/load_test.py http://localhost:8000/healthz -c 50 -n 500
"""

from __future__ import annotations

import argparse
import asyncio
import math
import time
from collections import Counter

import httpx


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, math.ceil(len(values) * fraction) - 1)
    return sorted(values)[index]


async def run(args: argparse.Namespace) -> int:
    semaphore = asyncio.Semaphore(args.concurrency)
    durations: list[float] = []
    statuses: Counter[int | str] = Counter()

    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        async def request_once() -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(args.url)
                    statuses[response.status_code] += 1
                except httpx.HTTPError as exc:
                    statuses[type(exc).__name__] += 1
                finally:
                    durations.append((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        await asyncio.gather(*(request_once() for _ in range(args.requests)))
        elapsed = time.perf_counter() - started

    print(f"URL: {args.url}")
    print(f"Requests: {args.requests}; concurrency: {args.concurrency}")
    print(f"Statuses: {dict(statuses)}")
    print(f"Throughput: {args.requests / elapsed:.2f} requests/second")
    print(
        "Latency ms: "
        f"p50={percentile(durations, 0.50):.2f} "
        f"p95={percentile(durations, 0.95):.2f} "
        f"p99={percentile(durations, 0.99):.2f} "
        f"max={max(durations, default=0):.2f}"
    )

    unexpected = sum(
        count for status, count in statuses.items()
        if status != args.expected_status
    )
    return 1 if unexpected else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a concurrent GET load test.")
    parser.add_argument("url")
    parser.add_argument("-c", "--concurrency", type=int, default=25)
    parser.add_argument("-n", "--requests", type=int, default=250)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expected-status", type=int, default=200)
    args = parser.parse_args()
    if args.concurrency < 1 or args.requests < 1:
        parser.error("concurrency and requests must be positive")
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
