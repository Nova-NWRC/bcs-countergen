# -*- coding: utf-8 -*-
"""HQ 双面样张 + 与 HQ Eg 原图对照（上=生成器，下=示例）。"""
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
EG = r"F:\DSH_PzC_BCS\BCSV\HQ Eg"
os.makedirs(OUT, exist_ok=True)

HQ = R.Counter(kind="hq", command_radius="10", formation_id="30 Inf", size_label="XX",
               activation="4", arty="4", ma="8", ar="4",
               symbol="inf", symbol_mode="glyph", bg="#7E9B3D", bar_color="#6E8B3D")

S = 8
cell = 75 * S
pad = 14
labels = ["gen front", "gen back", "example front", "example back"]
imgs = [
    R.render(HQ.copy(side="front"), 75).resize((cell, cell), Image.NEAREST),
    R.render(HQ.copy(side="back"), 75).resize((cell, cell), Image.NEAREST),
]
for name in ("HQ-正常.png", "HQ-已激活.png"):
    p = os.path.join(EG, name)
    imgs.append(Image.open(p).convert("RGBA").resize((cell, cell), Image.NEAREST))

sheet = Image.new("RGBA", (len(imgs) * cell + (len(imgs) + 1) * pad, cell + 62), (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, img in enumerate(imgs):
    x = pad + i * (cell + pad)
    sheet.alpha_composite(img, (x, 40))
    d.text((x + cell / 2, 14), labels[i], fill="#e2e2e2", anchor="ma",
           font=R.font("narrow_b", 20))
    if i >= 2:
        d.line([(x, 40), (x + cell, 40)], fill=(255, 90, 90), width=2)

path = os.path.join(OUT, "hq_compare.png")
sheet.convert("RGB").save(path)
print("ok", path)
