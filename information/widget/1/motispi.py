#!/usr/bin/env python3
"""information/widget/1 のモチスピ版画像を作る(index.html が ?app=motispi のときに差し替えて表示する)。

usage: python3 information/widget/1/motispi.py <motitan_app>/Assets/Motitan/Textures/Icon/motispi_icon_1024.png

日本語版 assets/01-b0c33659.webp と英語版 en/information/widget/1/01-b0c33659.webp(overlay.py + en.post.py の出力)の
アプリアイコンをモチスピのアプリアイコンに、案内文の「モチタン」「Motitan」を「モチスピ」「Motispi」に描き替えて、
同じ場所に 01-b0c33659-motispi.webp として書き出す。英語版の画像を作り直したら、このスクリプトも実行し直すこと。
アイコンにはタップの円(オレンジの半透明 + リング)と指が重なっているので、円は白地の側から測った半径ごとの色で
新しいアイコンの上に描き直し、指は元画像の画素を残す。Pillow だけで動く。
"""
import math
import os
import sys
from collections import deque

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "en"))
import overlay  # noqa: E402

NAME = "01-b0c33659.webp"
OUT_NAME = "01-b0c33659-motispi.webp"
JA = os.path.join(HERE, "assets", NAME)
EN = os.path.join(ROOT, "en", "information", "widget", "1", NAME)
FONT_JP = os.path.join(ROOT, "scripts", "en", "fonts", "NotoSansJP.ttf")

# アプリアイコン(元画像のピクセル。角丸の半径も同じ単位)
ICON = (373, 584.5, 527, 738.5)
ICON_RADIUS = 15.5
SCREEN = (254, 254, 255)
# タップの円の中心と、円が届く半径。円の色は中心から右(白地)へ向かう ±30 度の範囲で測る
TAP = (517, 718)
TAP_REACH = 47
TAP_SAMPLE_DEG = (-30, 24)
# 指の内側(白)の 1 点と、指を探す範囲。輪郭線(紺)の内側を塗りつぶして指の形にする
HAND_SEED = (560, 775)
HAND_AREA = (490, 690, 630, 840)
HAND_OUTLINE = 7

# 日本語の案内文「モチタンアプリを長押ししてね」の「タン」(3・4 文字目)を消す範囲と、
# 「スピ」を置く位置(1 文字目「モ」から 37.2px 送り、ベースライン 202)
JA_ERASE = (266, 166, 343, 211)
JA_PEN = [(269.2, 202), (306.4, 202)]
JA_TEXT = "スピ"
JA_SIZE, JA_WEIGHT = 36, 500
JA_COLOR = (55, 82, 96)

# 英語の案内文は overlay.py と同じ指定で描き直す(en.images.json の text だけを変える)
EN_SPEC = {"rect": [180, 158, 720, 216], "fill": "auto", "text": "Press and hold the Motispi app icon",
           "size": 38, "weight": 500, "color": {"darkest": [200, 170, 700, 205]}}


def is_outline(p):
    r, g, b = p[:3]
    return r < 70 and g < 115 and b < 150 and b > r


def hand_mask(orig):
    px = orig.load()
    x0, y0, x1, y1 = HAND_AREA
    seen = {HAND_SEED}
    q = deque([HAND_SEED])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in seen or not (x0 <= n[0] < x1 and y0 <= n[1] < y1) or is_outline(px[n]):
                continue
            seen.add(n)
            q.append(n)
    if any(x in (x0, x1 - 1) or y in (y0, y1 - 1) for x, y in seen):
        raise SystemExit("指の塗りつぶしが範囲の外へ漏れた(HAND_SEED / is_outline を見直す)")
    fill = Image.new("L", orig.size, 0)
    fp = fill.load()
    for x, y in seen:
        fp[x, y] = 255
    near = fill.filter(ImageFilter.MaxFilter(HAND_OUTLINE * 2 + 3))
    np_ = near.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            if np_[x, y] and is_outline(px[x, y]):
                fp[x, y] = 255
    return fill.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))


def tap_profile(orig, hand):
    """半径 0.5px ごとの、白地に重なったタップの円の色。"""
    px, hp = orig.load(), hand.load()
    bins = {}
    for deg10 in range(TAP_SAMPLE_DEG[0] * 10, TAP_SAMPLE_DEG[1] * 10 + 1, 5):
        a = math.radians(deg10 / 10)
        for i in range(0, TAP_REACH * 4):
            r = i / 4
            x, y = int(round(TAP[0] + r * math.cos(a))), int(round(TAP[1] + r * math.sin(a)))
            if ICON[0] - 2 <= x <= ICON[2] + 2 and ICON[1] - 2 <= y <= ICON[3] + 2 or hp[x, y]:
                continue
            bins.setdefault(round(r * 2) / 2, []).append(px[x, y][:3])
    profile = {}
    for r, cs in bins.items():
        profile[r] = tuple(sorted(c[i] for c in cs)[len(cs) // 2] for i in range(3))
    # 中心付近は指先に隠れて白地が見えないので、内側の円の色で埋める
    inner = [profile[r] for r in sorted(profile) if 14 <= r <= 17]
    inner = tuple(sum(c[i] for c in inner) // len(inner) for i in range(3))
    for i in range(0, 29):
        if i / 2 not in profile or i / 2 < 14:
            profile[i / 2] = inner
    return profile


def icon_layer(icon_path, size):
    """新しいアイコンを角丸で切り抜き、元画像と同じ位置に置いた RGBA。4 倍で描いて縮める。"""
    k = 4
    x0, y0, x1, y1 = ICON
    w, h = round((x1 - x0) * k), round((y1 - y0) * k)
    big = Image.new("RGBA", (size[0] * k, size[1] * k), (0, 0, 0, 0))
    icon = Image.open(icon_path).convert("RGBA").resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=ICON_RADIUS * k, fill=255)
    big.paste(icon, (round(x0 * k), round(y0 * k)), mask)
    return big.resize(size, Image.LANCZOS)


def replace_icon(im, orig, icon_path):
    hand = hand_mask(orig)
    profile = tap_profile(orig, hand)
    layer = icon_layer(icon_path, im.size)
    # 古いアイコンの縁が残らないよう、少し広い角丸の範囲を画面の白に戻してから新しいアイコンを置く
    x0, y0, x1, y1 = ICON
    footprint = Image.new("L", im.size, 0)
    ImageDraw.Draw(footprint).rounded_rectangle([x0 - 2, y0 - 2, x1 + 1, y1 + 1], radius=ICON_RADIUS + 2, fill=255)
    screen = Image.new("RGBA", im.size, SCREEN + (255,))
    screen.alpha_composite(layer)
    out = im.convert("RGBA")
    op, sp, fp, hp, src = out.load(), screen.load(), footprint.load(), hand.load(), im.load()
    for y in range(int(y0) - 3, int(y1) + 3):
        for x in range(int(x0) - 3, int(x1) + 3):
            if not fp[x, y]:
                continue
            r = math.hypot(x - TAP[0], y - TAP[1])
            c = sp[x, y][:3]
            if r < TAP_REACH:
                w = profile.get(round(r * 2) / 2)
                if w:
                    # 円の色は (r, g, 0) を不透明度 1 - w_b/255 で重ねたものとして、白地の色 w から下地を差し替える
                    t = w[2] / 255
                    c = tuple(int(round(min(255, max(0, w[i] - w[2] + t * c[i])))) if i < 2 else int(round(t * c[2])) for i in range(3))
            hm = hp[x, y] / 255
            if hm:
                c = tuple(int(round(c[i] * (1 - hm) + src[x, y][i] * hm)) for i in range(3))
            op[x, y] = c + (255,)
    return out.convert("RGB")


def replace_ja_text(im):
    x0, y0, x1, y1 = JA_ERASE
    px = im.load()
    src = im.copy().load()
    for x in range(x0, x1):
        top, bot = src[x, y0 - 1], src[x, y1]
        for y in range(y0, y1):
            t = (y - y0) / float(y1 - y0)
            px[x, y] = tuple(int(round(a * (1 - t) + b * t)) for a, b in zip(top, bot))
    f = ImageFont.truetype(FONT_JP, JA_SIZE)
    f.set_variation_by_axes([JA_WEIGHT])
    d = ImageDraw.Draw(im)
    for ch, pen in zip(JA_TEXT, JA_PEN):
        d.text(pen, ch, font=f, fill=JA_COLOR, anchor="ls")
    return im


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    icon_path = sys.argv[1]
    orig = Image.open(JA).convert("RGB")

    ja = replace_ja_text(replace_icon(orig.copy(), orig, icon_path))
    ja_out = os.path.join(os.path.dirname(JA), OUT_NAME)
    ja.save(ja_out, quality=82, method=6)
    print(ja_out)

    en = replace_icon(Image.open(EN).convert("RGB"), orig, icon_path)
    overlay.render(en, EN_SPEC, orig)
    en_out = os.path.join(os.path.dirname(EN), OUT_NAME)
    en.save(en_out, quality=82, method=6)
    print(en_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
