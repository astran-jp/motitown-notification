#!/usr/bin/env python3
"""information/widget/1 の英語画像の後処理(overlay.py は水平の文字しか描けないため)。

usage: python3 scripts/en/overlay.py information/widget/1 && python3 information/widget/1/en.post.py

overlay.py の出力 en/information/widget/1/01-b0c33659.webp を読み、傾いた 2 枚のウィジェットカードの
日本語(今日も成長してるね / 毎日頑張ってるね！)を周囲のグラデーションで消して、同じ傾きの英語に描き替える。
overlay.py を実行し直したら、このスクリプトも実行し直すこと。Pillow だけで動く。
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TARGET = os.path.join(ROOT, "en", "information", "widget", "1", "01-b0c33659.webp")
FONT = os.path.join(ROOT, "scripts", "en", "fonts", "NotoSans.ttf")

# center = 文字列の中心(元画像のピクセル)、angle = 文字の傾き(度。PIL の rotate に渡すと水平になる向き)
# band = 傾きを戻した座標での文字の範囲 (u0, v0, u1, v1)。center からの相対
# protect = 同じ座標系で、塗ってはいけない絵(葉っぱ)の範囲
CARDS = [
    {"center": (711, 1023), "angle": -14.62, "band": (-98, -8, 100, 14),
     "text": "Growing every day!", "size": 20, "color": (22, 96, 18)},
    {"center": (730, 1257), "angle": 11.84, "band": (-114, -18, 142, 12), "protect": [(10, 9, 46, 20)],
     "text": "Keep it up every day!", "size": 25, "color": (20, 90, 16)},
]


def font(size, weight):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_axes([weight if i == 0 else 100 for i, _ in enumerate(f.get_variation_axes())])
    except Exception:
        pass
    return f


def is_glyph(p):
    r, g, b = p[:3]
    return g > r + 18 and g > b + 18 and (r + g + b) < 420


def median(vals):
    vals = sorted(vals)
    return vals[len(vals) // 2]


def column_color(rot, x, rows):
    px = [rot.getpixel((xx, y))[:3] for xx in range(x - 2, x + 3) for y in rows]
    return tuple(median([p[i] for p in px]) for i in range(3))


def repaint(im, card):
    cx, cy = card["center"]
    ang = card["angle"]
    u0, v0, u1, v1 = card["band"]
    rot = im.rotate(ang, resample=Image.BICUBIC, center=(cx, cy))
    x0, y0, x1, y1 = cx + u0, cy + v0, cx + u1, cy + v1
    # 文字のピクセル(濃い緑)を太らせたマスク
    mask = Image.new("L", im.size, 0)
    mp = mask.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            if is_glyph(rot.getpixel((x, y))):
                mp[x, y] = 255
    mask = mask.filter(ImageFilter.MaxFilter(11))  # 文字の周りの白いにじみまで覆う
    # 帯の外(数字や葉っぱ)と protect の中は塗らない
    keep = Image.new("L", im.size, 0)
    kd = ImageDraw.Draw(keep)
    kd.rectangle([x0 - 6, y0 - 2, x1 + 6, y1 + 2], fill=255)
    for pu0, pv0, pu1, pv1 in card.get("protect", []):
        kd.rectangle([cx + pu0, cy + pv0, cx + pu1, cy + pv1], fill=0)
    mask = Image.composite(mask, Image.new("L", im.size, 0), keep)
    # 帯の全ピクセルに地色(上下の行からの補間)を入れておき、不透明度だけをマスクにする(縁に黒が混ざらない)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    lp = layer.load()
    pad = 8
    for x in range(x0 - pad, x1 + pad):
        top = column_color(rot, x, range(y0 - 6, y0 - 3))
        bot = column_color(rot, x, range(y1 + 3, y1 + 6))
        # 片方が絵(数字・葉っぱ・キャラ)に掛かっている列は、明るい方(= カードの地色)だけを使う
        if max(abs(a - b) for a, b in zip(top, bot)) > 16:
            top = bot = max(top, bot, key=sum)
        for y in range(y0 - pad, y1 + pad):
            t = min(1.0, max(0.0, (y - y0) / float(y1 - y0)))
            lp[x, y] = tuple(int(round(a * (1 - t) + b * t)) for a, b in zip(top, bot)) + (255,)
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(1.6)))
    f = font(card["size"], 600)
    d = ImageDraw.Draw(layer)
    d.text((cx + (u0 + u1) / 2.0, cy + (v0 + v1) / 2.0), card["text"], font=f, fill=card["color"] + (255,), anchor="mm")
    back = layer.rotate(-ang, resample=Image.BICUBIC, center=(cx, cy))
    out = im.convert("RGBA")
    out.alpha_composite(back)
    return out.convert("RGB")


# アプリアイコンの中のロゴ「モチタン」(白文字 + オレンジの縁)。右端はタップの丸(中心 TAP、半径 TAP_R)の下に隠れている
LOGO = (394, 698, 491, 736)
TAP, TAP_R = (517, 718), 29.5


def repaint_logo(im):
    x0, y0, x1, y1 = LOGO
    src = im.copy()
    px = im.load()
    for x in range(x0, x1):
        top = column_color(src, x, range(y0 - 4, y0 - 1))
        bot = column_color(src, x, range(y1, y1 + 2))
        for y in range(y0, y1):
            if (x - TAP[0]) ** 2 + (y - TAP[1]) ** 2 <= TAP_R ** 2:
                continue
            t = (y - y0) / float(y1 - y0)
            px[x, y] = tuple(int(round(a * (1 - t) + b * t)) for a, b in zip(top, bot))
    f = font(21, 900)
    pos = ((x0 + 486) / 2.0, (y0 + y1) / 2.0 - 1)
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text(pos, "Motitan", font=f, fill=(255, 255, 255, 150), anchor="mm",
                              stroke_width=5, stroke_fill=(255, 255, 255, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(1.5))
    ImageDraw.Draw(glow).text(pos, "Motitan", font=f, fill=(255, 252, 240, 255), anchor="mm",
                              stroke_width=3, stroke_fill=(232, 100, 18, 255))
    out = im.convert("RGBA")
    out.alpha_composite(glow)
    return out.convert("RGB")


def main():
    im = Image.open(TARGET).convert("RGB")
    for card in CARDS:
        im = repaint(im, card)
    im = repaint_logo(im)
    im.save(TARGET, quality=82, method=6)
    print(TARGET)


if __name__ == "__main__":
    main()
