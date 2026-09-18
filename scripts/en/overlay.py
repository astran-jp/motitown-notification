#!/usr/bin/env python3
"""画像に焼き込まれた日本語を英語に描き替える(文字部分を背景色で塗り、英語を載せる)。

usage: overlay.py <dir>           # information/about-bp など({dir}/en.images.json を読む)
       overlay.py --grid <画像> <出力png> [--step 100]   # 座標を読むための目盛り付き画像

{dir}/en.images.json の形:
  {"assets/01-xxxx.webp": [
     {"rect": [x0, y0, x1, y1],          # 塗りつぶして文字を消す範囲(元画像のピクセル)
      "fill": "auto" | "#rrggbb" | null,  # auto は rect の四辺の色の中央値。null は塗らない(文字の無い所に足すとき)
      "text": "English text\\n2nd line",   # 空なら塗るだけ
      "size": 40, "weight": 700,           # px / 100..900
      "color": "#333333" | {"darkest": [x0,y0,x1,y1]} | {"sample": [x,y]},   # 文字色。darkest は元画像の範囲で最も暗い色(日本語の文字色を拾う)
      "align": "center" | "left" | "right",
      "box": [x0, y0, x1, y1],             # 文字を置く範囲(省略時は rect)。align に従って水平位置、垂直は中央
      "line_height": 1.4, "font": "sans" | "jp", "valign": "middle" | "top",
      "fit": true                          # box 幅に収まるまで size を縮める(既定 true)
     }, ...],
   ...}

出力は en/{dir}/<画像のファイル名>。build.py は en/{dir}/ に同名ファイルがあると日本語版の代わりに使う。
フォントは scripts/en/fonts/ の Noto Sans(可変ウェイト)。
"""
import json, os, sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FONTS = {"sans": os.path.join(HERE, "fonts", "NotoSans.ttf"), "jp": os.path.join(HERE, "fonts", "NotoSansJP.ttf")}
_cache = {}


def font(kind, size, weight):
    key = (kind, size, weight)
    if key not in _cache:
        f = ImageFont.truetype(FONTS[kind], size)
        try:
            axes = [a["name"] if isinstance(a, dict) else a for a in f.get_variation_axes()]
            values = []
            for a in f.get_variation_axes():
                tag = a.get("name", b"")
                tag = tag.decode() if isinstance(tag, bytes) else str(tag)
                if tag.lower().startswith("w") and "wght" in tag.lower() or tag.lower() == "weight":
                    values.append(weight)
                elif tag.lower() in ("wdth", "width"):
                    values.append(100)
                else:
                    values.append(a.get("default", 0))
            f.set_variation_by_axes(values)
        except Exception:
            pass
        _cache[key] = f
    return _cache[key]


def median_edge_color(im, rect):
    x0, y0, x1, y1 = rect
    px = im.load()
    samples = []
    for x in range(x0, x1, max(1, (x1 - x0) // 40)):
        samples.append(px[x, y0]); samples.append(px[x, y1 - 1])
    for y in range(y0, y1, max(1, (y1 - y0) // 40)):
        samples.append(px[x0, y]); samples.append(px[x1 - 1, y])
    samples = [s[:3] for s in samples]
    return tuple(sorted(c[i] for c in samples)[len(samples) // 2] for i in range(3))


def hex_color(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def resolve_color(orig, value):
    """色指定を (r,g,b) にする。"#rrggbb" のほか、元画像から拾う
    {"sample": [x, y]}(その点の色)/ {"darkest": [x0, y0, x1, y1]}(範囲で最も暗い色 = 文字色)が使える。"""
    if isinstance(value, str):
        return hex_color(value)
    px = orig.load()
    if "sample" in value:
        x, y = value["sample"]
        return px[x, y][:3]
    if "darkest" in value:
        x0, y0, x1, y1 = value["darkest"]
        best, best_l = None, 1e9
        for y in range(y0, y1):
            for x in range(x0, x1):
                r, g, b = px[x, y][:3]
                l = 0.299 * r + 0.587 * g + 0.114 * b
                if l < best_l:
                    best, best_l = (r, g, b), l
        return best
    raise ValueError(f"unknown color spec: {value}")


def wrap(draw, text, f, max_w):
    """明示の改行を優先し、収まらない行は単語で折り返す。"""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            cand = (cur + " " + w).strip()
            if cur and draw.textlength(cand, font=f) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = cand
        lines.append(cur)
    return lines


def render(im, spec, orig):
    draw = ImageDraw.Draw(im)
    rect = spec.get("rect")
    fill = spec.get("fill", "auto")
    if rect and fill is not None:
        color = median_edge_color(im, rect) if fill == "auto" else resolve_color(orig, fill)
        draw.rectangle([rect[0], rect[1], rect[2] - 1, rect[3] - 1], fill=color)
    text = spec.get("text", "")
    if not text:
        return
    box = spec.get("box", rect)
    size = int(spec.get("size", 40))
    weight = int(spec.get("weight", 700))
    kind = spec.get("font", "sans")
    color = resolve_color(orig, spec.get("color", "#333333"))
    align = spec.get("align", "center")
    lh = float(spec.get("line_height", 1.4))
    fit = spec.get("fit", True)
    max_w = box[2] - box[0]
    max_h = box[3] - box[1]
    while True:
        f = font(kind, size, weight)
        lines = wrap(draw, text, f, max_w)
        line_h = size * lh
        total_h = line_h * len(lines)
        widest = max(draw.textlength(l, font=f) for l in lines)
        if not fit or size <= 10 or (total_h <= max_h + 1 and widest <= max_w + 1):
            break
        size -= 1
    valign = spec.get("valign", "middle")
    y = box[1] if valign == "top" else box[1] + (max_h - total_h) / 2
    for l in lines:
        w = draw.textlength(l, font=f)
        if align == "center":
            x = box[0] + (max_w - w) / 2
        elif align == "right":
            x = box[2] - w
        else:
            x = box[0]
        # anchor "la" = 左上・ascender 基準。行の高さは size*lh、文字は行内で中央寄せ
        draw.text((x, y + (line_h - size) / 2), l, font=f, fill=color, anchor="la")
        y += line_h


def grid(src, out, step=100):
    im = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(im)
    f = font("sans", 18, 600)
    w, h = im.size
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=(255, 0, 0), width=1)
        draw.text((x + 2, 2), str(x), font=f, fill=(255, 0, 0))
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(0, 0, 255), width=1)
        draw.text((2, y + 2), str(y), font=f, fill=(0, 0, 255))
    im.save(out)
    print(out, im.size)


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--grid":
        step = int(sys.argv[5]) if len(sys.argv) >= 6 and sys.argv[4] == "--step" else 100
        grid(sys.argv[2], sys.argv[3], step)
        return 0
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = sys.argv[1].strip("/")
    spec_path = os.path.join(ROOT, d, "en.images.json")
    if not os.path.isfile(spec_path):
        print(f"ERROR: {spec_path} が無い")
        return 1
    spec = json.load(open(spec_path, encoding="utf-8"))
    en_dir = os.path.join(ROOT, "en", d)
    os.makedirs(en_dir, exist_ok=True)
    for rel, items in spec.items():
        src = os.path.join(ROOT, d, rel)
        im = Image.open(src).convert("RGB")
        orig = im.copy()
        for item in items:
            render(im, item, orig)
        out = os.path.join(en_dir, os.path.basename(rel))
        if out.lower().endswith(".webp"):
            im.save(out, quality=82, method=6)
        else:
            im.save(out)
        print(f"{out}: {len(items)} 箇所")
    return 0


if __name__ == "__main__":
    sys.exit(main())
