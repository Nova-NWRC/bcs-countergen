# -*- coding: utf-8 -*-
"""量 HQ 正/反面的内容上下留白，确认整体居中。"""
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
HQ = R.Counter(kind="hq", command_radius="10", formation_id="30 Inf", size_label="X",
               activation="4", arty="4", ma="8", symbol="inf", symbol_mode="glyph",
               bg="#7E9B3D", bar_color="#6E8B3D")

for side in ("front", "back"):
    img = R.render(HQ.copy(side=side), 600, ss=1)
    a = np.array(img.convert("RGB")).astype(int)
    dark = (a[:, :, 0] < 60) & (a[:, :, 1] < 60) & (a[:, :, 2] < 60)
    inner = dark[int(3 * U):int(72 * U), int(3 * U):int(72 * U)]
    ys, xs = np.where(inner)
    top = 3 + ys.min() / U
    bot = 3 + ys.max() / U
    print(f"{side:>6}: 内容 y {top:5.1f} .. {bot:5.1f}  "
          f"上留白 {top:4.1f}  下留白 {72 - bot:4.1f}  高 {bot - top:5.1f}")
print("计数器 75 高；理想上/下留白相等")
