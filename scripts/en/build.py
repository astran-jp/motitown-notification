#!/usr/bin/env python3
"""{dir}/index.html(日本語)と {dir}/en.json から英語版 en/{dir}/index.html を生成する。

usage: build.py <dir>          # 22 / Notification/7 など

- 本文・<title>・alt 等を en.json の en で置き換える(未訳があれば失敗)
- 画像などのアセットは日本語版のディレクトリを参照する(コピーしない)。
  ただし en/{dir}/ に同名ファイル(英語版ヘッダー header.png など)があればそちらを使う
- lang / フォント(Noto Sans JP → Noto Sans)/ og:url を英語版に合わせる
- 生成後に残った日本語を数えて表示する(0 でなければ終了コード 1)
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import ROOT, JA, segments, attrs  # noqa: E402

SITE = "https://motitown-notification.astran.jp"


FALLBACK_MARK = "<!-- fallback: redirect to ja -->"


def has_english(path):
    p = os.path.join(ROOT, "en", path.strip("/"), "index.html")
    return os.path.isfile(p) and FALLBACK_MARK not in open(p, encoding="utf-8").read(2000)


def localize_links(html):
    """ページ内のサイト内リンク(ルート基準 /information/beginner-guide/2/ や絶対 URL)のうち、
    英語版が存在するものを /en/ 付きに向ける(使い方ガイドの前後ページなど)。日本語版へ意図して張るリンクは
    英語版が無いか、すでに /en/ 付きなのでそのまま。"""
    def rep(m):
        path = m.group(2)
        if path.startswith("/en/") or path == "/en" or not has_english(path):
            return m.group(0)
        return f'{m.group(1)}/en{path}"'
    html = re.sub(r'(href=")' + re.escape(SITE) + r'(/[^"#?]*?/?)"', rep, html)
    html = re.sub(r'(href=")(/[^"#?/][^"#?]*?/?)"', rep, html)
    return html


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1].strip("/")
    src = os.path.join(ROOT, d, "index.html")
    tr_path = os.path.join(ROOT, d, "en.json")
    for p in (src, tr_path):
        if not os.path.isfile(p):
            print(f"ERROR: {p} が無い(先に extract.py {d})")
            return 1
    html = open(src, encoding="utf-8").read()
    tr = json.load(open(tr_path, encoding="utf-8"))
    byja = {s["ja"]: s["en"] for s in tr["segments"]}
    missing = [s["ja"][:40] for s in tr["segments"] if not s["en"]]
    if not tr["title"]["en"]:
        missing.insert(0, "<title>")
    if missing:
        print(f"ERROR: 未訳 {len(missing)} 件: {missing[:5]}")
        return 1

    # 本文ブロックを後ろから置換(位置がずれないように)
    segs = segments(html)
    unknown = [s["ja"][:40] for s in segs if s["ja"] not in byja]
    if unknown:
        print(f"ERROR: en.json に無いブロック {len(unknown)} 件(index.html が変わった。extract.py をやり直す): {unknown[:5]}")
        return 1
    out = html
    for s in reversed(segs):
        out = out[: s["start"]] + s["raw"].replace(s["ja"], byja[s["ja"]]) + out[s["end"] :]
    for t in tr["segments"]:
        if t["tag"] == "text":
            out = re.sub(r">(\s*)" + re.escape(t["ja"]) + r"(\s*)<", lambda m: ">" + m.group(1) + t["en"] + m.group(2) + "<", out)
    for a in attrs(html):
        en = byja.get(a["ja"]) or (tr["title"]["en"] if a["ja"] == tr["title"]["ja"] else None)
        if en:
            out = out.replace(f'{a["tag"][5:]}="{a["ja"]}"', f'{a["tag"][5:]}="{en}"', 1)
    out = re.sub(r"<title>.*?</title>", "<title>" + tr["title"]["en"] + "</title>", out, count=1, flags=re.S)

    # 言語・フォント・URL
    out = out.replace('lang="ja"', 'lang="en"', 1)
    out = out.replace("family=Noto+Sans+JP", "family=Noto+Sans").replace('"Noto Sans JP"', '"Noto Sans"').replace("'Noto Sans JP'", "'Noto Sans'")
    # ページ自身の URL(og:url / canonical)だけ英語版に。アセットの絶対 URL は日本語版のまま
    out = out.replace(f"{SITE}/{d}/\"", f"{SITE}/en/{d}/\"").replace(f"{SITE}/{d}\"", f"{SITE}/en/{d}\"")

    # アセットは日本語版ディレクトリを参照。en/{dir}/ にある同名ファイルは英語版として優先
    en_dir = os.path.join(ROOT, "en", d)
    rel = os.path.relpath(os.path.join(ROOT, d), en_dir).replace(os.sep, "/")
    out = re.sub(r'((?:src|href|srcset|data-file|poster)=")(?!https?:|/|#|data:)', lambda m: m.group(1) + rel + "/", out)
    out = re.sub(r"(url\(['\"]?)(?!https?:|/|#|data:)(?=[\w.])", lambda m: m.group(1) + rel + "/", out)
    out = localize_links(out)
    os.makedirs(en_dir, exist_ok=True)
    for name in os.listdir(en_dir):
        if name in ("index.html", "en.json") or name.startswith(".") or os.path.isdir(os.path.join(en_dir, name)):
            continue
        out = out.replace(f"{rel}/assets/{name}", name).replace(f"{SITE}/{d}/assets/{name}", name)
        # 差し替え画像の寸法が日本語版と違えば <img> の width/height を実寸に合わせる(縦横比の崩れ防止)
        try:
            from PIL import Image
            w, h = Image.open(os.path.join(en_dir, name)).size
            out = re.sub(r'(<img[^>]*src="' + re.escape(name) + r'"[^>]*?)\swidth="\d+"\sheight="\d+"', lambda m: f'{m.group(1)} width="{w}" height="{h}"', out)
            out = re.sub(r'(<img[^>]*?)\sheight="\d+"([^>]*src="' + re.escape(name) + r'"[^>]*?)\swidth="\d+"', lambda m: f'{m.group(1)} height="{h}"{m.group(2)} width="{w}"', out)
        except ImportError:
            pass

    open(os.path.join(en_dir, "index.html"), "w", encoding="utf-8").write(out)
    body = re.sub(r"<!--.*?-->|<style.*?</style>|<script.*?</script>", "", out, flags=re.S)
    left = JA.findall(body)
    runs = re.findall(r"[぀-ヿ一-鿿][^<\"]{0,30}", body)
    print(f"en/{d}/index.html: 生成。残った日本語 {len(left)} 文字" + (f" 例: {runs[:5]}" if runs else ""))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
