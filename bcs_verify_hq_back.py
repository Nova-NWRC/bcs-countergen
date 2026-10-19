# -*- coding: utf-8 -*-
"""量 HQ 激活面：炮击值 vs 移动力的墨迹高度与中心线，确认“移动力略大、中心对齐”。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

U = 600 / 75.0
HQ = R.Counter(kind="hq", side="back", command_radius="10", formation_id="",
               activation="4", arty="4", ma="8", bg="#7E9B3D", bar_color="#6E8B3D")
img = R.render(HQ, 600, ss=1)
a = np.array(img.convert("RGB")).astype(int)
dark = (a[:, :, 0] < 70) & (a[:, :, 1] < 70) & (a[:, :, 2] < 70)


def bbox(x0, x1, y0, y1):
    sub = dark[int(y0 * U):int(y1 * U), int(x0 * U):int(x1 * U)]
    ys, xs = np.where(sub)
    if len(ys) == 0:
        return None
    return (x0 + xs.min() / U, y0 + ys.min() / U, x0 + xs.max() / U, y0 + ys.max() / U)


arty = bbox(23, 44, 47, 72)
ma = bbox(45, 70, 47, 72)
for name, b in (("炮击值 4", arty), ("移动力 8", ma)):
    h = b[3] - b[1] + 1 / U
    cy = (b[1] + b[3]) / 2
    print(f"{name}: y {b[1]:5.2f}..{b[3]:5.2f}  高 {h:5.2f}  中心 y {cy:5.2f}"
          f"  x {b[0]:5.2f}..{b[2]:5.2f}")
if arty and ma:
    print(f"\n高度比 = {(ma[3]-ma[1])/(arty[3]-arty[1]):.3f}（应 >1 且 ≈1.12）")
    print(f"中心差 = {abs((arty[1]+arty[3])/2 - (ma[1]+ma[3])/2):.2f} 格（应 ≈0）")
