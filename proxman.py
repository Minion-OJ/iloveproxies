import asyncio
import aiohttp
import aiofiles
import os
from aiohttp_socks import ProxyConnector
from colorama import Fore, Style, init

init(autoreset=True)

TMP_FOLDER = "proxy_tmp"
os.makedirs(TMP_FOLDER, exist_ok=True)

MAX_THREADS = 100
TIMEOUT = 5
DEFAULT_TEST_URL = "http://example.com"

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


async def validate_all(proxies_by_type):
    semaphore = asyncio.Semaphore(MAX_THREADS)
    results = {"http": [], "https": [], "socks4": [], "socks5": []}

    async def try_validate(proto, proxy):
        if proto == "http":
            return await test_http(proxy)
        elif proto == "https":
            return await test_https(proxy)
        elif proto == "socks4":
            return await test_socks(proxy, 4)
        elif proto == "socks5":
            return await test_socks(proxy, 5)
        return False

    async def validate_one(proto, proxy):
        async with semaphore:
            for attempt in range(3):  # First try + 2 retries
                ok = await try_validate(proto, proxy)
                if ok:
                    results[proto].append(proxy)
                    print(f"{Fore.GREEN}[VALID] {proto.upper()} - {proxy} (try {attempt+1})")
                    return
            print(f"{Fore.RED}[DEAD ] {proto.upper()} - {proxy} (after 3 tries)")

    tasks = []
    for proto, proxies in proxies_by_type.items():
        for proxy in proxies:
            tasks.append(validate_one(proto, proxy))

    await asyncio.gather(*tasks)

    for proto, valid_list in results.items():
        async with aiofiles.open(f"working_{proto}.txt", 'w') as f:
            await f.write("\n".join(valid_list))

    return results


async def main():
    print(f"{Fore.MAGENTA}[+] Starting full proxy pipeline...")
    proxies_by_type = await download_all()
    await validate_all(proxies_by_type)


if __name__ == "__main__":
    asyncio.run(main())
