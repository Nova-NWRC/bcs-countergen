# -*- coding: utf-8 -*-
"""生成北约编制规模标志对照图 samples/size_nato.png（13 种预设 + 各自说明）。"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)

SIZE = 240
COLS = 7
PAD = 12
LABEL_H = 34

presets = R.SIZE_PRESETS
rows = (len(presets) + COLS - 1) // COLS
W = COLS * SIZE + (COLS + 1) * PAD
H = rows * (SIZE + LABEL_H) + (rows + 1) * PAD
sheet = Image.new("RGBA", (W, H), (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)

for i, (sym, name) in enumerate(presets):
    r, c = divmod(i, COLS)
    ct = R.Counter(kind="inf", unit_id="1/1", formation_id="DEMO", size_label=sym,
                   ar="5", quality="3", ma="4", symbol="inf", symbol_mode="letter",
                   bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, SIZE)
    x = PAD + c * (SIZE + PAD)
    y = PAD + r * (SIZE + LABEL_H + PAD)
    sheet.alpha_composite(img, (x, y))
    d.text((x + SIZE / 2, y + SIZE + 8), sym, fill="#f0f0f0", anchor="ma",
           font=R.font("narrow_b", 18))
    d.text((x + SIZE / 2, y + SIZE + 22), name, fill="#8f8f8f", anchor="ma",
           font=R.font("narrow", 13))

path = os.path.join(OUT, "size_nato.png")
sheet.convert("RGB").save(path)
print("ok", path, len(presets), "presets")
