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


stats = {"done": 0, "failed": 0}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; BotyPodleNohy/1.0; +https://www.bosorka.cz)"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            err = e
            time.sleep(2)
    stats["failed"] += 1
    if stats["failed"] <= 5:
        print(f"nepodařilo se stáhnout {url}: {err}", flush=True)
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
    stats["done"] += 1
    if stats["done"] % 250 == 0:
        print(f"  {stats['done']} stránek, chyb {stats['failed']}", flush=True)
    if stats["done"] >= 100 and stats["failed"] > stats["done"] / 2:
        raise SystemExit("Většina stránek se nedá stáhnout – e-shop nás asi blokuje.")
    return product_from_html(url, h) if h else None


def main(out_dir):
    urls = candidate_urls()
    print(f"stránek ke kontrole: {len(urls)}", flush=True)
    with ThreadPoolExecutor(PARALLEL) as pool:
        products = [p for p in pool.map(fetch_product, urls) if p]
    print(f"bot nalezeno: {len(products)}")
    if len(products) < MIN_PRODUCTS:
        sys.exit(f"Načetlo se jen {len(products)} bot – data nepřepisuji.")
    write_outputs(products, out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site")
