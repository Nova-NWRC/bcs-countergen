# -*- coding: utf-8 -*-
"""移动力类型「分面」与 HQ 移动力分类的样张。

① 战斗单位：战斗面 Leg、移动面 Truck（同一枚算子两面不同色）
② 指挥部 HQ：背面移动力分别用 TAC / Leg / Truck
"""
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

S = 6
cell = 75 * S
pad = 12

# ① 同一枚单位，正面 Leg、反面 Truck
unit = R.Counter(kind="inf", unit_id="II/505", formation_id="10 GD", size_label="II",
                 ar="5", quality="3", ma="8", move_class="leg",
                 ma_move="12", move_class_move="truck",
                 symbol="inf", bg="#F2DCB0", bar_color="#D97A20")
imgs = [("战斗面 · Leg 8", R.render(unit.copy(side="front"), 75)),
        ("移动面 · Truck 12", R.render(unit.copy(side="back"), 75))]

# ② HQ 背面三种移动力类型
for cls, label in (("tac", "HQ 背面 · TAC"), ("leg", "HQ 背面 · Leg"),
                   ("truck", "HQ 背面 · Truck")):
    hq = R.Counter(kind="hq", side="back", formation_id="30 Inf", size_label="XX",
                   command_radius="10", arty="4", activation="4", ma="8",
                   move_class=cls, symbol="inf", symbol_mode="glyph",
                   bg="#7E9B3D", bar_color="#A63A6B")
    imgs.append((label, R.render(hq, 75)))

cols = 5
sheet = Image.new("RGBA", (cols * cell + (cols + 1) * pad, cell + 30 + pad),
                  (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, (label, img) in enumerate(imgs):
    x = pad + i * (cell + pad)
    sheet.alpha_composite(img.resize((cell, cell), Image.NEAREST), (x, 26))
    d.text((x + cell / 2, 6), label, fill="#e6e6e6", anchor="ma",
           font=R.font("narrow_b", 17))

path = os.path.join(OUT, "move_class_sides.png")
sheet.convert("RGB").save(path)

# 75px 原尺寸小样
row = Image.new("RGBA", (cols * 75 + (cols + 1) * 6, 87), (26, 26, 30, 255))
for i, (_l, img) in enumerate(imgs):
    row.alpha_composite(img, (6 + i * 81, 6))
row.convert("RGB").save(os.path.join(OUT, "move_class_sides_75.png"))
print("ok", path)
