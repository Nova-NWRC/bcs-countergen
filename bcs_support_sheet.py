# -*- coding: utf-8 -*-
"""支援单位样张：与战斗单位同版式，无箭头/MA/素质，底层铺 Support 大字。"""
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

CASES = [
    dict(unit_id="Spt", formation_id="10 GD", size_label="II", ar="6", symbol="oval",
         symbol_mode="letter", symbol_letters="", bg="#A3BA68", bar_color="#6E8B3D"),
    dict(unit_id="Arty", formation_id="4 AD", size_label="I", ar="5", symbol="text",
         symbol_mode="letter", symbol_letters="ARTY", bg="#B7D5EC", bar_color="#2F5FA8"),
    dict(unit_id="Corps", formation_id="82 Abn", size_label="X", ar="4",
         av="2", rng="3", support_values=True, symbol="none", symbol_mode="letter", symbol_letters="",
         bg="#F2DCB0", bar_color="#D97A20"),
    dict(unit_id="Eng", formation_id="1 GJ", size_label="II", ar="3", symbol="eng",
         symbol_mode="letter", symbol_letters="ENG", bg="#9AA46C", bar_color="#2E7D4F"),
]

imgs = []
for i, spec in enumerate(CASES):
    ct = R.Counter(kind="support", **spec)
    imgs.append(R.render(ct, 150))

sheet = Image.new("RGBA", (len(imgs) * 150 + (len(imgs) + 1) * 12, 150 + 46), (26, 26, 30, 255))
d = ImageDraw.Draw(sheet)
for i, img in enumerate(imgs):
    x = 12 + i * 162
    sheet.alpha_composite(img, (x, 34))
    d.text((x + 75, 12), f"support #{i+1}", fill="#dcdcdc", anchor="ma",
           font=R.font("narrow_b", 16))
path = os.path.join(OUT, "support_units.png")
sheet.convert("RGB").save(path)
print("ok", path)
