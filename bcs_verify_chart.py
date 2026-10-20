# -*- coding: utf-8 -*-
"""校验编制卡（Formation Chart）：版式几何、色带、文字区域、可复现性与导出接线。

设计口径（对照 BCS 官方编制卡 250×356 量得）：
  网格外框 x 18..231、y 18..336，中缝 x 124.5，横线 y 124 / 230
  每格 106..107 见方，比 75px 算子大 → 支援/标记算子放得下
  编制色带 y 300..324 画在 Support 格下部，两侧顶到网格边线
"""
import hashlib
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bcs_army as A  # noqa: E402
import bcs_chart as C  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SIZE = 250
BG = "#A3BA68"
BAND = "#A63A6B"
fails = []


def check(name, ok, detail=""):
    print(f"{'一致' if ok else '不一致'} · {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


img = C.render_chart("90 Inf Div", symbol="armor", bg=BG, band=BAND, size=SIZE)
a = np.array(img.convert("RGB")).astype(int)

# ① 尺寸与比例
exp_h = int(round(C.CH["H"] * SIZE / C.CH["W"]))
check("输出尺寸", img.size == (SIZE, exp_h), f"{img.size} vs ({SIZE}, {exp_h})")

# ② 网格线位置（在网格中段取一行/一列，找暗线中心）
def line_positions(vals, thresh=90):
    idx = [i for i, v in enumerate(vals) if v < thresh]
    groups = []
    for i in idx:
        if groups and i - groups[-1][-1] <= 2:
            groups[-1].append(i)
        else:
            groups.append([i])
    return [sum(g) / len(g) for g in groups]


row = a[int(80), :, :].mean(axis=1)          # 穿过第 1 行的竖线
col = a[:, int(30), :].mean(axis=1)          # 穿过左列的横线
vx = line_positions(row)
hy = line_positions(col)
def near(vals, target, tol=2.0):
    return any(abs(v - target) <= tol for v in vals)

check("竖线在 18 / 124.5 / 231", near(vx, 18) and near(vx, 124.5) and near(vx, 231),
      f"{[round(v, 1) for v in vx]}")
check("横线在 18 / 124 / 230 / 336",
      near(hy, 18) and near(hy, 124) and near(hy, 230) and near(hy, 336),
      f"{[round(v, 1) for v in hy]}")

# ③ 格子比算子大
cell_w = C.CH["COL"] - C.CH["GX0"]
cell_h = C.CH["R1"] - C.CH["GY0"]
check("格子 ≥ 算子尺寸", cell_w >= 75 and cell_h >= 75,
      f"{cell_w:.1f}×{cell_h:.1f} vs 75")

# ④ 编制色带：在 y 300..324 内、两侧顶到网格边线，且是给定颜色
band_px = a[int(312), int(30)]
check("色带颜色", tuple(band_px) == (0xA6, 0x3A, 0x6B), f"{tuple(int(v) for v in band_px)}")
left_edge = a[int(312), int(C.CH["GX0"]) + 5]
right_edge = a[int(312), int(C.CH["GX1"]) - 6]
check("色带顶到两边", tuple(left_edge) == tuple(band_px) == tuple(right_edge),
      f"左{tuple(int(v) for v in left_edge)} 右{tuple(int(v) for v in right_edge)}")
above = a[int(C.CH["BAND_Y0"]) - 4, int(60)]
below = a[int(C.CH["BAND_Y1"]) + 5, int(60)]
check("色带上下仍为底色", tuple(above) == (0xA3, 0xBA, 0x68) == tuple(below),
      f"上{tuple(int(v) for v in above)} 下{tuple(int(v) for v in below)}")

# ⑤ 五块文字区域都有墨迹（用与底色的差判断）
def has_ink(box):
    x0, y0, x1, y1 = [int(v) for v in box]
    sub = a[y0:y1, x0:x1]
    diff = np.abs(sub - np.array([0xA3, 0xBA, 0x68])).max(axis=2)
    return int((diff > 60).sum())


for name, box in (("Fatigue", (C.CH["COL"] + 4, C.CH["GY0"] + 4, C.CH["GX1"] - 4, C.CH["R1"] - 4)),
                  ("Artillery", (C.CH["GX0"] + 4, C.CH["R1"] + 4, C.CH["COL"] - 4, C.CH["R2"] - 4)),
                  ("Prepared", (C.CH["COL"] + 4, C.CH["R1"] + 4, C.CH["GX1"] - 4, C.CH["R2"] - 4)),
                  ("Support", (C.CH["GX0"] + 4, C.CH["R2"] + 4, C.CH["GX1"] - 4, C.CH["BAND_Y0"] - 4)),
                  ("编制名", (C.CH["GX0"] + 4, C.CH["R1"] - 26, C.CH["COL"] - 4, C.CH["R1"] - 4))):
    n = has_ink(box)
    check(f"{name} 有文字", n > 60, f"{n} 像素")

# ⑥ 徽标（兵种符号）画在左上格上部
badge = has_ink((C.CH["GX0"] + 4, C.CH["GY0"] + 4, C.CH["COL"] - 4, C.CH["R1"] - 30))
check("左上格有徽标", badge > 60, f"{badge} 像素")

# ⑦ 深底自动换浅墨
dark = C.render_chart("Dark", symbol="inf", bg="#1A1A18", band="#8C8C8C", size=SIZE)
da = np.array(dark.convert("RGB")).astype(int)
sub = da[int(C.CH["GY0"]) + 6:int(C.CH["R1"]) - 6, int(C.CH["COL"]) + 6:int(C.CH["GX1"]) - 6]
light_frac = float((sub.mean(axis=2) > 150).mean())
check("深底用浅墨", light_frac > 0.02, f"浅色笔画占比 {light_frac * 100:.1f}%")

# ⑧ 可复现
h1 = hashlib.sha256(img.tobytes()).hexdigest()[:16]
h2 = hashlib.sha256(C.render_chart("90 Inf Div", symbol="armor", bg=BG, band=BAND,
                                   size=SIZE).tobytes()).hexdigest()[:16]
check("两次渲染同图", h1 == h2, h1)

# ⑨ 导出接线：每个编制一张 + 总览；export_army(charts=True) 会带上
out = os.path.join(HERE, "out", "_chart_check")
army = A.load_army(os.path.join(HERE, "samples", "army_demo.json"))
res = C.export_charts(army, out, size=SIZE)
want = len(army["formations"]) + 1
check("导出张数", res["count"] == len(army["formations"]) and len(res["files"]) == want,
      f"{res['count']} 张 / {len(res['files'])} 文件（期望 {want}）")
check("有总览图", os.path.exists(os.path.join(out, "_charts_sheet.png")))

out2 = os.path.join(HERE, "out", "_chart_check2")
r2 = A.export_army(army, out2, size=75, charts=True)
n_chart = len([f for f in r2["files"] if f.endswith("__chart.png")])
check("export_army(charts=True) 带编制卡", n_chart == len(army["formations"]), f"{n_chart} 张")

print()
if fails:
    print("失败项：", "、".join(fails))
    sys.exit(1)
print("全部一致")
