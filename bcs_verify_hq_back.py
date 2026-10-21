# -*- coding: utf-8 -*-
"""量 HQ 激活面：炮击值 vs 移动力的墨迹高度与中心线，确认「移动力略大、中心对齐」。

测量口径 —— 差分渲染（v1.6.0 起这两个数值上色方式不同，任何一种颜色掩膜都会踩坑）：
  · 炮击值  —— _hq_num()：黑字 #101010 + 白描边
  · 移动力  —— draw_badged_value(..., MOVE_CLASS_STYLE[move_class], ...)：
              tac 红字 #B3202A / leg 白字 #FFFFFF / truck 近黑 #1A1A1A
  「黑墨」掩膜对红字/白字直接取空（老版本就是这样抛 TypeError 的）；而按「偏离底色」
  取又会把背面白带和底部斜面高光算成墨迹。所以这里渲染两遍 —— 正常 vs
  该数值清空 —— 逐像素取差异，差异区即该数值的完整墨迹（含描边），与配色无关。
"""
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
ON = "#7E9B3D"                      # 算子底色
SPLIT = 44.0                        # 左右分界：< 44 归炮击值，>= 44 归移动力

TOL_H = 0.5                         # 墨迹高 vs 设计目标（格）
TOL_RATIO = 0.06                    # 高度比 vs HQ_MA_SCALE
TOL_C = 0.30                        # 中心线 / 中心漂移（格）

# 版式契约（v1.6.0 实测值，随内容整体缩放 CONTENT_SCALE 等比放大）。有意改 L 里这几个
# 常量时，这里必须同步改 —— 红了是在提醒你确认「改版式」而不是「画歪了」。
_K = float(getattr(R, "CONTENT_SCALE", 1.0))
_AX, _AY = R.SCALE_AX, R.SCALE_AY


def _scaled(pt):
    """把设计坐标换算成缩放后的实际坐标"""
    return (_AX + (pt[0] - _AX) * _K, _AY + (pt[1] - _AY) * _K)
EXPECT_ART_H = 13.60 * _K            # = HQ_NUM_H * CONTENT_SCALE
EXPECT_MA_H = 19.72 * _K             # = HQ_NUM_H * HQ_MA_SCALE * CONTENT_SCALE
EXPECT_RATIO = 1.45                  # = HQ_MA_SCALE（比值与缩放无关）


def make_hq(arty="4", ma="8", move_class="tac"):
    return R.Counter(kind="hq", side="back", command_radius="10", formation_id="",
                     activation="4", arty=arty, ma=ma, bg=ON, bar_color="#6E8B3D",
                     move_class=move_class)


def pixels(ct):
    return np.array(R.render(ct, 600, ss=1).convert("RGB")).astype(int)


def bbox(mask):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    return (xs.min() / U, ys.min() / U, xs.max() / U, ys.max() / U)


def probe(ma_txt, mc):
    """返回 (炮击值墨迹框, 移动力墨迹框)；测不到的返回 None。"""
    full = pixels(make_hq(arty="4", ma=ma_txt, move_class=mc))
    blank = pixels(make_hq(arty="", ma="", move_class=mc))
    diff = np.abs(full - blank).max(axis=2) > 0
    xs = np.arange(diff.shape[1]) / U
    return bbox(diff & (xs < SPLIT)[None, :]), bbox(diff & (xs >= SPLIT)[None, :])


art_des = R.L["HQ_NUM_H"]
ma_des = R.L["HQ_NUM_H"] * R.L["HQ_MA_SCALE"]
print(f"契约：炮击墨迹高 {EXPECT_ART_H:.2f} · 移动力墨迹高 {EXPECT_MA_H:.2f} · 高度比 {EXPECT_RATIO:.2f}")
print(f"设计：炮击墨迹高 {art_des:.2f} · 移动力墨迹高 {ma_des:.2f}"
      f"（HQ_NUM_H {R.L['HQ_NUM_H']} × HQ_MA_SCALE {R.L['HQ_MA_SCALE']}）"
      f"{'' if (abs(art_des-EXPECT_ART_H) <= TOL_H and abs(ma_des-EXPECT_MA_H) <= TOL_H) else '  ← 常量变了：确认版式后同步改 EXPECT_*'}")
print(f"      炮击中心 {R.L['HQ_ARTY_B']} · 移动力中心 {R.L['HQ_MA_B']}\n")

print(f"{'用例':>12}{'炮击高':>8}{'移动力高':>9}{'高度比':>7}"
      f"{'炮击中心y':>10}{'移动力中心y':>11}{'中心差':>7}  判定")

ok_all = True
for ma_txt, mc in (("8", "tac"), ("8", "leg"), ("8", "truck"), ("12", "tac")):
    art, ma = probe(ma_txt, mc)
    if art is None or ma is None:
        side = "炮击值" if art is None else "移动力"
        print(f"{ma_txt + '/' + mc:>12}  ← {side}取不到墨迹（掩膜或版式变了）")
        ok_all = False
        continue

    ha = art[3] - art[1] + 1 / U
    hm = ma[3] - ma[1] + 1 / U
    ca = (art[1] + art[3]) / 2
    cm = (ma[1] + ma[3]) / 2
    cxa = (art[0] + art[2]) / 2
    cxm = (ma[0] + ma[2]) / 2
    ratio = hm / ha
    d_ha, d_hm = abs(ha - EXPECT_ART_H), abs(hm - EXPECT_MA_H)
    d_ratio = abs(ratio - EXPECT_RATIO)
    d_c = abs(ca - cm)
    _ab = _scaled(R.L["HQ_ARTY_B"])
    _mb = _scaled(R.L["HQ_MA_B"])
    d_ca = abs(ca - _ab[1])
    d_cm = abs(cm - _mb[1])
    d_xa = abs(cxa - _ab[0])
    d_xm = abs(cxm - _mb[0])
    ok = (d_ha <= TOL_H and d_hm <= TOL_H and d_ratio <= TOL_RATIO and d_c <= TOL_C
          and d_ca <= TOL_C and d_cm <= TOL_C and d_xa <= TOL_C and d_xm <= TOL_C)
    ok_all = ok_all and ok
    print(f"{ma_txt + '/' + mc:>12}{ha:>8.2f}{hm:>9.2f}{ratio:>7.3f}"
          f"{ca:>10.2f}{cm:>11.2f}{d_c:>7.2f}  {'一致' if ok else '检查'}"
          f"{'' if d_ha <= TOL_H else ' ←炮击高偏离设计'}"
          f"{'' if d_hm <= TOL_H else ' ←移动力高偏离设计'}"
          f"{'' if d_ratio <= TOL_RATIO else ' ←高度比偏离 %0.2f' % EXPECT_RATIO}"
          f"{'' if d_c <= TOL_C else ' ←中心线不齐'}"
          f"{'' if d_ca <= TOL_C else ' ←炮击中心漂移'}"
          f"{'' if d_cm <= TOL_C else ' ←移动力中心漂移'}"
          f"{'' if d_xa <= TOL_C else ' ←炮击水平偏心'}"
          f"{'' if d_xm <= TOL_C else ' ←移动力水平偏心'}")

print(f"\n容差：墨迹高 ±{TOL_H} 格 · 高度比 ±{TOL_RATIO} · 中心 ±{TOL_C} 格")
print("总体：", "全部通过" if ok_all else "有偏差，见上面「检查」行")
sys.exit(0 if ok_all else 1)
