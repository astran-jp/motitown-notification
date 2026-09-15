#!/usr/bin/env python3
"""日本語のお知らせ一覧 index.html から英語一覧 en/index.html を生成する。

usage: build_list.py

- 英語版 en/{dir}/index.html があるお知らせだけをカードにする(訳していないものは載せない)
- カードのタイトルは {dir}/en.json の list_title.en(無ければ title.en)
- サムネイルは日本語版と同じ assets/notice-{N}.webp。en/assets/ に同名ファイルがあればそちら(英語版バナー)
- 先頭 2 件は loading="lazy" なし、3 件目以降は付ける(日本語版と同じ)
- 英語版の無いお知らせ(数字ディレクトリと Notification/{N})には en/{dir}/index.html として日本語ページへの転送を置く。
  BE が英語ユーザーの URL を機械的に /en/{N} に読み替えるため、404 にしないための受け皿(一覧には載せない)
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import ROOT, JA  # noqa: E402

SITE = "https://motitown-notification.astran.jp"
CARD = re.compile(r'<a class="sd appear"[^>]*href="([^"]*)"[^>]*>.*?</a>', re.S)
HEAD = {"お知らせ｜モチタウン": "Announcements | Motitown", "お知らせ": "Announcements"}


FALLBACK_MARK = "<!-- fallback: redirect to ja -->"


def is_translated(d):
    p = os.path.join(ROOT, "en", d, "index.html")
    return os.path.isfile(p) and FALLBACK_MARK not in open(p, encoding="utf-8").read(2000)


def write_fallbacks():
    """英語版の無いお知らせに、日本語ページへ転送する en/{dir}/index.html を置く。"""
    dirs = [n for n in os.listdir(ROOT) if n.isdigit()] + [f"Notification/{n}" for n in os.listdir(os.path.join(ROOT, "Notification")) if n.isdigit()]
    n = 0
    for d in sorted(dirs):
        if not os.path.isfile(os.path.join(ROOT, d, "index.html")) or is_translated(d):
            continue
        target = f"/{d}/"
        html = (f'<!DOCTYPE html>{FALLBACK_MARK}\n<html lang="ja"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{SITE}{target}">'
                f'<title>Redirecting…</title></head><body><a href="{target}">{SITE}{target}</a></body></html>\n')
        os.makedirs(os.path.join(ROOT, "en", d), exist_ok=True)
        open(os.path.join(ROOT, "en", d, "index.html"), "w", encoding="utf-8").write(html)
        n += 1
    return n


def dir_of(href):
    m = re.match(re.escape(SITE) + r"/(\d+)/?$", href) or re.match(r"/(\d+)/?$", href)
    if m:
        return m.group(1)
    m = re.match(r"(?:" + re.escape(SITE) + r")?/(Notification/\d+)/?$", href)
    return m.group(1) if m else None


def main():
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    cards = list(CARD.finditer(idx))
    if not cards:
        print("ERROR: index.html にカードが無い")
        return 1
    kept, dropped = [], []
    for m in cards:
        d = dir_of(m.group(1))
        if not (d and is_translated(d)):
            dropped.append(m.group(1))
            continue
        tr = json.load(open(os.path.join(ROOT, d, "en.json"), encoding="utf-8"))
        title = (tr.get("list_title") or {}).get("en") or tr["title"]["en"]
        card = m.group(0)
        card = card.replace(f'href="{m.group(1)}"', f'href="/en/{d}/"', 1)
        # タイトルは 2 つ目の <p>
        ps = list(re.finditer(r"<p[^>]*>(.*?)</p>", card, re.S))
        if len(ps) < 2:
            print(f"ERROR: カードの形が想定外 {m.group(1)}")
            return 1
        p = ps[1]
        card = card[: p.start(1)] + title + card[p.end(1) :]
        # サムネイル
        def thumb(im):
            name = os.path.basename(im.group(1))
            local = os.path.isfile(os.path.join(ROOT, "en", "assets", name))
            return im.group(0).replace(im.group(1), ("assets/" if local else "../assets/") + name)
        card = re.sub(r'<img[^>]*src="([^"]+)"', thumb, card, count=1)
        card = card.replace(' loading="lazy"', "")
        kept.append(card)
    if not kept:
        print("ERROR: 英語版のあるお知らせが 1 件も無い")
        return 1
    for i in range(2, len(kept)):
        kept[i] = kept[i].replace("<img ", '<img loading="lazy" ', 1)

    out = idx[: cards[0].start()] + "".join(kept) + idx[cards[-1].end() :]
    for ja, en in sorted(HEAD.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(f">{ja}<", f">{en}<").replace(f'content="{ja}"', f'content="{en}"')
    out = out.replace('lang="ja"', 'lang="en"', 1)
    out = out.replace("family=Noto+Sans+JP", "family=Noto+Sans").replace('"Noto Sans JP"', '"Noto Sans"').replace("'Noto Sans JP'", "'Noto Sans'")
    out = out.replace(f'href="{SITE}/"', f'href="{SITE}/en/"').replace(f'content="{SITE}/"', f'content="{SITE}/en/"')
    out = re.sub(r'((?:href|src)=")(?!https?:|/|#|data:|\.\./|assets/)', lambda m: m.group(1) + "../", out)
    os.makedirs(os.path.join(ROOT, "en"), exist_ok=True)
    open(os.path.join(ROOT, "en", "index.html"), "w", encoding="utf-8").write(out)
    body = re.sub(r"<!--.*?-->|<style.*?</style>|<script.*?</script>", "", out, flags=re.S)
    left = re.findall(r"[぀-ヿ一-鿿][^<\"]{0,30}", body)
    fb = write_fallbacks()
    print(f"en/index.html: カード {len(kept)} 件(英語版なしで除外 {len(dropped)} 件)。日本語ページへの転送 {fb} 件。残った日本語 {len(left)} 箇所" + (f" 例: {left[:5]}" if left else ""))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
