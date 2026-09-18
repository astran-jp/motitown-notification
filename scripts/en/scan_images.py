#!/usr/bin/env python3
"""英語ページが参照している画像を OCR(macOS Vision)にかけ、日本語が残っている画像を探す。

usage: scan_images.py                 # en/ 配下の全英語ページ(転送スタブ以外)の画像を走査。残りがあれば終了コード 1
       scan_images.py <画像> [...]     # 指定した画像の文字と位置(元画像のピクセル)を全部出す。overlay の座標取りに使う

初回は scripts/en/ocr.swift を ~/.cache/motitown-notification/ocr にコンパイルする(macOS + swiftc が要る)。
OCR は小さい文字や装飾文字を取りこぼす/誤読することがあるので、最後は目でも確認する。
「くBack」のように英語の < を「く」と読む誤検出は ALLOW に入れてある。
"""
import hashlib, json, os, re, subprocess, sys, tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BIN = os.path.expanduser("~/.cache/motitown-notification/ocr")
JA = re.compile(r"[ぁ-んァ-ヶ一-鿿]")
FALLBACK_MARKS = ("<!-- fallback: redirect to ja -->", "<!-- moved:")
ALLOW = re.compile(r"^[く〈<＜]\s*Back$|^崔一鳴$")


def ensure_bin():
    src = os.path.join(HERE, "ocr.swift")
    if not os.path.isfile(BIN) or os.path.getmtime(BIN) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(BIN), exist_ok=True)
        subprocess.run(["swiftc", "-O", src, "-o", BIN], check=True)


def ocr(paths):
    """{path: [{"text", "box":[x0,y0,x1,y1], "conf"}]}(座標は元画像のピクセル)"""
    ensure_bin()
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        mapping, scale = {}, {}
        for p in paths:
            im = Image.open(p)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[3])
                im = bg
            else:
                im = im.convert("RGB")
            k = 2 if im.width < 700 else 1          # 小さい画像は 2 倍にして取りこぼしを減らす
            if k == 2:
                im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
            png = os.path.join(tmp, hashlib.md5(p.encode()).hexdigest() + ".png")
            im.save(png)
            mapping[png], scale[png] = p, k
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("\n".join(mapping))
        res = subprocess.run([BIN, lst], capture_output=True, text=True, check=True).stdout
        for line in res.splitlines():
            d = json.loads(line)
            k = scale[d["path"]]
            out[mapping[d["path"]]] = [
                {"text": i["text"], "conf": round(i["conf"], 2),
                 "box": [i["x"] // k, i["y"] // k, (i["x"] + i["w"]) // k, (i["y"] + i["h"]) // k]}
                for i in d.get("items", []) if i["conf"] >= 0.3]
    return out


def english_page_images():
    imgs = {}
    for cur, _dirs, files in os.walk(os.path.join(ROOT, "en")):
        if "index.html" not in files:
            continue
        html = open(os.path.join(cur, "index.html"), encoding="utf-8").read()
        if any(m in html[:2000] for m in FALLBACK_MARKS):
            continue
        srcs = set(re.findall(r'<img[^>]*?src="([^"]+)"', html)) | set(re.findall(r'url\(["\']?([^)"\']+\.(?:webp|png|jpe?g))', html))
        for s in srcs:
            if s.startswith("data:"):
                continue
            if s.startswith("http"):
                if "motitown-notification.astran.jp" not in s:
                    continue
                s = "/" + s.split("astran.jp/", 1)[1]
            p = os.path.join(ROOT, s.lstrip("/")) if s.startswith("/") else os.path.normpath(os.path.join(cur, s))
            if os.path.isfile(p) and not p.endswith(".svg"):
                imgs.setdefault(os.path.relpath(p, ROOT), []).append(os.path.relpath(cur, ROOT))
    return imgs


def main():
    if len(sys.argv) > 1:
        for p, items in ocr(sys.argv[1:]).items():
            print(f"== {p} {Image.open(p).size}")
            for i in items:
                print(f"  {'JA' if JA.search(i['text']) else '  '} {i['box']} {i['text']!r}")
        return 0
    imgs = english_page_images()
    res = ocr([os.path.join(ROOT, p) for p in imgs])
    left = 0
    for p in sorted(imgs):
        ja = [i for i in res.get(os.path.join(ROOT, p), []) if JA.search(i["text"]) and not ALLOW.search(i["text"].strip())]
        if ja:
            left += 1
            print(f"{p}  ({', '.join(sorted(set(imgs[p]))[:3])}) : {len(ja)} 箇所  {' / '.join(i['text'] for i in ja[:4])[:80]}")
    print(f"英語ページの画像 {len(imgs)} 枚中、日本語が残っているもの {left} 枚")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
