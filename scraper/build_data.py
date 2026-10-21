"""Ze stránek produktů vytvoří boty.json pro vyhledávač bot podle nohy.

Každý produkt: název, url, obrázek, cena, druh bot, šířka nohy (parametr),
velikosti skladem a velikostní tabulka {velikost: {len, wid, foot}}.
Boty bez tabulky se vypíšou do boty-bez-dat.csv ke kontrole.
"""
import csv
import html as htmllib
import json
import re
import sys
from pathlib import Path

from parse_sizes import parse_description


def meta(h, prop):
    m = re.search(rf'<meta property="{prop}" content="([^"]*)"', h)
    return htmllib.unescape(m.group(1)) if m else ""


def description(h):
    m = re.search(r'id="description".*?(?=id="(?:productDiscussion|ratingTab|relatedFiles|productsRelated)"|<footer)', h, re.S)
    return m.group(0) if m else ""


def foot_width_param(h):
    m = re.search(r"Šířka nohy<span[^>]*>:</span>.*?<td[^>]*>(.*?)</td>", h, re.S)
    if not m:
        return []
    txt = re.sub(r"<[^>]+>", " ", m.group(1))
    return [w.strip() for w in re.split(r",", htmllib.unescape(txt)) if w.strip()]


def sizes_in_stock(h):
    """Velikosti z výběru varianty, které nejsou vyprodané. None = produkt bez variant."""
    sel = re.search(r'<select[^>]*data-parameter-name="Velikost"[^>]*>(.*?)</select>', h, re.S)
    if not sel:
        return None
    pid = re.search(r'data-parameter-id="(\d+)"', h[sel.start():sel.start() + 400]).group(1)
    opts = re.findall(r'<option value="(\d+)"[^>]*>([^<]+)</option>', sel.group(1))
    data = {}
    m = re.search(r"necessaryVariantData = (\{.*?\});\s*\n", h, re.S)
    if m:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    out = []
    for vid, label in opts:
        v = data.get(f"{pid}-{vid}")
        if v is None or v.get("isNotSoldOut"):
            out.append(htmllib.unescape(label).strip())
    return out


KINDS = [  # (druh bot, klíčová slova v názvu/kategorii) – první shoda vyhrává
    ("Sandály", r"sandál|páskov"),
    ("Baleríny", r"balerín"),
    ("Bačkory a přezůvky", r"bačkor|přezůvk|papuč"),
    ("Holínky", r"holín|gumák"),
    ("Zimní boty", r"zimní|sněhul|snehul"),
    ("Kotníkové boty", r"kotník|kotnič|outdoor"),
    ("Tenisky a polobotky", r"tenisk|polobot|slip-on|mokasín"),
    ("Capáčky / první krůčky", r"capáč|první krůčky|prewalk"),
]


def shoe_kind(text):
    for kind, rx in KINDS:
        if re.search(rx, text):
            return kind
    return "Celoroční a ostatní"


def size_range(sizes):
    nums = [float(m.group()) for s in sizes for m in [re.match(r"\d+(?:\.\d)?", s)] if m]
    return (min(nums), max(nums)) if nums else (None, None)


def who_for(text, sizes):
    """Vrátí (pro děti, pro dospělé). Bota může být v obou (např. velikosti 30–40)."""
    kid_hint = re.search(r"dětsk|kids|junior|baby|první krůčky|capáč", text)
    adult_hint = re.search(r"dámsk|pánsk|women|\bmen|dospěl", text)
    lo, hi = size_range(sizes)
    kids = bool(kid_hint) or (not adult_hint and lo is not None and lo < 30)
    adult = bool(adult_hint) or (not kid_hint and hi is not None and hi >= 36)
    if not kids and not adult:
        kids = hi is not None and hi < 36
        adult = not kids
    return kids, adult


def norm_size(s):
    """'EU 25' -> '25', '21/22' -> '21-22', '25,5' -> '25.5'."""
    s = s.upper().replace("EU", "").replace(" ", "").replace("/", "-").replace(",", ".")
    return s


def product_from_html(url, h):
    """Z HTML stránky produktu udělá záznam pro vyhledávač. None = není to bota."""
    crumbs = [htmllib.unescape(c).strip() for c in
              re.findall(r'breadcrumbsSecondLevel"><span itemprop="name">([^<]+)<', h)]
    if not crumbs or crumbs[0] != "Barefoot obuv":
        return None
    t = re.search(r'itemprop="name" data-title="([^"]+)"', h)
    name = htmllib.unescape(t.group(1)).strip() if t else re.sub(r"\s*[-|]\s*Bosorka Plzeň$", "", meta(h, "og:title"))
    path = " / ".join(crumbs).lower()
    table = parse_description(description(h))
    stock = sizes_in_stock(h)
    price = re.search(r'"priceUnformatted":([\d.]+)', h)
    img = re.search(r'"detail_small":"([^"]+)"', h)
    prod = {
        "name": name,
        "url": url,
        "img": img.group(1).replace("\\/", "/") if img else meta(h, "og:image"),
        "price": float(price.group(1)) if price else None,
        "cat": shoe_kind(name.lower() + " " + path),
        "open": bool(re.search(r"sandál|balerín|páskov", name.lower() + " " + path)),
        "widthCat": foot_width_param(h),
        "stock": [norm_size(s) for s in stock] if stock is not None else None,
        "sizes": {norm_size(k): v for k, v in table.items()},
    }
    prod["kids"], prod["adult"] = who_for(name.lower() + " " + path, list(prod["sizes"]) + (prod["stock"] or []))
    return prod


def write_outputs(products, out_dir):
    """Uloží boty.json pro vyhledávač a boty-bez-dat.csv s botami, kterým chybí tabulka."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    products.sort(key=lambda p: p["url"])
    (out_dir / "boty.json").write_text(json.dumps(products, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    has = lambda p, k: any(v.get(k) for v in p["sizes"].values())
    rows = []
    for p in products:
        pro = "obojí" if p["kids"] and p["adult"] else "dětské" if p["kids"] else "dospělé"
        if not has(p, "len") and not has(p, "foot"):
            rows.append([pro, "chybí délka", p["name"], p["url"]])
        elif p["kids"] and has(p, "len") and not has(p, "wid"):
            rows.append([pro, "chybí šířka (dětská bota)", p["name"], p["url"]])
    rows.sort()
    with open(out_dir / "boty-bez-dat.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Pro", "Problém", "Název", "Odkaz"])
        w.writerows(rows)

    for group in ("kids", "adult"):
        ps = [p for p in products if p[group]]
        print(f"{group}: {len(ps)} bot, délka {sum(has(p, 'len') or has(p, 'foot') for p in ps)}, "
              f"šířka {sum(has(p, 'wid') for p in ps)}")


def main(pages_dir, idx_file, out_dir):
    """Lokální běh nad už staženými stránkami: soubor idx má řádky "číslo url"."""
    products = []
    for line in Path(idx_file).read_text().splitlines():
        i, url = line.split(" ", 1)
        p = Path(pages_dir) / f"{i}.html"
        if p.exists():
            prod = product_from_html(url, p.read_text(encoding="utf-8", errors="ignore"))
            if prod:
                products.append(prod)
    write_outputs(products, out_dir)


if __name__ == "__main__":
    main(*sys.argv[1:4])
