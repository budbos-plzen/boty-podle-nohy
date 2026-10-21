/* Vyhledávač bot podle nohy – Bosorka.
 * Na stránce e-shopu stačí <div id="bpn-root"></div> a tento skript.
 * Data (boty.json) se denně aktualizují přes GitHub Actions.
 */
(function () {
  var CSS = "/* Vše je pod #bpn, aby se styl nepral se šablonou Shoptetu. */\n  #bpn { --c-text: #2b2b2b; --c-muted: #6b6b6b; --c-line: #e4e0da; --c-accent: #7a5c3e; --c-ok: #3f7a4a; --c-bg2: #faf7f3;\n         color: var(--c-text); max-width: 1100px; margin: 0 auto; padding: 24px 16px; box-sizing: border-box; }\n  #bpn * { box-sizing: border-box; }\n  #bpn h2 { margin: 0 0 4px; font-size: 26px; }\n  #bpn .lead { margin: 0 0 20px; color: var(--c-muted); }\n  #bpn form { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); align-items: end;\n              background: var(--c-bg2); border: 1px solid var(--c-line); border-radius: 12px; padding: 18px; }\n  #bpn label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 6px; }\n  #bpn input[type=number], #bpn select { width: 100%; font: inherit; padding: 10px 12px; border: 1px solid #cfc8bf; border-radius: 8px; background: #fff; }\n  #bpn .seg { display: flex; border: 1px solid #cfc8bf; border-radius: 8px; overflow: hidden; }\n  #bpn .seg button { flex: 1; font: inherit; padding: 10px; border: 0; background: #fff; cursor: pointer; }\n  #bpn .seg button[aria-pressed=true] { background: var(--c-accent); color: #fff; }\n  #bpn .chk { display: flex; gap: 8px; align-items: center; font-weight: 400; margin: 0; padding: 10px 0; }\n  #bpn .hint { font-size: 13px; color: var(--c-muted); margin-top: 4px; }\n  #bpn .summary { margin: 22px 0 12px; font-size: 15px; }\n  #bpn .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }\n  #bpn .card { border: 1px solid var(--c-line); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column;\n               text-decoration: none; color: inherit; background: #fff; transition: box-shadow .15s; }\n  #bpn .card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); }\n  #bpn .card img { width: 100%; aspect-ratio: 4/3; object-fit: contain; background: #fff; }\n  #bpn .card .b { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 6px; flex: 1; }\n  #bpn .card .n { font-size: 14px; line-height: 1.35; }\n  #bpn .card .p { font-weight: 700; }\n  #bpn .size { display: inline-block; background: var(--c-ok); color: #fff; border-radius: 6px; padding: 3px 8px; font-weight: 700; font-size: 14px; }\n  #bpn .size.alt { background: #fff; color: var(--c-ok); border: 1px solid var(--c-ok); }\n  #bpn .meta { font-size: 12px; color: var(--c-muted); }\n  #bpn .sec { margin: 32px 0 6px; font-size: 18px; }\n  #bpn .empty { padding: 24px; text-align: center; color: var(--c-muted); border: 1px dashed var(--c-line); border-radius: 12px; }\n  #bpn .more { display: block; margin: 18px auto 0; font: inherit; padding: 10px 18px; border-radius: 8px; border: 1px solid var(--c-accent);\n               background: #fff; color: var(--c-accent); cursor: pointer; }\n";
  var HTML = "\n  <h2>Najděte boty podle nohy</h2>\n  <p class=\"lead\">Změřte délku chodidla (od paty po nejdelší prst) a u dětí i šířku v nejširším místě. Ukážeme boty se správnou rezervou.</p>\n\n  <form id=\"bpn-form\" onsubmit=\"return false\">\n    <div>\n      <label>Pro koho</label>\n      <div class=\"seg\" id=\"bpn-who\">\n        <button type=\"button\" data-v=\"kids\" aria-pressed=\"true\">Dítě</button>\n        <button type=\"button\" data-v=\"adult\" aria-pressed=\"false\">Dospělý</button>\n      </div>\n    </div>\n    <div>\n      <label for=\"bpn-len\">Délka chodidla (mm)</label>\n      <input id=\"bpn-len\" type=\"number\" inputmode=\"numeric\" min=\"80\" max=\"330\" placeholder=\"např. 165\">\n    </div>\n    <div id=\"bpn-wid-wrap\">\n      <label for=\"bpn-wid\">Šířka chodidla (mm)</label>\n      <input id=\"bpn-wid\" type=\"number\" inputmode=\"numeric\" min=\"40\" max=\"130\" placeholder=\"např. 68\">\n    </div>\n    <div>\n      <label for=\"bpn-cat\">Druh bot</label>\n      <select id=\"bpn-cat\"><option value=\"\">Všechny</option></select>\n    </div>\n    <div>\n      <label class=\"chk\"><input type=\"checkbox\" id=\"bpn-stock\" checked> Jen skladem</label>\n    </div>\n  </form>\n\n  <div id=\"bpn-out\"></div>";

  // ===== Nastavení rezerv (mm) =====
  var RULES = {
    kids:  { closed: { len: [6, 12] }, open: { len: [6, 12] }, wid: [1, 4] },  // open = sandály a baleríny
    adult: { closed: { len: [6, 12] }, open: { len: [4, 8] } }
  };
  // data leží vedle tohoto skriptu (GitHub Pages)
  var DATA_URL = (document.currentScript ? document.currentScript.src.replace(/[^/]*$/, "") : "") + "boty.json";
  var PAGE = 24;

  var root = document.getElementById("bpn-root");
  if (!root) return;  // na ostatních stránkách e-shopu nic nedělej
  var style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);
  root.innerHTML = '<div id="bpn">' + HTML + "</div>";

  var $ = function (id) { return document.getElementById(id); };
  var who = "kids", products = [], shown = PAGE;

  function inStock(p, size) {
    if (!p.stock) return true;                       // produkt bez variant velikosti
    if (p.stock.indexOf(size) >= 0) return true;
    var r = size.split("-");                         // tabulka "21-22", varianta "21" apod.
    return r.length === 2 && p.stock.some(function (s) { return s === r[0] || s === r[1]; });
  }

  function evaluate(p, footLen, footWid, onlyStock) {
    var rule = RULES[who], lr = rule[p.open ? "open" : "closed"].len, best = null, widUnknown = false;
    Object.keys(p.sizes).forEach(function (size) {
      var s = p.sizes[size];
      if (!s.len || s.suspicious) return;
      var lm = s.len - footLen;
      if (lm < lr[0] || lm > lr[1]) return;
      if (onlyStock && !inStock(p, size)) return;
      var wm = null;
      if (who === "kids" && footWid) {
        if (s.wid) {
          wm = s.wid - footWid;
          if (wm < rule.wid[0] || wm > rule.wid[1]) return;
        } else {
          widUnknown = true;
        }
      }
      // z vyhovujících velikostí ber tu nejblíž středu rozmezí
      var score = Math.abs(lm - (lr[0] + lr[1]) / 2);
      if (!best || score < best.score) best = { size: size, len: s.len, wid: s.wid, lm: lm, wm: wm, score: score };
    });
    if (!best) best = byFootLength(p, footLen, onlyStock);
    if (best) best.widUnknown = !!(who === "kids" && footWid && best.wm === null);
    return best;
  }

  // Výrobce uvádí jen „délku chodidla do X mm“ (rezerva je už v ní): nejmenší velikost, do které noha padne.
  function byFootLength(p, footLen, onlyStock) {
    var best = null;
    Object.keys(p.sizes).forEach(function (size) {
      var s = p.sizes[size];
      if (s.len || !s.foot || footLen > s.foot) return;
      if (!best || s.foot < best.foot) best = { size: size, foot: s.foot, wm: null, score: 50 + s.foot - footLen };
    });
    // jen ta jedna správná velikost; když není skladem, větší nenabízíme
    if (!best || best.foot - footLen > 10 || (onlyStock && !inStock(p, best.size))) return null;
    return best;
  }

  function card(p, m) {
    var price = p.price ? Math.round(p.price).toLocaleString("cs-CZ") + " Kč" : "";
    var dims = m.foot ? "pro chodidlo do " + m.foot + " mm (dle výrobce)" : "vnitřní délka " + m.len + " mm (+" + m.lm + ")";
    if (m.wid) dims += ", šířka " + m.wid + " mm" + (m.wm !== null ? " (+" + m.wm + ")" : "");
    var extra = m.widUnknown && p.widthCat.length ? '<span class="meta">Šířka v mm neuvedena · ' + p.widthCat.join(", ") + '</span>' : "";
    return '<a class="card" href="' + esc(p.url) + '">' +
      '<img loading="lazy" src="' + esc(p.img) + '" alt="">' +
      '<div class="b"><span class="n">' + esc(p.name) + '</span>' +
      '<span><span class="size' + (m.widUnknown ? " alt" : "") + '">Velikost ' + m.size + '</span></span>' +
      '<span class="meta">' + dims + '</span>' + extra +
      '<span class="p">' + price + '</span></div></a>';
  }

  function render() {
    var footLen = +$("bpn-len").value, footWid = who === "kids" ? +$("bpn-wid").value : 0;
    var cat = $("bpn-cat").value, onlyStock = $("bpn-stock").checked, out = $("bpn-out");
    if (!footLen) { out.innerHTML = ""; return; }

    var exact = [], approx = [];
    products.forEach(function (p) {
      if (!p[who]) return;
      if (cat && p.cat !== cat) return;
      var m = evaluate(p, footLen, footWid, onlyStock);
      if (!m) return;
      (m.widUnknown ? approx : exact).push([p, m]);
    });
    var byFit = function (a, b) { return a[1].score - b[1].score; };
    exact.sort(byFit); approx.sort(byFit);

    var html = '<p class="summary"><b>' + exact.length + '</b> ' + plural(exact.length) + ' sedí' +
      (who === "kids" && footWid ? " na délku i šířku" : " na délku") + ".</p>";
    html += exact.length ? '<div class="grid">' + exact.slice(0, shown).map(function (x) { return card(x[0], x[1]); }).join("") + "</div>"
                         : '<div class="empty">Žádná bota s touto rezervou. Zkuste jiný druh bot nebo vypněte „Jen skladem“.</div>';
    if (exact.length > shown) html += '<button class="more" id="bpn-more">Zobrazit další</button>';
    if (approx.length) {
      html += '<h3 class="sec">Sedí na délku, šířku výrobce neuvádí (' + approx.length + ')</h3>' +
              '<p class="hint">Orientačně podle naší kategorie šířky nohy.</p>' +
              '<div class="grid">' + approx.slice(0, PAGE).map(function (x) { return card(x[0], x[1]); }).join("") + "</div>";
    }
    out.innerHTML = html;
    var more = $("bpn-more");
    if (more) more.onclick = function () { shown += PAGE; render(); };
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function plural(n) { return n === 1 ? "bota" : n >= 2 && n <= 4 ? "boty" : "bot"; }

  function fillCats() {
    var cats = {};
    products.forEach(function (p) { if (p[who] && p.cat) cats[p.cat] = 1; });
    var sel = $("bpn-cat"), cur = sel.value;
    sel.innerHTML = '<option value="">Všechny</option>' + Object.keys(cats).sort().map(function (c) {
      return '<option' + (c === cur ? " selected" : "") + ">" + c + "</option>";
    }).join("");
  }

  Array.prototype.forEach.call($("bpn-who").children, function (b) {
    b.onclick = function () {
      who = b.dataset.v;
      Array.prototype.forEach.call($("bpn-who").children, function (x) { x.setAttribute("aria-pressed", x === b); });
      $("bpn-wid-wrap").style.display = who === "kids" ? "" : "none";
      fillCats(); shown = PAGE; render();
    };
  });
  ["bpn-len", "bpn-wid", "bpn-cat", "bpn-stock"].forEach(function (id) {
    $(id).addEventListener("input", function () { shown = PAGE; render(); });
  });

  fetch(DATA_URL).then(function (r) { return r.json(); }).then(function (d) { products = d; fillCats(); render(); });
})();
