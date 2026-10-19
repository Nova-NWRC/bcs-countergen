# -*- coding: utf-8 -*-
"""移动力 / 装甲值分类色底 + HQ 兵牌底色跟随编制色带 的样张。"""
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

MOVE = [("leg", "Leg 徒步"), ("truck", "Truck 卡车"), ("tac", "TAC 战术")]
AVS = [("red", "Red 红色"), ("limited", "Limited 有限"), ("standoff", "Stand Off 拒止"),
       ("light", "Light 轻装甲")]

cells = []
for cls, label in MOVE:
    cells.append((R.Counter(kind="inf", unit_id="II/505", formation_id="10 GD",
                            size_label="II", ar="5", quality="3", ma="8",
                            move_class=cls, symbol="inf", bg="#F2DCB0",
                            bar_color="#D97A20"), f"移动力 {label}"))
for cls, label in AVS:
    cells.append((R.Counter(kind="av", unit_id="I/33", formation_id="10 GD",
                            size_label="II", ar="5", av="4", quality="3", ma="12",
                            move_class="truck", av_class=cls, hard=True, symbol="armor",
                            bg="#A3BA68", bar_color="#6E8B3D"), f"装甲值 {label}"))

S = 6
cell = 75 * S
pad = 12
cols = 4
rows = (len(cells) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cell + (cols + 1) * pad, rows * (cell + 26) + pad),
                  (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, (ct, label) in enumerate(cells):
    r, c = divmod(i, cols)
    x = pad + c * (cell + pad)
    y = pad + r * (cell + 26)
    sheet.alpha_composite(R.render(ct, 75).resize((cell, cell), Image.NEAREST), (x, y))
    d.text((x + cell / 2, y + cell + 4), label, fill="#dcdcdc", anchor="ma",
           font=R.font("narrow_b", 15))

path = os.path.join(OUT, "value_classes.png")
sheet.convert("RGB").save(path)
print("ok", path)

# HQ 兵牌底色开关
hq_on = R.Counter(kind="hq", formation_id="30 Inf", size_label="XX", command_radius="10",
                  arty="4", activation="4", ma="8", symbol="inf", symbol_mode="glyph",
                  bg="#7E9B3D", bar_color="#A63A6B", hq_box_tint=True)
hq_off = hq_on.copy(hq_box_tint=False)
pair = Image.new("RGBA", (2 * 300 + 36, 330), (26, 26, 30, 255))
d2 = ImageDraw.Draw(pair)
pair.alpha_composite(R.render(hq_on, 300), (12, 26))
pair.alpha_composite(R.render(hq_off, 300), (12 + 300 + 12, 26))
d2.text((12 + 150, 6), "兵牌底色跟随编制色带 (开)", fill="#eee", anchor="ma",
        font=R.font("narrow_b", 16))
d2.text((12 + 300 + 12 + 150, 6), "关闭", fill="#eee", anchor="ma", font=R.font("narrow_b", 16))
pair.convert("RGB").save(os.path.join(OUT, "hq_box_tint.png"))
print("ok hq_box_tint.png")
