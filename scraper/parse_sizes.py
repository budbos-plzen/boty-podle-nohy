"""Vytáhne z HTML popisu produktu velikostní tabulku: {velikost: {"len": mm, "wid": mm}}.

len = vnitřní délka boty, wid = vnitřní šířka boty (obě v mm).
Zvládá tabulky naležato i nastojato, tabulky rozdělené do více bloků,
sloučené buňky oddělené <br> a hodnoty v cm.
"""
import re
from html.parser import HTMLParser

SEP = " ¦ "  # náhrada za <br> uvnitř buňky


class TableGrabber(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif not self._stack:
            return
        elif tag == "tr":
            self._stack[-1].append([])
        elif tag in ("td", "th"):
            if not self._stack[-1]:
                self._stack[-1].append([])
            self._stack[-1][-1].append("")
        elif tag in ("br", "p", "div") and self._stack[-1] and self._stack[-1][-1]:
            self._stack[-1][-1][-1] += SEP

    def handle_endtag(self, tag):
        if tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._stack and self._stack[-1] and self._stack[-1][-1]:
            self._stack[-1][-1][-1] += data


def clean(s):
    s = re.sub(r"\s+", " ", s.replace("\xa0", " "))
    parts = [p.strip() for p in s.split(SEP.strip())]
    return SEP.join(p for p in parts if p)


def parts(s):
    return [p for p in s.split(SEP) if p]


def num(s):
    m = re.search(r"\d+(?:\s?[.,]\s?\d+)?", s)
    return float(re.sub(r"\s", "", m.group()).replace(",", ".")) if m else None


def label_kind(s):
    """Co je v řádku/sloupci: size, len, wid, len+wid, nebo None (ignorovat)."""
    s = s.lower()
    if not s:
        return None
    if ("šíř" in s or "šir" in s) and "obvod" in s and "v obvodu" not in s and "v opk" not in s:
        return "skip"
    if ("obvod" in s and "šíř" not in s) or "věk" in s or "hmotnost" in s or "výšk" in s:
        return "skip"  # obvod, věk… nechceme
    if re.search(r"(délk|delk|length).*(nohy|chodidl|foot)|(nohy|chodidl|foot).*(délk|length)", s):
        return "foot"  # výrobce uvádí délku chodidla, pro kterou je velikost (rezerva už započtena)
    if "nohy" in s or "chodidl" in s:
        return "skip"
    has_len = bool(re.search(r"délk|delk|length|stélk", s))
    has_wid = bool(re.search(r"šíř|šir|sirk|width", s))
    if has_len and has_wid:
        return "len+wid"
    if has_len:
        return "len"
    if has_wid:
        return "wid"
    if re.search(r"velikost|^eu\b|^vel\.?$|size", s):
        return "size"
    if re.fullmatch(r"cm|mm", s):
        return "len"  # Vivobarefoot: řádek "CM" = délka stélky
    return None


def to_mm(v, unit_hint=None):
    if v is None:
        return None
    if unit_hint == "cm" or v < 40:  # i když je napsáno (mm), 11,3 jsou centimetry  # 16,4 (cm) -> 164 mm
        return round(v * 10)
    return round(v)


def unit_of(s):
    s = s.lower()
    if re.search(r"\bcm\b", s):
        return "cm"
    if "mm" in s:
        return "mm"
    return None


def looks_like_size(s):
    return bool(re.fullmatch(r"(EU\s*)?\d{2}(?:[.,]5)?(?:\s*[-/]\s*\d{2})?|[SMLX]{1,3}\+?|\d?XL|\d+XL", s.strip()))


def transpose_horizontal(rows):
    """Tabulku naležato (popisky v 1. sloupci) převede na nastojato.
    Rozdělené tabulky (další blok bez popisků) poskládá za sebe."""
    kinds = [label_kind(r[0]) for r in rows]
    # první blok: od řádku s velikostmi po další řádek s velikostmi / bez popisku
    blocks, cur = [], None
    for r, k in zip(rows, kinds):
        is_size_row = k == "size" or (not r[0] and sum(looks_like_size(c) for c in r[1:]) >= 2)
        block_has_data = cur is not None and any(label_kind(lab) in ("len", "wid", "len+wid", "foot") or not lab for lab, _ in cur["rows"])
        if is_size_row and (cur is None or block_has_data):
            cur = {"sizes": r[1:], "rows": []}
            blocks.append(cur)
        elif cur is not None:
            cur["rows"].append((r[0], r[1:]))
    if not blocks:
        return None
    labels = [lab for lab, _ in blocks[0]["rows"]]
    header = ["Velikost"] + labels
    out = [header]
    for b in blocks:
        for col, size in enumerate(b["sizes"]):
            if not size:
                continue
            line = [size]
            for idx in range(len(labels)):
                vals = b["rows"][idx][1] if idx < len(b["rows"]) else []
                line.append(vals[col] if col < len(vals) else "")
            out.append(line)
    return out


def parse_grid(rows):
    rows = [[clean(c) for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    # zahoď nadpisový řádek s jedinou buňkou ("Velikostní tabulka …")
    while rows and len([c for c in rows[0] if c]) == 1 and len(rows) > 1 and len(rows[1]) > 2:
        rows = rows[1:]
    if len(rows) < 2:
        return None

    first_col = [label_kind(r[0]) for r in rows]
    horizontal = (
        any(k in ("len", "wid", "len+wid", "foot") for k in first_col)
        and (first_col[0] == "size" or (not rows[0][0] and sum(looks_like_size(c) for c in rows[0][1:]) >= 2))
    )
    if horizontal:
        rows = transpose_horizontal(rows)
        if not rows:
            return None

    # najdi řádek hlavičky (nastojato)
    hi = next((i for i, r in enumerate(rows[:3]) if any(label_kind(c) in ("len", "wid", "len+wid", "foot") for c in r)), None)
    if hi is None:
        return None
    head = rows[hi]
    kinds = [label_kind(c) for c in head]
    if "size" not in kinds:
        if not head[0]:
            kinds[0] = "size"
        else:
            return None
    units = [unit_of(c) for c in head]
    si = kinds.index("size")

    result = {}
    for r in rows[hi + 1:]:
        if len(r) <= si or not looks_like_size(r[si]):
            continue
        cells = [c for c in r]
        # buňky odsazené prázdnými sloupci (Protetika: "37 | | 23,5 | | 9,0")
        if len(cells) == len(head):
            pairs = list(zip(kinds, cells, units))
        else:
            pairs = list(zip(kinds, cells, units))
        entry = {}
        unlabeled = []
        for kind, val, unit in pairs:
            unit = unit or unit_of(val)
            if kind in ("len", "wid") and num(val) is not None and kind not in entry:
                entry[kind] = to_mm(num(val), unit)
            elif kind == "foot" and "foot" not in entry:
                nums = re.findall(r"\d+(?:[.,]\d+)?", val)
                if nums:  # rozsah "123-132" -> horní mez
                    entry["foot"] = to_mm(float(nums[-1].replace(",", ".")), unit)
            elif kind == "len+wid":
                p = parts(val)
                if len(p) == 2:
                    entry["len"], entry["wid"] = to_mm(num(p[0]), unit), to_mm(num(p[1]), unit)
            elif kind is None and num(val) is not None:
                unlabeled.append(to_mm(num(val), unit))
        # nepopsaný sloupec za délkou, který je výrazně menší → šířka (Koel: "12,3 | 6,6 cm")
        if "len" in entry and "wid" not in entry and len(unlabeled) == 1:
            w = unlabeled[0]
            if 0.3 < w / entry["len"] < 0.6:
                entry["wid"] = w
        if entry.get("len") or entry.get("wid") or entry.get("foot"):
            result[r[si]] = entry
    return result or None


def parse_description(html):
    g = TableGrabber()
    g.feed(html)
    out = {}
    for t in g.tables:
        parsed = parse_grid(t)
        if parsed:
            out.update(parsed)
    # sanity: šířka musí dávat smysl vůči délce
    for size, e in list(out.items()):
        if e.get("len") and e.get("wid") and not (0.3 < e["wid"] / e["len"] < 0.6):
            e["suspicious"] = True
    return out
