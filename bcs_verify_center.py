# -*- coding: utf-8 -*-
"""校验中轴列：素质值与射程是否同字号（墨迹等高）、都居中于中轴，
   以及「两格总高」是否略高于左右大数值。"""
import os
import sys

import numpy as np
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
U = 600 / 75.0

CASES = [("4", "2", ""), ("3", "1", ""), ("5", "4", "9"), ("2", "3", "")]


def dark_mask(img):
    a = np.array(img.convert("RGB")).astype(int)
    return (a[:, :, 0] < 65) & (a[:, :, 1] < 65) & (a[:, :, 2] < 65)


def red_mask(img):
    a = np.array(img.convert("RGB")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (r > 110) & (g < 95) & (b < 95)


def box(mask, x0, x1, y0, y1):
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.where(sub)
    if len(ys) == 0:
        return None
    return (xs.min() + x0, ys.min() + y0, xs.max() + x0, ys.max() + y0)


print(f"{'素质':>4}{'射程':>5}{'素质高':>8}{'射程高':>8}{'两格总高':>10}{'大数值高':>10}"
      f"{'中轴x':>8}  判定")
rows = []
for q, rg, rg2 in CASES:
    ct = R.Counter(kind="av", unit_id="19", formation_id="C/64", ar="6", av="3", ma="14",
                   quality=q, rng=rg, rng2=rg2, hard=True, symbol="armor",
                   symbol_mode="letter", bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, 600, ss=1)
    dm, rm = dark_mask(img), red_mask(img)
    split = int((R.L["Q_Y"] + R.L["R_Y"]) / 2 * U)
    qb = box(dm, int(32.2 * U), int(42.8 * U), int(38 * U), split)
    rb = box(dm, int(32.2 * U), int(42.8 * U), split, int(72 * U))
    big = box(rm, int(4 * U), 300, int(38 * U), int(72 * U))
    qh = (qb[3] - qb[1] + 1) / U if qb else 0
    rh = (rb[3] - rb[1] + 1) / U if rb else 0
    tot = ((rb[3] - qb[1] + 1) / U) if (qb and rb) else qh + rh
    bh = (big[3] - big[1] + 1) / U if big else 0
    cx = ((qb[0] + qb[2]) / 2 / U) if qb else 0
    cnt = (rb[0] + rb[2]) / 2 / U if rb else 0
    ok = abs(qh - rh) <= 0.2 and abs(cx - 37.5) <= 0.6 and abs(cnt - 37.5) <= 0.6
    if rg2:      # 射程两行：按“两行合计 ≈ 一格高”判定
        ok = abs(rh - R.L["SM_H"]) <= 0.8 and abs(cx - 37.5) <= 0.6
    rows.append((q, rg, rg2, qh, rh, tot, bh, cx, cnt, ok))
    print(f"{q:>4}{rg:>5}{qh:>8.2f}{rh:>8.2f}{tot:>10.2f}{bh:>10.2f}"
          f"{cx:>8.2f}  {'一致' if ok else '不一致'}"
          f"{'' if abs(qh-rh) <= 0.2 or rg2 else ' ←两格字高不同'}"
          f"{'' if tot > bh else ' ←总高未超过大数值'}")

print("\n设计值：SM_H=%.1f SM_GAP=%.1f → 两格总高 %.1f；VAL_H=%.1f"
      % (R.L["SM_H"], R.L["SM_GAP"], 2 * R.L["SM_H"] + R.L["SM_GAP"], R.L["VAL_H"]))

# 标尺图
S = 8
pad = 14
cell = 75 * S
sheet = Image.new("RGB", (len(rows) * cell + (len(rows) + 1) * pad, cell + 56), (26, 26, 30))
d = ImageDraw.Draw(sheet)
for i, (q, rg, rg2, qh, rh, tot, bh, cx, cnt, ok) in enumerate(rows):
    ct = R.Counter(kind="av", unit_id="19", formation_id="C/64", ar="6", av="3", ma="14",
                   quality=q, rng=rg, rng2=rg2, hard=True, symbol="armor",
                   symbol_mode="letter", bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, 75).resize((cell, cell), Image.NEAREST)
    x = pad + i * (cell + pad)
    sheet.paste(img, (x, 30))
    for yy in (R.L["Q_Y"] - R.L["SM_H"] / 2, R.L["Q_Y"] + R.L["SM_H"] / 2):
        d.line([(x, 30 + yy * S), (x + cell, 30 + yy * S)], fill=(120, 255, 140), width=1)
    for yy in (R.L["R_Y"] - R.L["SM_H"] / 2, R.L["R_Y"] + R.L["SM_H"] / 2):
        d.line([(x, 30 + yy * S), (x + cell, 30 + yy * S)], fill=(120, 210, 255), width=1)
    for yy in (R.L["VAL_Y"] - R.L["VAL_H"] / 2, R.L["VAL_Y"] + R.L["VAL_H"] / 2):
        d.line([(x, 30 + yy * S), (x + cell, 30 + yy * S)], fill=(255, 210, 80), width=1)
    d.line([(x + 37.5 * S, 30), (x + 37.5 * S, 30 + cell)], fill=(255, 80, 80), width=1)
    d.text((x + cell / 2, 8), f"素质 {q} / 射程 {rg}{('/' + rg2) if rg2 else ''}",
           fill="#eee", anchor="ma", font=R.font("narrow_b", 19))
    d.text((x + cell / 2, cell + 34), f"{tot:.1f} 格 > 大数值 {bh:.1f} 格",
           fill="#9ad0ff", anchor="ma", font=R.font("narrow", 16))
path = os.path.join(OUT, "center_symmetry.png")
sheet.save(path)
print("标尺图 →", path)
