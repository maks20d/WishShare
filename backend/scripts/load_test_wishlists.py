import argparse
import asyncio
import random
import string
import time

import httpx


def _rand_email() -> str:
    return "loadtest_" + "".join(random.choice(string.ascii_lowercase) for _ in range(8)) + "@example.com"


async def run(base_url: str, gifts: int, requests: int, concurrency: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        email = _rand_email()
        await client.post("/auth/register", json={"email": email, "password": "Test1234!", "name": "Load Test"})
        await client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        wl = await client.post("/wishlists", json={"title": "Load Test", "privacy": "public"})
        data = wl.json()
        slug = data["slug"]

        for i in range(gifts):
            await client.post(
                f"/wishlists/{slug}/gifts",
                json={"title": f"Gift {i}", "is_collective": False, "is_private": False},
            )

        latencies: list[float] = []

        async def hit() -> None:
            start = time.perf_counter()
            res = await client.get(f"/wishlists/{slug}")
            latencies.append((time.perf_counter() - start) * 1000.0)
            if res.status_code != 200:
                raise RuntimeError(f"status {res.status_code}")

        pending = requests
        while pending > 0:
            batch = min(concurrency, pending)
            await asyncio.gather(*[hit() for _ in range(batch)])
            pending -= batch

        lat_sorted = sorted(latencies)
        p50 = lat_sorted[len(lat_sorted) // 2]
        p95 = lat_sorted[int(len(lat_sorted) * 0.95) - 1]
        print(f"requests={requests} concurrency={concurrency} gifts={gifts} p50_ms={p50:.2f} p95_ms={p95:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--gifts", type=int, default=80)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.gifts, args.requests, args.concurrency))


if __name__ == "__main__":
    main()
