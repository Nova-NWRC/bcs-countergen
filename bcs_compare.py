"""把 75px 生成算子与真实算子并排放大对比，检验版式还原度。"""
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)

mine = [
    R.Counter(kind="av", unit_id="I/33", formation_id="10 GD", size_label="II", ar="5",
              av="4", rng="4", rng2="2", ma="16", hard=True, symbol="armor",
              bg="#A3BA68", band="#5B8FD6", bar_color="#4A5A22"),
    R.Counter(kind="inf", unit_id="G/504", formation_id="82 Abn", size_label="I", ar="5",
              rng="3", ma="4", hard=False, symbol="abn", assault=True,
              bg="#C8DEEE", band="#5B8FD6", bar_color="#2F5FA8"),
    R.Counter(kind="av", unit_id="23", formation_id="Pape", size_label="I", ar="5",
              av="1", rng="5", ma="16", hard=False, symbol="recon",
              bg="#BFC0B6", band="#8FA8C8", bar_color="#3A5C8C"),
]
real = [
    r'F:\DSH_PzC_BCS\BCSV\Counter\DF\DF R03 C05.png',
    r'F:\DSH_PzC_BCS\BCSV\Counter\LB\CS-1-F_0.png',
    r'F:\DSH_PzC_BCS\BCSV\Counter\PLS\BCS-PLS-1-F_158.png',
]

S = 6
cell = 75 * S
pad = 10
cols = 3
sheet = Image.new("RGBA", (cols * cell + (cols + 1) * pad, 2 * cell + 3 * pad), (30, 30, 34, 255))
for i, ct in enumerate(mine):
    img = R.render(ct, 75).resize((cell, cell), Image.NEAREST)
    sheet.alpha_composite(img, (pad + i * (cell + pad), pad))
for i, p in enumerate(real):
    img = Image.open(p).convert("RGBA")
    img = img.resize((cell, cell), Image.NEAREST)
    sheet.alpha_composite(img, (pad + i * (cell + pad), 2 * pad + cell))
path = os.path.join(OUT, "compare_75.png")
sheet.save(path)
print("ok", path)
