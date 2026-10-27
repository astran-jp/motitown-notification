#!/usr/bin/env python3
"""ブログ記事の cover と同じ構図(左に大きな文字・右にキャラと絵)で、一覧カード用サムネイル(900x270 WebP)を作る。

usage: blog-banner.py <文字消し版cover> <x0> <y0> <x1> <y1> <出力.webp> --l1 "4,784本|の動画学習" --l2 "大辞典からの単語登録" [--sub ほか] [--preview out.png]

- 右側: 文字消し版 cover の (x0,y0)-(x1,y1) を高さいっぱいに置く(キャラと絵の塊。左端はフェードで背景になじませる)
- 左側: 淡いクリーム〜水色の背景に、cover の見出しと同じ配色で2行の文字
  - --l1 は「|」で区切った前半をオレンジ(数字など強調)、後半を紺で描く
  - --l2 は紺。--sub は2行目の右に小さく
- 文字は Noto Sans JP Black・白縁・薄い影(cover の見出しに合わせる)
"""
import argparse, importlib.util, os, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "banner_title", os.path.join(HERE, "..", "..", "notification-page", "scripts", "banner-title.py"))
bt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bt)

W, H = 2000, 600          # 作業解像度(出力は 900x270)
OUT_W, OUT_H = 900, 270
ORANGE_TOP, ORANGE_BOTTOM = (255, 150, 30), (240, 70, 20)
NAVY = (22, 32, 62)
WHITE = (255, 255, 255)
BG_LEFT, BG_RIGHT = (255, 250, 232), (225, 242, 252)
MARGIN = 60


def gradient_text(text, font, stroke):
    """オレンジの縦グラデーション文字(白縁)のレイヤーを返す。"""
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=font, stroke_width=stroke)
    w, h = r - l, b - t
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((-l, -t), text, font=font, fill=255)
    grad = Image.new("RGBA", (w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        c = tuple(round(ORANGE_TOP[i] * (1 - k) + ORANGE_BOTTOM[i] * k) for i in range(3))
        ImageDraw.Draw(grad).line((0, y, w, y), fill=c + (255,))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((-l, -t), text, font=font, fill=WHITE, stroke_width=stroke, stroke_fill=WHITE)
    layer.paste(grad, (0, 0), mask)
    return layer, l, t


def solid_text(text, font, stroke, fill):
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=font, stroke_width=stroke)
    layer = Image.new("RGBA", (r - l, b - t), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((-l, -t), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=WHITE)
    return layer, l, t


def with_shadow(canvas, layer, xy):
    a = layer.split()[3]
    sh = Image.new("RGBA", layer.size, (40, 60, 110, 0))
    sh.putalpha(a.point(lambda v: v * 0.35))
    pad = 24
    big = Image.new("RGBA", (layer.width + pad * 2, layer.height + pad * 2), (0, 0, 0, 0))
    big.paste(sh, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(8))
    canvas.alpha_composite(big, (xy[0] - pad + 4, xy[1] - pad + 8))
    canvas.alpha_composite(layer, xy)


def fit_font(parts, max_w, size, stroke):
    while size > 20:
        f = bt.load_font(size)
        if sum(f.getlength(p) for p in parts) + stroke * 2 <= max_w:
            return f, size
        size -= 4
    return bt.load_font(size), size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); [ap.add_argument(k, type=int) for k in ("x0", "y0", "x1", "y1")]; ap.add_argument("out")
    ap.add_argument("--l1", required=True); ap.add_argument("--l2", required=True); ap.add_argument("--sub")
    ap.add_argument("--text-w", type=int, default=1060, help="文字領域の幅(作業解像度 2000 基準)")
    ap.add_argument("--preview")
    a = ap.parse_args()

    canvas = Image.new("RGBA", (W, H))
    for x in range(W):
        k = x / (W - 1)
        c = tuple(round(BG_LEFT[i] * (1 - k) + BG_RIGHT[i] * k) for i in range(3))
        ImageDraw.Draw(canvas).line((x, 0, x, H), fill=c + (255,))

    art = Image.open(a.src).convert("RGBA").crop((a.x0, a.y0, a.x1, a.y1))
    art = art.resize((round(art.width * H / art.height), H), Image.LANCZOS)
    fade = 120
    mask = Image.new("L", art.size, 255)
    for x in range(fade):
        ImageDraw.Draw(mask).line((x, 0, x, H), fill=round(255 * x / fade))
    art.putalpha(mask)
    canvas.alpha_composite(art, (W - art.width, 0))

    text_w = a.text_w - MARGIN
    stroke1, stroke2 = 14, 11
    p1 = a.l1.split("|")
    f1, s1 = fit_font(p1, text_w, 170, stroke1)
    p2 = [a.l2] + ([a.sub] if a.sub else [])
    f2, s2 = fit_font([a.l2, (a.sub or "") * 0], text_w - (bt.load_font(60).getlength(a.sub) + 10 if a.sub else 0), 120, stroke2)
    fsub = bt.load_font(round(s2 * 0.5)) if a.sub else None

    # 1行目: オレンジ + 紺
    layers1 = []
    for i, part in enumerate(p1):
        if i == 0:
            layers1.append(gradient_text(part, f1, stroke1))
        else:
            layers1.append(solid_text(part, f1, stroke1, NAVY))
    l2, l2l, l2t = solid_text(a.l2, f2, stroke2, NAVY)
    lsub = solid_text(a.sub, fsub, stroke2 - 3, NAVY) if fsub else None

    h1 = max(l.height for l, _, _ in layers1)
    gap = 18
    total_h = h1 + gap + l2.height
    y = (H - total_h) // 2
    w1 = sum(l.width for l, _, _ in layers1) - stroke1 * 2 * (len(layers1) - 1)
    w2 = l2.width + (lsub[0].width + 8 if lsub else 0)
    x = MARGIN + max(0, (text_w - max(w1, w2)) // 2)
    cx = x + (max(w1, w2) - w1) // 2
    for l, ll, lt in layers1:
        with_shadow(canvas, l, (cx, y + (h1 - l.height)))
        cx += l.width - stroke1 * 2
    y2 = y + h1 + gap
    x2 = x + (max(w1, w2) - w2) // 2
    with_shadow(canvas, l2, (x2, y2))
    if lsub:
        with_shadow(canvas, lsub[0], (x2 + l2.width + 8, y2 + l2.height - lsub[0].height - 4))

    out = canvas.convert("RGB").resize((OUT_W, OUT_H), Image.LANCZOS)
    out.save(a.out, "WEBP", quality=75, method=6)
    if a.preview:
        out.save(a.preview)
    print(f"wrote {a.out} art=({a.x0},{a.y0})-({a.x1},{a.y1})→{art.width}px l1={s1}px l2={s2}px")
    return 0


if __name__ == "__main__":
    sys.exit(main())
