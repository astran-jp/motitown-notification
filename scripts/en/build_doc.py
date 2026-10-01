#!/usr/bin/env python3
"""{dir}/index.html(日本語)の外枠に {dir}/en.html(英語本文)を差し込んで en/{dir}/index.html を作る。

usage: build_doc.py <dir>        # document/legal-privacy/riyokiyaku など

お知らせ本文(build.py)と違い、利用規約・プライバシーポリシーのような文書ページ向け。
公式の英訳(Notion「利用規約、プライバシーポリシーの作成」配下)を en.html に HTML として書き、
日本語ページの <head>・スタイル・外枠(StudioCanvas)をそのまま使って英語ページにする。

en.html の 1 行目は <!-- title: ... --> でページタイトル(<title> と og:title)を書く。
本文は <div class="richText sd" ...> の中身(h2/p/ol/ul/table)を並べる。日本語ページで richText に
付いている data-s-* 属性はスタイルのキーなので、本文ブロックの属性は日本語ページの 2 番目の richText から引き継ぐ。
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import ROOT, JA  # noqa: E402

SITE = "https://motitown-notification.astran.jp"
LANG_SWITCH_EN = '<div class="lang-switch" style="position:fixed;top:calc(8px + env(safe-area-inset-top,0px));right:8px;z-index:9999;"><span style="display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border:1px solid #d6dde3;border-radius:999px;background:#fff;font-size:14px;line-height:1;color:#1b6aa5;box-shadow:0 1px 3px rgba(0,0,0,.08);"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true" style="flex:none"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg><a data-has-link="true" href="/{d}/" rel="noopener" style="color:#1b6aa5;text-decoration:none">日本語</a><span style="color:#9aa5ad">|</span><strong style="color:#1d2a2e">English</strong></span></div>'



def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1].strip("/")
    src = os.path.join(ROOT, d, "index.html")
    body_path = os.path.join(ROOT, d, "en.html")
    for p in (src, body_path):
        if not os.path.isfile(p):
            print(f"ERROR: {p} が無い")
            return 1
    html = open(src, encoding="utf-8").read()
    en = open(body_path, encoding="utf-8").read()
    m = re.match(r"\s*<!--\s*title:\s*(.*?)\s*-->\s*", en, re.S)
    if not m:
        print("ERROR: en.html の 1 行目に <!-- title: ... --> が無い")
        return 1
    title = m.group(1)
    en_body = en[m.end():].strip()

    # 本文: 最初の richText(見出し)から最後の richText までを英語本文で置き換える
    blocks = list(re.finditer(r'<div class="richText sd"( data-s-[0-9a-f-]+="")?>', html))
    if len(blocks) < 2:
        print("ERROR: richText ブロックが 2 つ未満(文書ページの形ではない)")
        return 1
    heading_attr = blocks[0].group(1) or ""
    body_attr = blocks[1].group(1) or ""
    start = blocks[0].start()
    end = html.index("<!-- -->", start)
    # 末尾は「</div></div><!-- -->」(richText の閉じ + appear の閉じ)。appear の閉じは残す
    end = html.rfind("</div>", start, end)
    new_body = (f'<div class="richText sd"{heading_attr}><h2 id="index_txZJqCzR">{title}</h2></div>'
                f'<div class="richText sd"{body_attr}>{en_body}</div>')
    out = html[:start] + new_body + html[end:]

    out = re.sub(r"<title>.*?</title>", f"<title>{title} | Motitown</title>", out, count=1, flags=re.S)
    out = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda mm: mm.group(1) + title + mm.group(2), out, count=1)
    # 右上の言語切替: 日本語ページの「日本語（現在）| English」→ 英語ページでは「日本語 | English（現在）」
    out = re.sub(r'<div class="lang-switch".*?</span></div>', LANG_SWITCH_EN.format(d=d), out, count=1, flags=re.S)
    out = out.replace('lang="ja"', 'lang="en"', 1)
    out = out.replace("family=Noto+Sans+JP", "family=Noto+Sans").replace('"Noto Sans JP"', '"Noto Sans"').replace("'Noto Sans JP'", "'Noto Sans'")
    out = out.replace(f"{SITE}/{d}/\"", f"{SITE}/en/{d}/\"").replace(f"{SITE}/{d}\"", f"{SITE}/en/{d}\"")
    # STUDIO の表は日本語向けに word-break: break-all なので、英語では単語の途中で折り返さないようにする
    out = out.replace("</head>", '<style>.richText [data-type="table"] p{word-break:normal;overflow-wrap:anywhere;}</style>\n</head>', 1)

    en_dir = os.path.join(ROOT, "en", d)
    rel = os.path.relpath(os.path.join(ROOT, d), en_dir).replace(os.sep, "/")
    out = re.sub(r'((?:src|href|srcset|poster)=")(?!https?:|/|#|data:|mailto:|tel:)', lambda mm: mm.group(1) + rel + "/", out)
    out = re.sub(r"(url\(['\"]?)(?!https?:|/|#|data:)(?=[\w.])", lambda mm: mm.group(1) + rel + "/", out)
    os.makedirs(en_dir, exist_ok=True)
    open(os.path.join(en_dir, "index.html"), "w", encoding="utf-8").write(out)
    body = re.sub(r"<!--.*?-->|<style.*?</style>|<script.*?</script>|<div class=\"lang-switch\".*?</span></div>", "", out, flags=re.S)
    left = JA.findall(body)
    runs = re.findall(r"[぀-ヿ一-鿿][^<\"]{0,30}", body)
    print(f"en/{d}/index.html: 生成。残った日本語 {len(left)} 文字" + (f" 例: {runs[:5]}" if runs else ""))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
