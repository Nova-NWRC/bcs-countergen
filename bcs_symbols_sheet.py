# -*- coding: utf-8 -*-
"""生成全部兵种符号对照表 samples/symbols.png（当作工具箱的图标速查）。"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

try:                                    # 控制台不是 UTF-8 时 print 中文会炸
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)

SIZE = 150
COLS = 8
PAD = 12
LABEL_H = 26

rows = (len(R.SYMBOLS) + COLS - 1) // COLS
W = COLS * SIZE + (COLS + 1) * PAD
H = rows * (SIZE + LABEL_H) + (rows + 1) * PAD
sheet = Image.new("RGBA", (W, H), (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)

for i, (key, name) in enumerate(R.SYMBOLS):
    r, c = divmod(i, COLS)
    ct = R.Counter(kind="inf", unit_id="1/1", formation_id="DEMO", size_label="II",
                   ar="5", rng="3", ma="4", symbol=key, symbol_text="PzJg", symbol_mode="glyph",
                   hard=(i % 3 == 0), bg="#A3BA68", band="#E8C10C", bar_color="#4A5A22")
    img = R.render(ct, SIZE)
    x = PAD + c * (SIZE + PAD)
    y = PAD + r * (SIZE + LABEL_H + PAD)
    sheet.alpha_composite(img, (x, y))
    d.text((x + SIZE / 2, y + SIZE + 6), key, fill="#e6e6e6",
           anchor="ma", font=R.font("narrow_b", 15))
    d.text((x + SIZE / 2, y + SIZE + 17), name.split(" ", 1)[-1], fill="#8f8f8f",
           anchor="ma", font=R.font("narrow", 12))

path = os.path.join(OUT, "symbols.png")
sheet.save(path)
print("ok", path, f"({len(R.SYMBOLS)} 个符号)")
