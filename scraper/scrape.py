"""Projde e-shop podle sitemapy, stáhne stránky produktů a vytvoří data pro vyhledávač.

Použití: python3 scrape.py <výstupní složka>
Spouští se jednou denně přes GitHub Actions (.github/workflows/aktualizace.yml).
"""
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from build_data import product_from_html, write_outputs

SHOP = "https://www.bosorka.cz"
# první část adresy, kde určitě nejsou boty (značky, blog…) – ušetří zbytečné stahování
SKIP = {"znacka", "slovnik-pojmu", "nase-novinky-blog", "blog-2", "blog"}
PARALLEL = 3          # kolik stránek najednou
PAUSE = 0.3           # pauza po každé stránce (s), ať e-shop nezatěžujeme
MIN_PRODUCTS = 1000   # pojistka: když se načte méně bot, něco je špatně a data nepřepisujeme


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BotyPodleNohy/1.0 (+bosorka.cz)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def candidate_urls():
    xml = get(SHOP + "/sitemap.xml") or ""
    urls = []
    for u in re.findall(r"<loc>([^<]+)</loc>", xml):
        parts = [p for p in urlparse(u).path.split("/") if p]
        if len(parts) == 2 and parts[0] not in SKIP:
            urls.append(u)
    return sorted(set(urls))


def fetch_product(url):
    h = get(url)
    time.sleep(PAUSE)
    return product_from_html(url, h) if h else None


def main(out_dir):
    urls = candidate_urls()
    print(f"stránek ke kontrole: {len(urls)}")
    with ThreadPoolExecutor(PARALLEL) as pool:
        products = [p for p in pool.map(fetch_product, urls) if p]
    print(f"bot nalezeno: {len(products)}")
    if len(products) < MIN_PRODUCTS:
        sys.exit(f"Načetlo se jen {len(products)} bot – data nepřepisuji.")
    write_outputs(products, out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site")
