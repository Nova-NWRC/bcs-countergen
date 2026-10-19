# -*- coding: utf-8 -*-
"""校验：装甲值与移动力是否同字号、同字高、关于中轴对称。

做法：渲染后按数值色（深红）取蒙版，分别量左/右半区数字的像素包围盒，
打印 上沿/下沿/高度/中心，并生成带标尺的对照图 samples/value_symmetry.png。
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)

CASES = [
    ("单/双位数", dict(av="3", ma="14")),
    ("双/单", dict(av="14", ma="4")),
    ("双/双", dict(av="16", ma="12")),
    ("单/单", dict(av="5", ma="8")),
    ("窄字符 1", dict(av="1", ma="11")),
]


def red_mask(img):
    a = np.array(img.convert("RGB")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (r > 110) & (g < 95) & (b < 95)


def bbox(mask, x0, x1, y0, y1):
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.where(sub)
    if len(ys) == 0:
        return None
    return (int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + x0, int(ys.max()) + y0)


def measure(spec, factor=8):
    ct = R.Counter(kind="av", unit_id="19", formation_id="C/64", size_label="II",
                   ar="6", quality="3", rng="", hard=True, symbol="armor",
                   symbol_mode="letter", bg="#7E9B3D", bar_pos="none", **spec)
    img = R.render(ct, 75 * factor, ss=2).resize((75, 75), Image.LANCZOS)
    m = red_mask(img)
    left = bbox(m, 0, 37, 36, 75)
    right = bbox(m, 38, 75, 36, 75)
    return img, left, right


def main():
    rows = []
    imgs = []
    for name, spec in CASES:
        img, L, Rr = measure(spec)
        imgs.append((name, spec, img, L, Rr))
        lh = L[3] - L[1] + 1 if L else 0
        rh = Rr[3] - Rr[1] + 1 if Rr else 0
        lc = (L[1] + L[3]) / 2 if L else 0
        rc = (Rr[1] + Rr[3]) / 2 if Rr else 0
        rows.append((name, spec["av"], spec["ma"], lh, rh, lc, rc,
                     round((L[0] + L[2]) / 2, 1) if L else 0,
                     round((Rr[0] + Rr[2]) / 2, 1) if Rr else 0))

    print(f"{'用例':<10}{'AV':>4}{'MA':>5}{'左高':>6}{'右高':>6}{'左中线':>8}{'右中线':>8}"
          f"{'左心x':>8}{'右心x':>8}  判定")
    ok_all = True
    for name, av, ma, lh, rh, lc, rc, lx, rx in rows:
        same_h = (lh == rh)
        same_line = abs(lc - rc) <= 1
        ok = same_h and same_line
        ok_all &= ok
        print(f"{name:<10}{av:>4}{ma:>5}{lh:>6}{rh:>6}{lc:>8.1f}{rc:>8.1f}"
              f"{lx:>8.1f}{rx:>8.1f}  {'一致' if ok else '不一致'}"
              f"{'' if same_h else ' ←字高不同'}")
    print("\n中轴 37.5；左心/右心到中轴的距离差 =",
          round(abs((37.5 - rows[0][7]) - (rows[0][8] - 37.5)), 1))
    print("总体：", "全部同高同基线" if ok_all else "存在差异")

    # 生成带标尺的对照图
    S = 8
    pad = 14
    cell = 75 * S
    n = len(imgs)
    sheet = Image.new("RGB", (n * cell + (n + 1) * pad, cell + 60), (26, 26, 30))
    d = ImageDraw.Draw(sheet)
    for i, (name, spec, img, L, Rr) in enumerate(imgs):
        x = pad + i * (cell + pad)
        big = img.resize((cell, cell), Image.NEAREST)
        sheet.paste(big, (x, 34))
        for side, bb, col in (("L", L, (0, 255, 120)), ("R", Rr, (0, 200, 255))):
            if not bb:
                continue
            for yy in (bb[1], bb[3]):
                d.line([(x, 34 + yy * S), (x + cell, 34 + yy * S)], fill=col, width=1)
            d.line([(x + (bb[0] + bb[2]) // 2 * S, 34 + bb[1] * S),
                    (x + (bb[0] + bb[2]) // 2 * S, 34 + bb[3] * S)], fill=col, width=1)
        d.text((x + cell / 2, 10), f'{spec["av"]} / {spec["ma"]}', fill="#e8e8e8",
               anchor="ma", font=R.font("narrow_b", 20))
        d.text((x + cell / 2, 34 + cell + 6),
               f"高度 {L[3]-L[1]+1}px = {Rr[3]-Rr[1]+1}px", fill="#9ad0ff",
               anchor="ma", font=R.font("narrow", 16))
    path = os.path.join(OUT, "value_symmetry.png")
    sheet.save(path)
    print("对照图 →", path)


if __name__ == "__main__":
    main()
