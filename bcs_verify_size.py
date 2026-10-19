# -*- coding: utf-8 -*-
"""校验编制标志：I/II/III 的竖杠高度与 X 的叉高是否一致（600px 直出量墨迹）。"""
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
print(f"{'标志':>6}{'墨迹高':>8}{'墨迹宽':>8}{'顶端':>7}{'底端':>7}")
for sym in ["I", "II", "III", "X"]:
    ct = R.Counter(kind="inf", unit_id="1/1", formation_id="DEMO", size_label=sym,
                   ar="5", quality="3", ma="4", symbol="inf", symbol_mode="letter",
                   bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, 600, ss=1)
    a = np.array(img.convert("RGB")).astype(int)
    dark = (a[:, :, 0] < 70) & (a[:, :, 1] < 70) & (a[:, :, 2] < 70)
    # 只取规模标志那一片：x 33~41.6, y 8~15.8（避开符号框上边框）
    sub = dark[int(8 * U):int(15.8 * U), int(33 * U):int(41.6 * U)]
    ys, xs = np.where(sub)
    if len(ys) == 0:
        print(sym, "空")
        continue
    h = (ys.max() - ys.min() + 1) / U
    w = (xs.max() - xs.min() + 1) / U
    print(f"{sym:>6}{h:>8.2f}{w:>8.2f}{8 + ys.min() / U:>7.2f}{8 + ys.max() / U:>7.2f}")

print("\n设计：竖杠高 7.0（cy±3.5）；叉的 half 已改为 3.5 → 叉高同为 7.0")
