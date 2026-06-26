from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.request


SAMPLE_PAYLOAD = {
    "ticket_id": "LOAD-TICKET",
    "complaint": "Payment failed at merchant checkout.",
    "transaction_history": [],
}


def post_once(base_url: str, index: int) -> float:
    payload = dict(SAMPLE_PAYLOAD)
    payload["ticket_id"] = f"LOAD-TICKET-{index}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/analyze-ticket",
        data=body,
        headers={"Content-Type": "application/json", "Idempotency-Key": f"load-{index}"},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}")
    return (time.perf_counter() - start) * 1000


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(len(ordered) * percentile_value), len(ordered) - 1)
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="QueueStorm local smoke load test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    latencies: list[float] = []
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(post_once, args.base_url, index) for index in range(args.requests)]
        for future in concurrent.futures.as_completed(futures):
            latencies.append(future.result())

    print(
        json.dumps(
            {
                "requests": args.requests,
                "workers": args.workers,
                "duration_seconds": round(time.perf_counter() - started, 3),
                "p50_ms": round(percentile(latencies, 0.50), 2),
                "p95_ms": round(percentile(latencies, 0.95), 2),
                "max_ms": round(max(latencies) if latencies else 0.0, 2),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
