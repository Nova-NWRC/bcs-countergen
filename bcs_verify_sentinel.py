# -*- coding: utf-8 -*-
"""验证 "-" 约定：留空=沿用正面、填 "-"=这一面不画。"""
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

BASE = dict(kind="av", unit_id="I/33", formation_id="10 GD", size_label="II", ar="5",
            av="4", rng="2", ma="16", hard=True, symbol="armor",
            bg="#A3BA68", bar_color="#6E8B3D")


def ink(img, box):
    a = np.array(img.convert("RGB")).astype(int)
    x0, y0, x1, y1 = box
    m = (a[int(y0 * 8):int(y1 * 8), int(x0 * 8):int(x1 * 8)] < 60).any(axis=2)
    return int(m.sum())


cases = [
    ("留空 → 沿用正面", R.Counter(**BASE)),
    ("av_move='-' → 不画 AV", R.Counter(**BASE, av_move="-")),
    ("rng_move='-' → 不画射程", R.Counter(**BASE, rng_move="-")),
    ("ma_move='-' → 不画机动力", R.Counter(**BASE, ma_move="-")),
    ("av_move='3' → 覆盖为 3", R.Counter(**BASE, av_move="3")),
]
print(f"{'情况':<28}{'左值区':>8}{'中轴列':>8}{'右值区':>8}")
for name, ct in cases:
    b = R.render(ct.copy(side="back"), 600, ss=1)
    left = ink(b, (12, 43, 32, 62))
    mid = ink(b, (32, 40, 43, 66))
    right = ink(b, (43.5, 43, 64, 64))
    print(f"{name:<28}{left:>8}{mid:>8}{right:>8}")

print("\n对照（正面，应都有内容）:")
f = R.render(R.Counter(**BASE).copy(side="front"), 600, ss=1)
print(f"{'正面':<28}{ink(f, (12, 43, 32, 62)):>8}{ink(f, (32, 40, 43, 66)):>8}"
      f"{ink(f, (43.5, 43, 64, 64)):>8}")
