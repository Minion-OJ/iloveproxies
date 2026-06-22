"""
validator.py
Async SOCKS5 proxy validator with concurrency control and latency tracking.
Adapted from iloveproxies/proxman.py test_socks() and ProxyBroker checker.
"""

import asyncio
import time
from dataclasses import dataclass

import aiohttp
from aiohttp_socks import ProxyConnector

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_TEST_URL = "http://httpbin.org/ip"
FALLBACK_TEST_URL = "http://example.com"
TIMEOUT_SECONDS = 5
MAX_RETRIES = 1


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
@dataclass
class ProxyResult:
    proxy: str          # "host:port"
    alive: bool
    latency_ms: float   # round-trip in milliseconds, -1 if dead
    country: str = ""   # placeholder for future GeoIP


# ---------------------------------------------------------------------------
# Single proxy test
# ---------------------------------------------------------------------------
async def _test_one(proxy: str) -> ProxyResult:
    """
    Attempt to connect through a SOCKS5 proxy to a test URL.
    Retries up to MAX_RETRIES times. Returns a ProxyResult.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            connector = ProxyConnector.from_url(f"socks5://{proxy}")
            timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            start = time.perf_counter()
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                async with session.get(DEFAULT_TEST_URL) as resp:
                    if resp.status == 200:
                        elapsed = (time.perf_counter() - start) * 1000
                        return ProxyResult(
                            proxy=proxy,
                            alive=True,
                            latency_ms=round(elapsed, 1),
                        )
        except Exception:
            pass

    return ProxyResult(proxy=proxy, alive=False, latency_ms=-1)


# ---------------------------------------------------------------------------
# Batch validator
# ---------------------------------------------------------------------------
async def validate_batch(
    proxies: set[str],
    concurrency: int = 150,
    on_result=None,
) -> list[ProxyResult]:
    """
    Validate a batch of SOCKS5 proxies concurrently.

    Args:
        proxies: Set of 'host:port' strings to test.
        concurrency: Max concurrent checks.
        on_result: Optional async callable(ProxyResult) called as each proxy is checked.

    Returns:
        List of ProxyResult for every proxy tested (both alive and dead).
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[ProxyResult] = []

    async def _wrapped(proxy: str):
        async with semaphore:
            result = await _test_one(proxy)
            results.append(result)
            if on_result:
                await on_result(result)

    tasks = [asyncio.ensure_future(_wrapped(p)) for p in sorted(proxies)]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results
