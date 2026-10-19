# -*- coding: utf-8 -*-
"""补给车样张：正常面 / 失常面 与 HQ Eg 原图对照。"""
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

TRUCK = R.Counter(kind="supply", formation_id="90 Inf\nDiv", bg="#7E9B3D",
                  bar_color="#6E8B3D", bar_pos="none")

S = 8
cell = 75 * S
pad = 14
labels = ["gen 正常面", "gen 失常面", "example 正常", "example 失常"]
imgs = [
    R.render(TRUCK.copy(side="front"), 75).resize((cell, cell), Image.NEAREST),
    R.render(TRUCK.copy(side="back"), 75).resize((cell, cell), Image.NEAREST),
]
for name in ("补给车-正常.png", "补给车-失常.png"):
    imgs.append(Image.open(os.path.join(EG, name)).convert("RGBA")
                .resize((cell, cell), Image.NEAREST))

sheet = Image.new("RGBA", (len(imgs) * cell + (len(imgs) + 1) * pad, cell + 62),
                  (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, img in enumerate(imgs):
    x = pad + i * (cell + pad)
    sheet.alpha_composite(img, (x, 40))
    d.text((x + cell / 2, 14), labels[i], fill="#e2e2e2", anchor="ma",
           font=R.font("narrow_b", 20))

path = os.path.join(OUT, "supply_truck.png")
sheet.convert("RGB").save(path)
print("ok", path)
