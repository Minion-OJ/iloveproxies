import asyncio
import aiohttp
import aiofiles
import os
from aiohttp_socks import ProxyConnector
from colorama import Fore, init

init(autoreset=True)

# === Settings ===
TMP_FOLDER = "proxy_tmp"
os.makedirs(TMP_FOLDER, exist_ok=True)

GLOBAL_CONCURRENCY = 200  # <== HARD LIMIT on overall proxy concurrency
TIMEOUT = 5
DEFAULT_TEST_URL = "http://example.com"

# === Hardcoded Source List ===
HARDCODED_LINKS = {
    "http": [
        "https://raw.githubusercontent.com/FifzzSENZE/Master-Proxy/master/proxies/http.txt",
        "https://raw.githubusercontent.com/gaurav-321/Public-Fast-Proxy-Listy/master/http.txt",
        "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/http.txt",
        "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/http.txt",
    ],
    "https": [
        "https://raw.githubusercontent.com/FifzzSENZE/Master-Proxy/master/proxies/https.txt",
        "https://raw.githubusercontent.com/gaurav-321/Public-Fast-Proxy-Listy/master/https.txt",
        "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/https.txt",
        "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/https.txt",
    ],
    "socks4": [
        "https://raw.githubusercontent.com/FifzzSENZE/Master-Proxy/master/proxies/socks4.txt",
        "https://raw.githubusercontent.com/gaurav-321/Public-Fast-Proxy-Listy/master/socks4.txt",
        "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/socks4.txt",
        "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks4.txt",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/FifzzSENZE/Master-Proxy/master/proxies/socks5.txt",
        "https://raw.githubusercontent.com/gaurav-321/Public-Fast-Proxy-Listy/master/socks5.txt",
        "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/socks5.txt",
        "https://raw.githubusercontent.com/SevenworksDev/proxy-list/main/proxies/socks5.txt",
    ]
}


# === Downloader ===
async def download_one(session, url):
    try:
        async with session.get(url, timeout=15) as resp:
            return await resp.text()
    except Exception as e:
        print(f"{Fore.RED}[!] Error downloading {url}: {e}")
        return ""

async def download_all():
    results = {}
    async with aiohttp.ClientSession() as session:
        for proto, urls in HARDCODED_LINKS.items():
            print(f"{Fore.BLUE}[*] Downloading {proto} proxies...")
            proxies = set()
            for url in urls:
                content = await download_one(session, url)
                for line in content.splitlines():
                    line = line.strip()
                    if ":" in line:
                        proxies.add(line)
            filename = f"{proto}_combined.txt"
            async with aiofiles.open(filename, 'w') as f:
                await f.write("\n".join(sorted(proxies)))
            print(f"{Fore.GREEN}[+] Saved {len(proxies)} unique {proto} proxies to {filename}")
            results[proto] = sorted(proxies)
    return results


# === Proxy Test Helpers ===
async def test_http(proxy):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DEFAULT_TEST_URL, proxy=f"http://{proxy}", timeout=TIMEOUT) as resp:
                return resp.status == 200
    except:
        return False

async def test_https(proxy):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://google.com", proxy=f"http://{proxy}", timeout=TIMEOUT) as resp:
                return resp.status == 200
    except:
        return False

async def test_socks(proxy, version):
    try:
        connector = ProxyConnector.from_url(f'socks{version}://{proxy}')
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(DEFAULT_TEST_URL, timeout=TIMEOUT) as resp:
                return resp.status == 200
    except:
        return False

async def write_working(proxy, proto):
    async with aiofiles.open(f"working_{proto}.txt", 'a') as f:
        await f.write(proxy + "\n")


# === Validation (Safe Concurrency) ===
async def validate_proxy(proxy, semaphore):
    async with semaphore:
        async def try_validate(test_func, proto_name):
            for attempt in range(3):
                if await test_func():
                    await write_working(proxy, proto_name)
                    print(f"{Fore.GREEN}[VALID] {proto_name.upper()} - {proxy} (try {attempt+1})")
                    return
            print(f"{Fore.RED}[DEAD ] {proto_name.upper()} - {proxy}")

        await asyncio.gather(
            try_validate(lambda: test_http(proxy), "http"),
            try_validate(lambda: test_https(proxy), "https"),
            try_validate(lambda: test_socks(proxy, 4), "socks4"),
            try_validate(lambda: test_socks(proxy, 5), "socks5"),
        )


# === Main Orchestrator ===
async def validate_all_combined(proxies_by_type):
    all_proxies = set()
    for proxies in proxies_by_type.values():
        all_proxies.update(proxies)

    semaphore = asyncio.Semaphore(GLOBAL_CONCURRENCY)
    tasks = [validate_proxy(proxy, semaphore) for proxy in sorted(all_proxies)]
    await asyncio.gather(*tasks)


# === Main Entry ===
async def main():
    print(f"{Fore.MAGENTA}[+] Starting full proxy pipeline with safety limit {GLOBAL_CONCURRENCY}...")
    proxies_by_type = await download_all()
    await validate_all_combined(proxies_by_type)

if __name__ == "__main__":
    asyncio.run(main())
