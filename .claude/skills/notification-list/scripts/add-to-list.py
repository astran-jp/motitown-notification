#!/usr/bin/env python3
"""お知らせ一覧(index.html)の先頭にお知らせ {N} のカードを追加する。

usage: add-to-list.py <N> [--title "一覧用タイトル"] [--date "2026/09/10 12:00"] [--dry-run]

- 文言の既定値は {N}/draft.md の frontmatter(list_title があればそれ、無ければ title / date)
- サムネイルは {N}/assets/header.png を幅900・品質75の WebP に変換して assets/notice-{N}.webp に置く
- カードのマークアップは、一覧にある直近の番号付きお知らせのカードを複製する(STUDIO の data-s 属性を共有し、CSS を増やさない)
- すでに /{N}/ のカードがあれば何もしない(exit 0)。--dry-run は index.html を書かずに差し込む HTML を表示する
- loading="lazy" は3件目以降に付ける(先頭2件は付けない)
"""
import argparse, os, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASE_URL = "https://motitown-notification.astran.jp"


def frontmatter(path):
    fm = {}
    lines = open(path, encoding="utf-8").read().split("\n")
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            m = re.match(r"^([A-Za-z_]+):\s*(.*)$", ln)
            if m:
                fm[m.group(1)] = m.group(2).strip()
    return fm


def norm_date(d):
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})$", d.strip())
    if not m:
        return d.strip()
    y, mo, da, h, mi = m.groups()
    return f"{y}/{int(mo):02d}/{int(da):02d} {int(h):02d}:{mi}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n")
    ap.add_argument("--title"); ap.add_argument("--date"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    n = a.n
    draft = os.path.join(REPO, n, "draft.md")
    fm = frontmatter(draft) if os.path.exists(draft) else {}
    title = a.title or fm.get("list_title") or fm.get("title")
    date = norm_date(a.date or fm.get("date", ""))
    if not title or not date or date == "TBD":
        print("一覧用タイトルと日時が要ります(draft.md の list_title/title と date、または --title/--date)", file=sys.stderr)
        return 2
    title_html = title.replace("／", "<br/>")

    idx_path = os.path.join(REPO, "index.html")
    html = open(idx_path, encoding="utf-8").read()
    href = f"{BASE_URL}/{n}/"
    if f'href="{href}"' in html:
        print(f"すでに一覧にあります: {href}")
        return 0

    # サムネイル
    src_png = os.path.join(REPO, n, "assets", "header.png")
    if not os.path.exists(src_png):
        print(f"ヘッダー画像がありません: {src_png}", file=sys.stderr)
        return 2
    im = Image.open(src_png).convert("RGB")
    w = 900
    h = round(im.height * w / im.width)
    thumb_rel = f"assets/notice-{n}.webp"
    thumb_abs = os.path.join(REPO, thumb_rel)
    if not a.dry_run:
        im.resize((w, h), Image.LANCZOS).save(thumb_abs, "WEBP", quality=75, method=6)

    # 雛形: 直近の番号付きお知らせのカード
    m = re.search(r'<a class="sd appear" data-s-[0-9a-f-]{36}="" href="' + re.escape(BASE_URL) + r'/\d+/"[^>]*>.*?</a>', html, re.S)
    if not m:
        print("雛形にするカード(番号付きお知らせ)が見つかりません", file=sys.stderr)
        return 2
    card = m.group(0)
    card = re.sub(r'href="[^"]*"', f'href="{href}"', card, count=1)
    card = re.sub(r' rel="noopener" target="_blank"', "", card)
    card = card.replace('<a class="sd appear"', '<a class="sd appear"', 1)
    card = re.sub(r'(<a [^>]*href="[^"]*")', r'\1 rel="noopener" target="_blank"', card, count=1)
    card = re.sub(r'src="[^"]*"', f'src="{thumb_rel}"', card, count=1)
    card = re.sub(r'width="\d+"', f'width="{w}"', card, count=1)
    card = re.sub(r'height="\d+"', f'height="{h}"', card, count=1)
    card = card.replace(' loading="lazy"', "")
    card = re.sub(r' data-r-[^=]*=""', "", card)  # STUDIO の残骸。CSS から参照されない
    ps = list(re.finditer(r'(<p class="text sd appear"[^>]*>)(.*?)(</p>)', card, re.S))
    if len(ps) != 2:
        print("雛形カードの日時/タイトルの <p> が2つではありません", file=sys.stderr)
        return 2
    card = card[:ps[0].start(2)] + date + card[ps[0].end(2):ps[1].start(2)] + title_html + card[ps[1].end(2):]

    # 先頭カードの直前に挿入
    body_i = html.index("<body")
    first_a = html.index('<a class="sd appear"', body_i)
    new_html = html[:first_a] + card + html[first_a:]

    # lazy の付け直し(3件目以降)
    cards = list(re.finditer(r'<a class="sd appear" [^>]*>.*?</a>', new_html, re.S))
    out, pos = [], 0
    for i, c in enumerate(cards):
        seg = c.group(0)
        has = ' loading="lazy"' in seg
        if i >= 2 and not has:
            seg = seg.replace(' decoding="async"', ' decoding="async" loading="lazy"', 1)
        elif i < 2 and has:
            seg = seg.replace(' loading="lazy"', "", 1)
        out.append(new_html[pos:c.start()]); out.append(seg); pos = c.end()
    out.append(new_html[pos:])
    new_html = "".join(out)

    if a.dry_run:
        print(card)
        return 0
    open(idx_path, "w", encoding="utf-8").write(new_html)
    print(f"added: {href} | {date} | {title} | {thumb_rel} ({w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
