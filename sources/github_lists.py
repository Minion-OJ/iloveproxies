"""
github_lists.py
Downloads SOCKS5 proxy lists from curated GitHub raw sources.
Adapted from iloveproxies/proxman.py.
"""

import aiohttp

# ---------------------------------------------------------------------------
# SOCKS5 raw-text source URLs
# ---------------------------------------------------------------------------
SOCKS5_SOURCES = [
    "https://raw.githubusercontent.com/FifzzSENZE/Master-Proxy/master/proxies/socks5.txt",
    "https://raw.githubusercontent.com/gaurav-321/Public-Fast-Proxy-Listy/master/socks5.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/socks5.txt",
    "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/RX4096/proxy-list/main/online/socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
]

_DOWNLOAD_TIMEOUT = 20  # seconds per URL


async def _fetch_one(session: aiohttp.ClientSession, url: str) -> list[str]:
    """Fetch a single URL and return lines that look like host:port."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=_DOWNLOAD_TIMEOUT)) as resp:
            if resp.status != 200:
                return []
            text = await resp.text(encoding="utf-8", errors="ignore")
            results = []
            for line in text.splitlines():
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    parts = line.split(":")
                    if len(parts) == 2 and parts[1].isdigit():
                        results.append(line)
            return results
    except Exception:
        return []


async def fetch_all(progress_callback=None) -> set[str]:
    """
    Download all GitHub raw SOCKS5 lists concurrently.

    Args:
        progress_callback: Optional async callable(url, count) called after each URL finishes.

    Returns:
        Deduplicated set of 'host:port' strings.
    """
    import asyncio

    proxies: set[str] = set()

    async with aiohttp.ClientSession() as session:
        tasks = {
            asyncio.ensure_future(_fetch_one(session, url)): url
            for url in SOCKS5_SOURCES
        }
        for coro in asyncio.as_completed(list(tasks.keys())):
            # find which url this corresponds to
            result = await coro
            proxies.update(result)
            if progress_callback:
                await progress_callback(len(result))

    return proxies
