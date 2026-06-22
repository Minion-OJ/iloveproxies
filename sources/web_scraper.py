"""
web_scraper.py
Scrapes SOCKS5 proxies from public web pages.
Adapted from ProxyBroker's providers.py — only SOCKS5-relevant providers.
Pure aiohttp, no ProxyBroker dependency.
"""

import asyncio
import re
from base64 import b64decode
from html import unescape
from math import sqrt
from urllib.parse import unquote

import aiohttp

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
_IP_PORT = re.compile(
    r"(?P<ip>(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?))"
    r"\s*[:\s]\s*"
    r"(?P<port>\d{2,5})"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_TIMEOUT = aiohttp.ClientTimeout(total=25)
_MAX_TRIES = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_ip_port(page: str) -> list[str]:
    """Return list of 'ip:port' strings from raw page text."""
    return [f"{m[0]}:{m[1]}" for m in _IP_PORT.findall(page)]


async def _get(session: aiohttp.ClientSession, url: str, **kwargs) -> str:
    """Fetch a page with retries."""
    method = kwargs.pop("method", "GET")
    for _ in range(_MAX_TRIES):
        try:
            async with session.request(
                method, url, timeout=_TIMEOUT, headers=_HEADERS, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.text(errors="ignore")
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# Individual scrapers
# ---------------------------------------------------------------------------
async def _scrape_socks_proxy_net(session: aiohttp.ClientSession) -> list[str]:
    """socks-proxy.net — Free SOCKS proxy list."""
    page = await _get(session, "https://socks-proxy.net/")
    return _extract_ip_port(page)


async def _scrape_proxy_list_download(session: aiohttp.ClientSession) -> list[str]:
    """proxy-list.download API — SOCKS5 endpoint."""
    page = await _get(
        session,
        "https://www.proxy-list.download/api/v1/get?type=socks5",
    )
    return _extract_ip_port(page)


async def _scrape_proxylistplus(session: aiohttp.ClientSession) -> list[str]:
    """list.proxylistplus.com — Socks list pages."""
    results = []
    for n in range(1, 7):
        page = await _get(
            session,
            f"http://list.proxylistplus.com/Socks-List-{n}",
        )
        results.extend(_extract_ip_port(page))
    return results


async def _scrape_free_proxy_list_net(session: aiohttp.ClientSession) -> list[str]:
    """free-proxy-list.net — General proxy list."""
    page = await _get(session, "https://free-proxy-list.net/")
    return _extract_ip_port(page)


async def _scrape_us_proxy(session: aiohttp.ClientSession) -> list[str]:
    """us-proxy.org — US proxy list."""
    page = await _get(session, "https://us-proxy.org/")
    return _extract_ip_port(page)


async def _scrape_proxyscrape(session: aiohttp.ClientSession) -> list[str]:
    """proxyscrape.com — SOCKS5 API."""
    page = await _get(
        session,
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
    )
    return _extract_ip_port(page)


async def _scrape_spys_socks(session: aiohttp.ClientSession) -> list[str]:
    """spys.one — SOCKS proxy list."""
    page = await _get(session, "https://spys.one/en/socks-proxy-list/")
    if not page:
        return []

    # spys.one hides ports with JS XOR. Extract the char-to-number mapping.
    char_eq_num = {}
    exp_char_num = r"[>;]{1}(?P<char>[a-z\d]{4,})=(?P<num>[a-z\d\^]+)"
    res = re.findall(exp_char_num, page)
    for char, num in res:
        if "^" in num:
            digit, tochar = num.split("^")
            num = int(digit) ^ char_eq_num.get(tochar, 0)
        char_eq_num[char] = int(num)

    # Now decode the port expressions
    def _decode_port(matchobj):
        chars = matchobj.groups()[0].split("+")
        num = ""
        for chunk in chars[1:]:  # first is empty
            var1, var2 = chunk.strip("()").split("^")
            digit = char_eq_num.get(var1, 0) ^ char_eq_num.get(var2, 0)
            num += str(digit)
        return num

    exp_port_js = r"(?P<js_port_code>(?:\+\([a-z0-9^+]+\))+)"
    decoded_page = re.sub(exp_port_js, _decode_port, page)
    return _extract_ip_port(decoded_page)


async def _scrape_checkerproxy(session: aiohttp.ClientSession) -> list[str]:
    """checkerproxy.net — Archive-based proxy list."""
    page = await _get(session, "https://checkerproxy.net/")
    if not page:
        return []
    exp = r"""href\s*=\s*['"](/archive/\d{4}-\d{2}-\d{2})['"]"""
    paths = re.findall(exp, page)[:3]  # Only check last 3 days
    results = []
    for path in paths:
        api_page = await _get(session, f"https://checkerproxy.net/api{path}")
        results.extend(_extract_ip_port(api_page))
    return results


# ---------------------------------------------------------------------------
# All scrapers
# ---------------------------------------------------------------------------
_SCRAPERS = [
    ("socks-proxy.net", _scrape_socks_proxy_net),
    ("proxy-list.download", _scrape_proxy_list_download),
    ("proxylistplus.com", _scrape_proxylistplus),
    ("free-proxy-list.net", _scrape_free_proxy_list_net),
    ("us-proxy.org", _scrape_us_proxy),
    ("proxyscrape.com", _scrape_proxyscrape),
    ("spys.one", _scrape_spys_socks),
    ("checkerproxy.net", _scrape_checkerproxy),
]


async def scrape_all(progress_callback=None) -> set[str]:
    """
    Scrape all web providers for SOCKS5 proxies.

    Args:
        progress_callback: Optional async callable(source_name, count) called
                           after each scraper completes.

    Returns:
        Deduplicated set of 'host:port' strings.
    """
    proxies: set[str] = set()

    async with aiohttp.ClientSession() as session:
        tasks = {
            asyncio.ensure_future(fn(session)): name
            for name, fn in _SCRAPERS
        }
        for coro in asyncio.as_completed(list(tasks.keys())):
            try:
                result = await coro
            except Exception:
                result = []
            proxies.update(result)
            if progress_callback:
                await progress_callback(len(result))

    return proxies
