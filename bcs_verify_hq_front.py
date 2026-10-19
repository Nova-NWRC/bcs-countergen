# -*- coding: utf-8 -*-
"""量 HQ 正面炮击点数在“兵牌右侧空间”里的水平居中情况。"""
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
ct = R.Counter(kind="hq", command_radius="10", formation_id="", size_label="XX",
               arty="10", symbol="inf", symbol_mode="glyph",
               bg="#7E9B3D", bar_color="#6E8B3D")
img = R.render(ct, 600, ss=1)
a = np.array(img.convert("RGB")).astype(int)
m = (a[:, :, 0] < 70) & (a[:, :, 1] < 70) & (a[:, :, 2] < 70)
x0, x1 = R.L["HQ_BOX"][2], 73.4
wx0, wx1 = 54.0, 72.5
sub = m[int(20 * U):int(45 * U), int(wx0 * U):int(wx1 * U)]
ys, xs = np.where(sub)
lx, rx = wx0 + xs.min() / U, wx0 + xs.max() / U
print(f"右侧空间 {x0:.1f}..{x1:.1f} 中心 {(x0 + x1) / 2:.2f}")
print(f"炮击点数墨迹 {lx:.2f}..{rx:.2f} 中心 {(lx + rx) / 2:.2f}")
print(f"偏移 {(lx + rx) / 2 - (x0 + x1) / 2:+.2f} 格")
