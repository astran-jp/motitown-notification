#!/usr/bin/env python3
"""ヘッダーバナーにタイトル文字を固定スタイルで合成する。

usage: banner-title.py <背景画像(文字なし)> "<タイトル>" <出力png> [--size N] [--top N]

固定スタイル(お知らせ20のバナーを実測して決めた値。毎回同じ見た目にするため変えない):
  - フォント: Noto Sans JP Black (wght 900)  … サイト本文と同じファミリー
  - サイズ: 86px(1000x380 基準。文字列が安全域 900px を超えるときだけ自動で縮める)
  - 塗り: オレンジ #FF940F
  - 縁取り: 白 8px
  - ハロー: 薄い水色 #B5DFFB を 16px ぼかして外側に敷く
  - 位置: 水平中央、上端から 34px
  - 行数: 原則1行(8文字以内が目安)。タイトルに「／」か改行を含めると2行にし、各行を中央揃えにする
背景の幅が 1000 以外なら、すべての寸法を幅に比例させる。
"""
import argparse, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "NotoSansJP-Black.ttf")
FILL = (255, 148, 15)
STROKE = (255, 255, 255)
HALO = (181, 223, 251)
BASE_W = 1000
BASE_SIZE, BASE_TOP, BASE_STROKE, BASE_HALO, SAFE_W = 86, 34, 8, 16, 900


def load_font(size):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_axes([900])
    except Exception:
        try:
            f.set_variation_by_name("Black")
        except Exception:
            pass
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bg"); ap.add_argument("text"); ap.add_argument("out")
    ap.add_argument("--size", type=int); ap.add_argument("--top", type=int)
    a = ap.parse_args()

    bg = Image.open(a.bg).convert("RGBA")
    W, H = bg.size
    k = W / BASE_W
    size = a.size or round(BASE_SIZE * k)
    top = a.top if a.top is not None else round(BASE_TOP * k)
    stroke = max(1, round(BASE_STROKE * k))
    halo_r = max(1, round(BASE_HALO * k))
    safe = SAFE_W * k

    lines = [ln for ln in a.text.replace("／", "\n").split("\n") if ln.strip()]
    font = load_font(size)
    while max(font.getlength(ln) for ln in lines) > safe and size > 20:
        size -= 2
        font = load_font(size)

    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y_cursor = top
    widths = []
    for ln in lines:
        l, t, r, b = tmp.textbbox((0, 0), ln, font=font, stroke_width=stroke)
        tw, th = r - l, b - t
        widths.append(tw)
        x = round((W - tw) / 2 - l)
        y = round(y_cursor - t)
        # ハロー: 縁取り込みの字形を水色で描き、ぼかして下に敷く
        ImageDraw.Draw(halo).text((x, y), ln, font=font, fill=HALO, stroke_width=stroke + halo_r // 2, stroke_fill=HALO)
        # 本体: 白縁 + オレンジ塗り
        ImageDraw.Draw(layer).text((x, y), ln, font=font, fill=FILL, stroke_width=stroke, stroke_fill=STROKE)
        y_cursor += th + round(6 * k)

    out = Image.alpha_composite(bg, halo.filter(ImageFilter.GaussianBlur(halo_r)))
    out = Image.alpha_composite(out, layer)
    out.convert("RGB").save(a.out, optimize=True)
    print(f"wrote {a.out} size={W}x{H} font={size}px lines={len(lines)} text_w={max(widths)}px top={top}px")


if __name__ == "__main__":
    sys.exit(main())
