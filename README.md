# Boty podle nohy – Bosorka

Vyhledávač bot podle naměřené délky (a u dětí šířky) chodidla.

- `scraper/` – každou noc projde bosorka.cz, z velikostních tabulek v popisech vytáhne
  vnitřní délku/šířku pro každou velikost a uloží `boty.json`.
- `site/widget.js` – samotný vyhledávač, vkládá se do Shoptetu.
- `site/boty-bez-dat.csv` – boty, u kterých se tabulku nepodařilo přečíst (ke kontrole).
- `.github/workflows/aktualizace.yml` – denní spuštění a zveřejnění na GitHub Pages.

## Rezervy

Nastavují se na začátku `site/widget.js` (`RULES`):

| | délka | šířka |
|---|---|---|
| dětské (i sandály, baleríny) | 6–12 mm | 1–4 mm |
| dospělé | 6–12 mm | – |
| dospělé sandály, baleríny | 4–8 mm | – |

Když výrobce uvádí místo vnitřní délky „délku chodidla“ (rezerva je v ní už
započítaná), nabídne se nejmenší velikost, do které noha padne.

## Vložení do Shoptetu

1. **Vzhled a obsah → Editor → HTML kód → Zápatí** vložit:
   `<script src="https://UZIVATEL.github.io/boty-podle-nohy/widget.js" defer></script>`
2. Na stránku, kde má vyhledávač být, vložit v zobrazení zdrojového kódu:
   `<div id="bpn-root">Načítám vyhledávač…</div>`

Ruční aktualizace dat: na GitHubu **Actions → Aktualizace dat → Run workflow**.
