#!/usr/bin/env python3
"""公開中ページ一覧 — repo 内の index.html を走査して一覧 JSON（と任意で HTML）を作る。

usage: public_pages.py [--json OUT.json] [--html OUT.html] [--urlmanager PATH]

正本はファイルそのもの（この一覧は生成物。手で編集しない）。
- 1 行 = 日本語ページ 1 枚。英語版（en/<path>/index.html または <path>/en/...）は同じ行の列に出す
- 日付は本文の「制定／改定／最終更新」表記を正規表現で拾う（無ければ空）
- 最終更新は git log の日付
- アプリ参照は motitan_app の URLManager.cs に URL が書かれているか
"""
import argparse, html, json, os, re, subprocess, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://motitown.com/notification"
SKIP_DIRS = {".git", "node_modules", "tmp", "scripts", "sql", "assets", ".claude"}
CATEGORY = [
    (re.compile(r"^\d+$"), "お知らせ（新）"),
    (re.compile(r"^Notification$"), "お知らせ（旧）"),
    (re.compile(r"^Alert$"), "アラート"),
    (re.compile(r"^information$"), "使い方・説明"),
    (re.compile(r"^document$"), "法務文書"),
    (re.compile(r"^event$"), "イベント"),
    (re.compile(r"^recommend$"), "相互紹介"),
    (re.compile(r"^store$"), "ストア"),
    (re.compile(r"^be-delivery$"), "BE 配信"),
    (re.compile(r"^faq$"), "FAQ"),
    (re.compile(r"^manual$"), "マニュアル"),
]
DATE_RE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*(制定|改定|改訂|施行|最終更新|更新)")
DATE_EN_RE = re.compile(r"\[(Established|Revised|Last updated)\s+([A-Z][a-z]+ \d{1,2}, \d{4})\]")


def category_of(path):
    top = path.split("/")[0] if path else ""
    if not top:
        return "トップ"
    for rx, name in CATEGORY:
        if rx.match(top):
            return name
    return top


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def title_of(src):
    m = re.search(r"<title>(.*?)</title>", src, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def dates_of(src):
    text = re.sub(r"<[^>]+>", " ", src)
    found = [f"{y}-{int(mo):02d}-{int(d):02d} {kind}" for y, mo, d, kind in DATE_RE.findall(text)]
    found += [f"{d} ({k})" for k, d in DATE_EN_RE.findall(text)]
    # 重複を保ったまま順序維持で一意化
    seen, out = set(), []
    for x in found:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def git_date(relpath):
    try:
        out = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%as", "--", relpath], capture_output=True, text=True, check=True).stdout.strip()
        return out
    except Exception:
        return ""


def app_urls(urlmanager):
    if not urlmanager or not os.path.exists(urlmanager):
        return set()
    src = read(urlmanager)
    return {u.rstrip("/") for u in re.findall(r"https://motitown\.com/notification[^\"'\s]*", src)}


def en_kind(src):
    """英語ページの種類: 'en'=英語本文 / 'redirect'=日本語へ転送 / 'ja'=日本語のまま"""
    if re.search(r'http-equiv=["\']refresh["\']|location\.replace|location\.href', src, re.I):
        return "redirect"
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", src, flags=re.S)
    jp = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", body)); en = len(re.findall(r"[A-Za-z]", body))
    return "en" if en > jp * 3 else "ja"


def is_en_path(path):
    parts = path.split("/")
    return parts[0] == "en" or "en" in parts[1:]


def ja_path_of_en(path):
    parts = path.split("/")
    if parts[0] == "en":
        return "/".join(parts[1:])
    return "/".join(p for p in parts if p != "en")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--html")
    ap.add_argument("--urlmanager", default=os.path.expanduser("~/motitown/motitan_app/Assets/Motitan/Scripts/Core/Api/URLManager.cs"))
    a = ap.parse_args()

    pages = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        pages[rel] = os.path.join(dirpath, "index.html")

    refs = app_urls(a.urlmanager)
    rows = []
    en_only = []
    for rel, fpath in sorted(pages.items()):
        if is_en_path(rel):
            continue
        src = read(fpath)
        en_rel = f"en/{rel}" if rel else "en"
        en_exists = en_rel in pages
        if not en_exists:
            # be-delivery/monthly-rewards/en/odd-months のような内側の en/
            parts = rel.split("/")
            for i in range(1, len(parts) + 1):
                cand = "/".join(parts[:i] + ["en"] + parts[i:])
                if cand in pages:
                    en_rel, en_exists = cand, True
                    break
        url = f"{SITE}/{rel}/" if rel else f"{SITE}/"
        rows.append({
            "path": rel,
            "category": category_of(rel),
            "title": title_of(src),
            "url": url,
            "en_url": (f"{SITE}/{en_rel}/" if en_exists else ""),
            "en_kind": (en_kind(read(pages[en_rel])) if en_exists else ""),
            "dates": dates_of(src),
            "en_dates": dates_of(read(pages[en_rel])) if en_exists else [],
            "updated": git_date(os.path.relpath(fpath, ROOT)),
            "en_updated": git_date(os.path.relpath(pages[en_rel], ROOT)) if en_exists else "",
            "noindex": 'name="robots"' in src and "noindex" in src,
            "app_ref": url.rstrip("/") in refs,
            "github": f"https://github.com/astran-jp/motitown-notification/blob/main/{rel + '/' if rel else ''}index.html",
        })
    for rel in sorted(pages):
        if is_en_path(rel) and ja_path_of_en(rel) not in pages:
            en_only.append({"path": rel, "url": f"{SITE}/{rel}/", "title": title_of(read(pages[rel]))})

    data = {"generated": date.today().isoformat(), "site": SITE, "count": len(rows), "app_ref_count": sum(r["app_ref"] for r in rows), "en_count": sum(r["en_kind"] == "en" for r in rows), "en_redirect_count": sum(r["en_kind"] == "redirect" for r in rows), "rows": rows, "en_only": en_only}
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    if a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(render_html(data))
    print(f"pages={len(rows)} en={data['en_count']} app_ref={data['app_ref_count']} en_only={len(en_only)}")


def render_html(data):
    rows = data["rows"]
    cats = []
    for r in rows:
        if r["category"] not in cats:
            cats.append(r["category"])
    order = ["法務文書", "使い方・説明", "FAQ", "マニュアル", "お知らせ（新）", "お知らせ（旧）", "アラート", "イベント", "ストア", "相互紹介", "BE 配信", "トップ"]
    cats.sort(key=lambda c: order.index(c) if c in order else 99)
    counts = {c: sum(r["category"] == c for r in rows) for c in cats}
    E = html.escape

    def trs():
        out = []
        for r in rows:
            d = "<br>".join(E(x) for x in r["dates"]) or '<span class="muted">—</span>'
            if r["en_kind"] == "en":
                en = f'<a href="{E(r["en_url"])}" target="_blank" rel="noopener">EN</a>'
            elif r["en_kind"] == "redirect":
                en = '<span class="muted" title="/en/ は日本語ページへ転送">転送</span>'
            elif r["en_kind"] == "ja":
                en = '<span class="pill pill-warn">日本語のまま</span>'
            else:
                en = '<span class="muted">なし</span>'
            app = '<span class="pill pill-app">アプリ</span>' if r["app_ref"] else ""
            noidx = "" if r["noindex"] else '<span class="pill pill-warn">index可</span>'
            t = E(r["title"]) or '<span class="muted">（題名なし）</span>'
            path = E(r["path"] or "/")
            out.append(
                f'<tr data-cat="{E(r["category"])}" data-text="{E((r["title"] + " " + r["path"]).lower())}">'
                f'<td class="cat">{E(r["category"])}</td>'
                f'<td class="title"><a href="{E(r["url"])}" target="_blank" rel="noopener">{t}</a><div class="path">/{path}</div></td>'
                f'<td class="lang">{en}</td>'
                f'<td class="dates">{d}</td>'
                f'<td class="upd num">{E(r["updated"])}</td>'
                f'<td class="flags">{app}{noidx}</td>'
                f'<td class="gh"><a href="{E(r["github"])}" target="_blank" rel="noopener">HTML</a></td>'
                f"</tr>"
            )
        return "\n".join(out)

    cat_buttons = "".join(f'<button class="chip" data-cat="{E(c)}">{E(c)} <b>{counts[c]}</b></button>' for c in cats)
    en_only_html = ""
    if data["en_only"]:
        items = "".join(f'<li><a href="{E(x["url"])}" target="_blank" rel="noopener">{E(x["title"] or x["path"])}</a> <span class="path">/{E(x["path"])}</span></li>' for x in data["en_only"])
        en_only_html = f'<section class="note"><h2>英語版だけがあるページ（{len(data["en_only"])}）</h2><ul>{items}</ul></section>'

    return f"""<title>公開中ページ一覧</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* layout: summary strip → filter chips → one dense table; data face for paths and dates */
:root {{
  --bg: #f7f8f6; --surface: #ffffff; --fg: #1d2a2e; --muted: #6b7a80; --line: #dde3e2;
  --accent: #0b6e8f; --accent-soft: #e3f1f6; --warn: #b4530a; --warn-soft: #fbeedf;
  --sans: "Noto Sans JP", "Hiragino Sans", system-ui, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #121a1d; --surface: #1a2428; --fg: #e6ecec; --muted: #93a3a8; --line: #2c393e;
  --accent: #5fc0df; --accent-soft: #15333d; --warn: #f0a05a; --warn-soft: #3d2a16; color-scheme: dark;
}} }}
:root[data-theme="dark"] {{
  --bg: #121a1d; --surface: #1a2428; --fg: #e6ecec; --muted: #93a3a8; --line: #2c393e;
  --accent: #5fc0df; --accent-soft: #15333d; --warn: #f0a05a; --warn-soft: #3d2a16; color-scheme: dark;
}}
body {{ background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 14px; line-height: 1.55; padding-inline: 16px; padding-block: 24px 48px; }}
.wrap {{ max-width: 1240px; margin: 0 auto; display: grid; gap: 20px; }}
header h1 {{ font-size: 22px; font-weight: 700; margin: 0 0 4px; text-wrap: balance; }}
header p {{ margin: 0; color: var(--muted); }}
header code {{ font-family: var(--mono); font-size: 12.5px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
.tile {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }}
.tile .k {{ font-size: 11px; letter-spacing: .06em; color: var(--muted); text-transform: uppercase; }}
.tile .v {{ font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
.chip {{ font: inherit; font-size: 13px; border: 1px solid var(--line); background: var(--surface); color: var(--fg); border-radius: 999px; padding: 4px 12px; cursor: pointer; }}
.chip b {{ color: var(--muted); font-weight: 500; margin-left: 2px; }}
.chip[aria-pressed="true"] {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
.chip[aria-pressed="true"] b {{ color: #e8f4f8; }}
.chip:focus-visible, input:focus-visible, a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
#q {{ font: inherit; font-size: 14px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--fg); min-width: 220px; flex: 1 1 220px; }}
.tablewrap {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }}
table {{ border-collapse: collapse; width: 100%; min-width: 860px; }}
th, td {{ text-align: left; vertical-align: top; padding: 9px 12px; border-top: 1px solid var(--line); }}
th {{ font-size: 11.5px; letter-spacing: .05em; color: var(--muted); font-weight: 500; border-top: 0; position: sticky; top: env(safe-area-inset-top, 0px); background: var(--surface); }}
td.cat {{ white-space: nowrap; color: var(--muted); font-size: 12.5px; }}
td.title a {{ color: var(--fg); font-weight: 500; text-decoration: none; }}
td.title a:hover {{ color: var(--accent); text-decoration: underline; }}
.path {{ font-family: var(--mono); font-size: 11.5px; color: var(--muted); word-break: break-all; }}
td.lang a, td.gh a {{ color: var(--accent); font-weight: 500; text-decoration: none; }}
td.dates {{ font-family: var(--mono); font-size: 12px; white-space: nowrap; }}
td.num {{ font-family: var(--mono); font-size: 12px; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.muted {{ color: var(--muted); }}
.pill {{ display: inline-block; font-size: 11px; border-radius: 999px; padding: 1px 8px; margin-right: 4px; white-space: nowrap; }}
.pill-app {{ background: var(--accent-soft); color: var(--accent); }}
.pill-warn {{ background: var(--warn-soft); color: var(--warn); }}
tr[hidden] {{ display: none; }}
.count {{ color: var(--muted); font-size: 13px; }}
.note {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px; }}
.note h2 {{ font-size: 14px; margin: 0 0 6px; }}
.note ul {{ margin: 0; padding-left: 18px; }}
footer {{ color: var(--muted); font-size: 12.5px; }}
@media (max-width: 600px) {{ th, td {{ padding: 8px; }} }}
</style>
<div class="wrap">
<header>
  <h1>公開中ページ一覧</h1>
  <p>お知らせサイト <code>{E(data["site"])}/</code> で公開中の日本語ページ全件。英語版がある行は <b>EN</b> リンク、無い行は <b>転送</b>（/en/ を開くと日本語ページへ飛ぶ）。生成日 {E(data["generated"])}・正本は GitHub <code>astran-jp/motitown-notification</code> のファイル（この表は <code>scripts/public_pages.py</code> の生成物）。</p>
</header>
<section class="summary">
  <div class="tile"><div class="k">公開ページ</div><div class="v">{data["count"]}</div></div>
  <div class="tile"><div class="k">英語版あり</div><div class="v">{data["en_count"]}</div></div>
  <div class="tile"><div class="k">/en/ は日本語へ転送</div><div class="v">{data["en_redirect_count"]}</div></div>
  <div class="tile"><div class="k">アプリから参照</div><div class="v">{data["app_ref_count"]}</div></div>
  <div class="tile"><div class="k">法務文書</div><div class="v">{counts.get("法務文書", 0)}</div></div>
</section>
<div class="controls">
  <button class="chip" data-cat="" aria-pressed="true">すべて <b>{data["count"]}</b></button>
  {cat_buttons}
  <input id="q" type="search" placeholder="題名・パスで絞り込み" aria-label="題名・パスで絞り込み">
  <span class="count" id="count"></span>
</div>
<div class="tablewrap">
<table>
<thead><tr><th>分類</th><th>題名 / パス</th><th>英語</th><th>制定・改定（本文表記）</th><th>最終更新</th><th></th><th>GitHub</th></tr></thead>
<tbody id="rows">
{trs()}
</tbody>
</table>
</div>
{en_only_html}
<footer>「アプリ」= motitan_app の URLManager.cs から開かれる URL／「index可」= noindex が付いていない（検索結果に出る可能性）／最終更新 = git の最終コミット日。英語版は <code>/notification/en/…</code>。</footer>
</div>
<script>
(function () {{
  var chips = document.querySelectorAll('.chip');
  var q = document.getElementById('q');
  var rows = document.querySelectorAll('#rows tr');
  var count = document.getElementById('count');
  var cat = '';
  try {{ cat = localStorage.getItem('pp-cat') || ''; q.value = localStorage.getItem('pp-q') || ''; }} catch (e) {{}}
  function apply() {{
    var t = q.value.trim().toLowerCase(); var n = 0;
    rows.forEach(function (r) {{
      var ok = (!cat || r.dataset.cat === cat) && (!t || r.dataset.text.indexOf(t) >= 0);
      r.hidden = !ok; if (ok) n++;
    }});
    chips.forEach(function (c) {{ c.setAttribute('aria-pressed', String(c.dataset.cat === cat)); }});
    count.textContent = n + ' 件';
    try {{ localStorage.setItem('pp-cat', cat); localStorage.setItem('pp-q', q.value); }} catch (e) {{}}
  }}
  chips.forEach(function (c) {{ c.addEventListener('click', function () {{ cat = c.dataset.cat; apply(); }}); }});
  q.addEventListener('input', apply);
  apply();
}})();
</script>
"""


if __name__ == "__main__":
    sys.exit(main())
