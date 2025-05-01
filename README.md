🛠️ 1. Tool Features

  ✅ Downloads proxies from hardcoded GitHub raw .txt URLs

  ✅ Groups proxies by type: http, https, socks4, socks5

  ✅ Combines and deduplicates proxies into type-specific files

  ✅ Validates each proxy with up to 3 tries (1 original + 2 retries)

  ✅ Asynchronously tests proxies using up to 100 concurrent threads

  ✅ Saves working proxies in separate working_*.txt files

  ✅ Uses colored output for valid/dead proxies

📦 2. Install Required Python Libraries

You need the following dependencies:
✅ Create requirements.txt

aiohttp
aiofiles
aiohttp_socks
colorama

✅ Install with pip

pip install -r requirements.txt

Or directly:

pip install aiohttp aiofiles aiohttp_socks colorama

📂 3. Folder Structure

Your project folder should look like this:

proxy_pipeline/
├── proxy_tool.py
├── requirements.txt
└── proxy_tmp/               # This folder is auto-created for scratch space

🚀 4. How to Run the Tool

Simply run:

python3 proxy_tool.py

The tool does everything in one go:

  Downloads proxies by type.

   Combines and deduplicates into:

        http_combined.txt

        https_combined.txt

        socks4_combined.txt

        socks5_combined.txt

  Validates each proxy:

  Up to 3 tries per proxy

  Colored console output

  Saves results into:

        working_http.txt

        working_https.txt

        working_socks4.txt

        working_socks5.txt

📁 5. Output Example

http_combined.txt         ← All unique HTTP proxies combined
https_combined.txt        ← All unique HTTPS proxies
socks4_combined.txt       ← All unique SOCKS4 proxies
socks5_combined.txt       ← All unique SOCKS5 proxies

working_http.txt          ← Valid HTTP proxies after test
working_https.txt         ← Valid HTTPS proxies after test
working_socks4.txt        ← Valid SOCKS4 proxies after test
working_socks5.txt        ← Valid SOCKS5 proxies after test

🧼 6. Optional Cleanup

To clear previous results before running again:

rm *_combined.txt working_*.txt

🧪 7. Optional: Test Your Installation
