#!/usr/bin/env python3
"""お知らせ一覧(index.html)の先頭に、開発者ブログ記事へのカードを追加する。

usage: add-blog-card.py <slug> --title "12.2.0 アップデート内容／…" --date "2026/10/23 15:40" [--dry-run]

- リンク先は https://motitown.com/blog/<slug>/ 、サムネイルは assets/blog-<slug>.webp(blog-thumb.py で先に作る)
- カードのマークアップは一覧にある既存のブログカード(無ければ番号付きお知らせのカード)を複製する(CSS を増やさない)
- タイトルの「／」は改行(<br/>)になる
- すでに同じ URL のカードがあれば何もしない(exit 0)
- loading="lazy" は3件目以降に付ける(先頭2件は付けない)
"""
import argparse, os, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CARD = r'<a class="sd appear" data-s-[0-9a-f-]{36}="" href="%s"[^>]*>.*?</a>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("--title", required=True); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not re.match(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}$", a.date):
        print("日時は 2026/10/23 15:40 の形で", file=sys.stderr)
        return 2
    href = f"https://motitown.com/blog/{a.slug}/"
    thumb_rel = f"assets/blog-{a.slug}.webp"
    if not os.path.exists(os.path.join(REPO, thumb_rel)):
        print(f"サムネイルがありません: {thumb_rel}(blog-thumb.py で作る)", file=sys.stderr)
        return 2
    w, h = Image.open(os.path.join(REPO, thumb_rel)).size

    idx_path = os.path.join(REPO, "index.html")
    html = open(idx_path, encoding="utf-8").read()
    if f'href="{href}"' in html:
        print(f"すでに一覧にあります: {href}")
        return 0

    m = (re.search(CARD % r"https://motitown\.com/blog/[^\"]+/", html, re.S)
         or re.search(CARD % r"https://motitown\.com/notification/\d+/", html, re.S))
    if not m:
        print("雛形にするカードが見つかりません", file=sys.stderr)
        return 2
    card = m.group(0)
    card = re.sub(r'href="[^"]*"', f'href="{href}"', card, count=1)
    card = re.sub(r'src="[^"]*"', f'src="{thumb_rel}"', card, count=1)
    card = re.sub(r'width="\d+"', f'width="{w}"', card, count=1)
    card = re.sub(r'height="\d+"', f'height="{h}"', card, count=1)
    card = card.replace(' loading="lazy"', "")
    card = re.sub(r' data-r-[^=]*=""', "", card)
    ps = list(re.finditer(r'(<p class="text sd appear"[^>]*>)(.*?)(</p>)', card, re.S))
    if len(ps) != 2:
        print("雛形カードの日時/タイトルの <p> が2つではありません", file=sys.stderr)
        return 2
    title_html = a.title.replace("／", "<br/>")
    card = card[:ps[0].start(2)] + a.date + card[ps[0].end(2):ps[1].start(2)] + title_html + card[ps[1].end(2):]

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
    print(f"added: {href} | {a.date} | {a.title} | {thumb_rel} ({w}x{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
