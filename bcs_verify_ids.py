# -*- coding: utf-8 -*-
"""校验左右两列番号/编制：字号是否一致、是否顶出上端、是否过小。"""
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

CASES = [
    ("2", "110/28"), ("19", "C/64"), ("06", "10 Arm"), ("GebJg", "1 GJ"),
    ("14/1", "2 Inf"), ("II/505", "10 GD"), ("1.1/10", "Pape"), ("2", "10 GD"),
]


def dark_mask(img):
    a = np.array(img.convert("RGB")).astype(int)
    return (a[:, :, 0] < 70) & (a[:, :, 1] < 70) & (a[:, :, 2] < 70)


def bbox(mask, x0, x1, y0, y1):
    sub = mask[int(y0 * U):int(y1 * U), int(x0 * U):int(x1 * U)]
    ys, xs = np.where(sub)
    if len(ys) == 0:
        return None
    return (x0 + xs.min() / U, y0 + ys.min() / U, x0 + xs.max() / U, y0 + ys.max() / U)


print(f"{'左番号':>9}{'右编制':>9}{'左字面':>7}{'右字面':>7}{'左顶':>6}{'右顶':>6}"
      f"{'左底':>6}{'右底':>6}{'字号':>6}  判定")
rows = []
for uid, form in CASES:
    ct = R.Counter(kind="av", unit_id=uid, formation_id=form, ar="6", av="3", ma="14",
                   quality="3", hard=True, symbol="armor", symbol_mode="letter",
                   bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, 600, ss=1)
    m = dark_mask(img)
    lb = bbox(m, 3, 21.5, 3, 45)     # 左列：取符号框左侧
    rb = bbox(m, 51, 72.5, 3, 45)    # 右列：取符号框右侧
    lh = (lb[2] - lb[0]) if lb else 0
    rh = (rb[2] - rb[0]) if rb else 0
    size = R.fit_id_size(R.Ctx(img, U, "#000"), [uid, form], R.L["ID_SIZE"],
                         R.L["ID_MAXLEN"], R.L["ID_MAXH"])
    top_ok = min(lb[1], rb[1]) >= 3.5
    ok = abs(lh - rh) <= 0.5 and top_ok and size >= 9.0
    rows.append((uid, form, lh, rh, lb, rb, size, ok))
    print(f"{uid:>9}{form:>9}{lh:>7.2f}{rh:>7.2f}{lb[1]:>6.1f}{rb[1]:>6.1f}"
          f"{lb[3]:>6.1f}{rb[3]:>6.1f}{size:>6.2f}  {'一致' if ok else '检查'}"
          f"{'' if abs(lh-rh) <= 0.5 else ' ←两侧字面不等'}"
          f"{'' if top_ok else ' ←顶出上沿'}"
          f"{'' if size >= 9.0 else ' ←字号偏小'}")

print("\n设计值：ID_SIZE=%.1f（上限） ID_MAXLEN=%.1f ID_MAXH=%.1f ID_Y=%.1f"
      % (R.L["ID_SIZE"], R.L["ID_MAXLEN"], R.L["ID_MAXH"], R.L["ID_Y"]))

S = 8
pad = 14
cell = 75 * S
sheet = Image.new("RGB", (len(rows) * cell + (len(rows) + 1) * pad, cell + 54), (26, 26, 30))
d = ImageDraw.Draw(sheet)
for i, (uid, form, lh, rh, lb, rb, size, ok) in enumerate(rows):
    ct = R.Counter(kind="av", unit_id=uid, formation_id=form, ar="6", av="3", ma="14",
                   quality="3", hard=True, symbol="armor", symbol_mode="letter",
                   bg="#7E9B3D", bar_pos="none")
    img = R.render(ct, 75).resize((cell, cell), Image.NEAREST)
    x = pad + i * (cell + pad)
    sheet.paste(img, (x, 30))
    d.text((x + cell / 2, 8), f"{uid} / {form}", fill="#eee", anchor="ma",
           font=R.font("narrow_b", 19))
    d.text((x + cell / 2, cell + 36), f"字面 {lh:.1f} = {rh:.1f} · 字号 {size:.1f}",
           fill="#9ad0ff", anchor="ma", font=R.font("narrow", 15))
path = os.path.join(OUT, "id_symmetry.png")
sheet.save(path)
print("对照图 →", path)
