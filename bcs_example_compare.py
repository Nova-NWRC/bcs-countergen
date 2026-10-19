# -*- coding: utf-8 -*-
"""用用户框选示例的实测数据复刻同样算子，并排对比版式（上=生成器，下=Example 原图）。"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EX = r"F:\DSH_PzC_BCS\BCSV\Example"
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)


def bg_of(path):
    im = Image.open(path).convert("RGB")
    a = im.load()
    return "#%02X%02X%02X" % a[3, 30]


CASES = [
    # (示例文件名, 生成器规格)
    ("CS-3-F_352.png", dict(kind="inf", unit_id="2", formation_id="110/28", size_label="II",
                            ar="6", quality="4", rng="", ma="4", hard=False, symbol="inf",
                            symbol_mode="glyph", assault=True)),
    ("CS-3-F_192.png", dict(kind="av", unit_id="19", formation_id="C/64", size_label="II",
                            ar="6", av="3", quality="3", rng="", ma="14", hard=True, symbol="armor",
                            symbol_mode="glyph", assault=True)),
    ("CS-3-F_252.png", dict(kind="dual", unit_id="06", formation_id="10 Arm", size_label="I",
                            ar="5", av="1", quality="3", rng="", ma="16", hard=False, symbol="recon",
                            symbol_mode="glyph", assault=True)),
    ("CS-3-F_95.png", dict(kind="av", unit_id="14/1", formation_id="2 Inf", size_label="I",
                           ar="6", av="3", quality="2", rng="", ma="", hard=True, symbol="oval",
                           symbol_mode="glyph", assault=False)),
]

S = 7
cell = 75 * S
pad = 12
n = len(CASES)
sheet = Image.new("RGBA", (n * cell + (n + 1) * pad, 2 * cell + 3 * pad + 34), (26, 26, 30, 255))
d = R.ImageDraw.Draw(sheet)

for i, (name, spec) in enumerate(CASES):
    src = os.path.join(EX, name)
    x = pad + i * (cell + pad)
    ct = R.Counter(bg=bg_of(src), band="#5B8FD6", show_band=False,
                   bar_pos="none", **spec)
    mine = R.render(ct, 75).resize((cell, cell), Image.NEAREST)
    sheet.alpha_composite(mine, (x, pad + 18))
    real = Image.open(src).convert("RGBA").resize((cell, cell), Image.NEAREST)
    sheet.alpha_composite(real, (x, pad * 2 + cell + 24))
    d.text((x + cell / 2, pad + 4), "生成器 · " + name.replace(".png", ""), fill="#dcdcdc",
           anchor="ma", font=R.font("narrow_b", 17))
    d.text((x + cell / 2, pad * 2 + cell + 12), "Example 原图", fill="#9a9a9a",
           anchor="ma", font=R.font("narrow", 15))

path = os.path.join(OUT, "refit_compare.png")
sheet.convert("RGB").save(path)
print("ok", path)
