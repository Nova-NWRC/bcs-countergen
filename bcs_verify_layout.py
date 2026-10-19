# -*- coding: utf-8 -*-
"""按几何方式核对：两位数 AV/MA 与中轴列、编制标志与兵牌上沿的间距。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


class FakeCtx:
    u = 8.0
    d = None


def ink_w(txt, h, fnt):
    """用 _text_tight 的墨迹比例反推设计宽度。"""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    ctx = R.Ctx(img, 8.0, "#000")
    t = R._text_tight(ctx, txt, h * 1.9, "#FFFFFF", "#000000", 0.5, fnt)
    return h * t.width / t.height


CX, FLANK = R.L["CX"], R.L["FLANK"]
print(f"CX={CX} FLANK={FLANK} VAL_H={R.L['VAL_H']} SM_H={R.L['SM_H']}")
print("\n① 两位数数值与中轴列的间距（按墨迹宽度推算）")
for av, ma in (("16", "12"), ("14", "16"), ("3", "16"), ("16", "4")):
    for txt, side in ((av, "左"), (ma, "右")):
        w = ink_w(txt, R.L["VAL_H"], "narrow_b" if len(txt) >= 2 else "black")
        c = CX - FLANK if side == "左" else CX + FLANK
        print(f"  {side}值 {txt:>2}: 宽 {w:5.1f}  跨度 {c - w / 2:5.1f}..{c + w / 2:5.1f}")
    mid_l, mid_r = 35.0, 42.9
    lw = ink_w(av, R.L["VAL_H"], "narrow_b" if len(av) >= 2 else "black")
    rw = ink_w(ma, R.L["VAL_H"], "narrow_b" if len(ma) >= 2 else "black")
    gap_l = mid_l - (CX - FLANK + lw / 2)
    gap_r = (CX + FLANK - rw / 2) - mid_r
    print(f"  → 与中轴间隙 左 {gap_l:+.2f} / 右 {gap_r:+.2f} 格\n")

print("② 编制标志底部 vs 兵牌上沿（几何推算）")
half = 3.0
for sym in ("I", "II", "III", "X", "XX", "XXX"):
    hh = 7.0
    if set(sym) == {"I"}:
        bottom = R.L["SIZE"][1] + hh / 2
    else:
        h2 = 3.0 if len(sym) == 1 else 2.5
        bottom = R.L["SIZE"][1] + h2 + 0.55
    print(f"  {sym:>4}: 标志底 {bottom:5.2f} | 兵牌上沿 {R.L['SYM_BOX'][1]:5.2f}"
          f" → 间隙 {R.L['SYM_BOX'][1] - bottom:+.2f} 格")
hq_half = 3.0
print(f"  HQ XX: 标志底 {R.L['HQ_SIZE'][1] + 2.5 + 0.55:5.2f} | 兵牌上沿 {R.L['HQ_BOX'][1]:5.2f}"
      f" → 间隙 {R.L['HQ_BOX'][1] - (R.L['HQ_SIZE'][1] + 3.05):+.2f} 格")
