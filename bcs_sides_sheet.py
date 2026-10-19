# -*- coding: utf-8 -*-
"""战斗单位正/反面样张：同一枚算子的战斗面与移动面并排，验证布局一致、只换数值。"""
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

UNITS = [
    R.Counter(kind="av", unit_id="I/33", formation_id="10 GD", size_label="II", ar="5",
              av="4", quality="4", rng="2", ma="16", ma_move="12", quality_move="3",
              move_class="tac", move_class_move="truck",
              hard=True, symbol="armor", bg="#A3BA68", bar_color="#6E8B3D"),
    R.Counter(kind="inf", unit_id="II/505", formation_id="10 GD", size_label="II", ar="5",
              quality="3", ma="8", ma_move="12", quality_move="2",
              move_class="leg", move_class_move="truck",
              symbol="inf", bg="#F2DCB0", bar_color="#D97A20"),
    R.Counter(kind="dual", unit_id="23", formation_id="Pape", size_label="I", ar="5",
              av="1", quality="5", ma="16", ma_move="12",
              move_class="truck", move_class_move="leg",
              symbol="recon", bg="#BFC0B6", bar_color="#7A3E8F"),
]

S = 5
cell = 75 * S
pad = 12
cols = len(UNITS)
sheet = Image.new("RGBA", (cols * 2 * cell + (cols * 2 + 1) * pad, cell + 58), (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, ct in enumerate(UNITS):
    for j, side in enumerate(("front", "back")):
        img = R.render(ct.copy(side=side), 75).resize((cell, cell), Image.NEAREST)
        x = pad + (i * 2 + j) * (cell + pad)
        sheet.alpha_composite(img, (x, 40))
        d.text((x + cell / 2, 14), ("战斗面 front" if side == "front" else "移动面 back"),
               fill="#e2e2e2", anchor="ma", font=R.font("narrow_b", 18))

path = os.path.join(OUT, "combat_sides.png")
sheet.convert("RGB").save(path)

# 75px 原尺寸小样，确认缩放后仍可辨
row = Image.new("RGBA", (cols * 2 * 75 + (cols * 2 + 1) * 6, 87), (26, 26, 30, 255))
for i, ct in enumerate(UNITS):
    for j, side in enumerate(("front", "back")):
        row.alpha_composite(R.render(ct.copy(side=side), 75),
                            (6 + (i * 2 + j) * 81, 6))
row.convert("RGB").save(os.path.join(OUT, "combat_sides_75.png"))
print("ok", path)
