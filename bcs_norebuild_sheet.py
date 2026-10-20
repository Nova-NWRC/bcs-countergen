# -*- coding: utf-8 -*-
"""「不可补员/重建」黄圈样张：与官方 BC 算子并排对照。"""
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
ROOT = r"F:\DSH_PzC_BCS\BCSV\Counter"

base = dict(kind="av", unit_id="1/33", formation_id="10 GD", size_label="II", ar="5",
            av="4", quality="4", rng="2", ma="12", move_class="truck",
            symbol="inf", bg="#A3BA68", bar_color="#6E8B3D")
on = R.Counter(**base, no_rebuild=True)
off = R.Counter(**base, no_rebuild=False)

S = 7
cell = 75 * S
tiles = [("生成 · 不可重建", R.render(on, 75)), ("生成 · 普通", R.render(off, 75))]
for fn, label in (("BBC-CS-1-B_78.png", "官方 · 带黄圈"), ("BBC-CS-1-B_1.png", "官方 · 普通")):
    p = os.path.join(ROOT, "BC", fn)
    if os.path.exists(p):
        tiles.append((label, Image.open(p).convert("RGBA")))

sheet = Image.new("RGBA", (len(tiles) * (cell + 12) + 12, cell + 34), (24, 24, 28, 255))
d = ImageDraw.Draw(sheet)
for i, (label, img) in enumerate(tiles):
    x = 12 + i * (cell + 12)
    sheet.alpha_composite(img.resize((cell, cell), Image.NEAREST), (x, 28))
    d.text((x + cell / 2, 8), label, fill="#e2e2e2", anchor="ma", font=R.font("narrow_b", 15))

path = os.path.join(OUT, "no_rebuild.png")
sheet.convert("RGB").save(path)
print("ok", path)
