#!/usr/bin/env python3
"""お知らせ 1 件の日本語 index.html から翻訳対象の文字ブロックを抜き出し、{dir}/en.json に書く。

usage: extract.py <dir>          # 22 / Notification/7 など(日本語 index.html があるディレクトリ)

en.json の形:
  {"title": {"ja": "...", "en": ""},          # <title>(一覧カードと og:title にも使う)
   "list_title": {"ja": "...", "en": ""},     # 一覧(index.html)のカード文言。一覧に無ければ省略
   "banner": {"ja": "...", "en": ""},         # draft.md の banner(ヘッダー画像の文字)。無ければ省略
   "segments": [{"tag": "p", "ja": "...", "en": ""}, ...]}   # 本文。ja 内の <br>/<strong>/<a> は en でも同じ位置に残す

既に en.json があれば、同じ ja の en は引き継ぐ(再抽出で訳が消えない)。
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JA = re.compile(r"[぀-ヿ一-鿿]")
OPEN = re.compile(r"<(h1|h2|h3|h4|p|li|figcaption|summary|th|td|dt|dd)(\s[^>]*)?>")
BOUND = re.compile(r"<(?:ul|ol|p|div|li|h[1-4]|table|dl|section|figure|figcaption|nav|footer|header)\b|</(?:h1|h2|h3|h4|p|li|figcaption|summary|th|td|dt|dd)>")
ATTR = re.compile(r'(alt|aria-label|content)="([^"]*[぀-ヿ一-鿿][^"]*)"')


def segments(html):
    """本文の文字ブロックを出現順に返す。各要素は {tag, start, end, raw, ja}。raw は開始タグ直後から
    次のブロック境界までの生 HTML(インラインタグ込み)、ja はその strip。"""
    out = []
    for m in OPEN.finditer(html):
        start = m.end()
        b = BOUND.search(html, start)
        end = b.start() if b else len(html)
        raw = html[start:end]
        if not JA.search(raw):
            continue
        out.append({"tag": m.group(1), "start": start, "end": end, "raw": raw, "ja": raw.strip()})
    return out


def attrs(html):
    return [{"tag": "attr:" + m.group(1), "ja": m.group(2)} for m in ATTR.finditer(html)]


def read_frontmatter(path):
    if not os.path.isfile(path):
        return {}
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def list_title_for(d):
    """一覧 index.html のカードからこのお知らせのタイトルを拾う(無ければ None)。"""
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    hrefs = [f"https://motitown-notification.astran.jp/{d}/", f"/{d}/"]
    for h in hrefs:
        m = re.search(r'<a class="sd appear"[^>]*href="' + re.escape(h) + r'"[^>]*>.*?<p[^>]*>[^<]*</p><p[^>]*>(.*?)</p>', idx, re.S)
        if m:
            return m.group(1).strip()
    return None


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1].strip("/")
    src = os.path.join(ROOT, d, "index.html")
    if not os.path.isfile(src):
        print(f"ERROR: {src} が無い")
        return 1
    html = open(src, encoding="utf-8").read()
    out_path = os.path.join(ROOT, d, "en.json")
    prev = json.load(open(out_path, encoding="utf-8")) if os.path.isfile(out_path) else {}
    memo = {s["ja"]: s["en"] for s in prev.get("segments", []) if s.get("en")}
    for k in ("title", "list_title", "banner"):
        if prev.get(k, {}).get("en"):
            memo[prev[k]["ja"]] = prev[k]["en"]

    def pair(ja):
        return {"ja": ja, "en": memo.get(ja, "")}

    out = {}
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    out["title"] = pair(m.group(1).strip() if m else "")
    lt = list_title_for(d)
    if lt:
        out["list_title"] = pair(lt)
    fm = read_frontmatter(os.path.join(ROOT, d, "draft.md"))
    if fm.get("banner"):
        out["banner"] = pair(fm["banner"])
    segs = [{"tag": s["tag"], **pair(s["ja"])} for s in segments(html)] + [{"tag": a["tag"], **pair(a["ja"])} for a in attrs(html)]
    # <title> と同じ文字列は segments に含めない(title 側で訳す)
    out["segments"] = [s for s in segs if not (s["tag"] == "attr:content" and s["ja"] == out["title"]["ja"])]
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    todo = sum(1 for s in out["segments"] if not s["en"]) + sum(1 for k in ("title", "list_title", "banner") if k in out and not out[k]["en"])
    print(f"{out_path}: segments {len(out['segments'])}, 未訳 {todo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
