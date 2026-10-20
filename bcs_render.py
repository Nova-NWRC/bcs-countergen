# -*- coding: utf-8 -*-
"""
BCS 算子生成器 —— 渲染核心
版式严格对照 BCS 系列 Unit Key (BCSV/Unit Key.png)：
  行动值框(AR) / 单位规模 / 兵种符号框(Hard=黄框, Not Hard=白框) / 左竖排番号 / 右竖排编制
  / 底部机动色带 + 装甲值(AV) / 射程 / 机动力(MA) / 突击箭头 / HQ 指挥半径·激活值 / 辎重(KG)
画布坐标全部使用 75×75 的“设计单位”，内部按目标像素 × 超采样倍数放大，最后 LANCZOS 降采样，
这样 75px 的原尺寸也能得到干净的抗锯齿边缘。
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 常量与字体
DESIGN = 75.0
FONT_DIR = r"C:\Windows\Fonts"
FONTS = {
    "narrow_b": os.path.join(FONT_DIR, "ARIALNB.TTF"),   # Arial Narrow Bold —— 番号/编制
    "narrow": os.path.join(FONT_DIR, "ARIALN.TTF"),      # Arial Narrow
    "black": os.path.join(FONT_DIR, "ariblk.ttf"),       # Arial Black —— 大数值
    "impact": os.path.join(FONT_DIR, "impact.ttf"),      # Impact —— 超粗数值
    "stencil": os.path.join(FONT_DIR, "STENCIL.TTF"),    # 模板字
    "italic": os.path.join(FONT_DIR, "ariali.ttf"),      # Arial Italic —— 编制卡的固定标签
    "italic_b": os.path.join(FONT_DIR, "arialbi.ttf"),   # Arial Bold Italic
}

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(name: str, px: int) -> ImageFont.FreeTypeFont:
    px = max(4, int(px))
    key = (name, px)
    if key not in _font_cache:
        path = FONTS.get(name) or FONTS["narrow_b"]
        try:
            _font_cache[key] = ImageFont.truetype(path, px)
        except Exception:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


# ---------------------------------------------------------------- 颜色工具
def hx(c: str) -> tuple[int, int, int]:
    c = (c or "#808080").lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def tohex(c) -> str:
    if isinstance(c, str):
        return c if c.startswith("#") else "#" + c
    return "#%02X%02X%02X" % tuple(int(v) for v in c[:3])


def mix(a, b, t: float):
    a, b = hx(a) if isinstance(a, str) else a, hx(b) if isinstance(b, str) else b
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def lighten(c, t: float):
    return mix(c, (255, 255, 255), t)


def darken(c, t: float):
    return mix(c, (0, 0, 0), t)


def luma(c) -> float:
    r, g, b = hx(c) if isinstance(c, str) else c
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def readable_ink(bg, dark="#1A1A1A", light="#FFFFFF") -> str:
    return dark if luma(bg) > 0.45 else light


# ---------------------------------------------------------------- 预设
BG_PRESETS = {
    "US 美军":        ("#B7D5EC", "#3C6FB4"),
    "US 空降":        ("#C8DEEE", "#4C7FBF"),
    "英军":           ("#F2DCB0", "#C08A3E"),
    "德军 野战灰":     ("#A3BA68", "#5E7A33"),
    "德军 装甲(深绿)":  ("#7E9B4B", "#42591F"),
    "德军 党卫军":     ("#9AA46C", "#5A6437"),
    "苏军":           ("#C9A6A0", "#9E2B26"),
    "意军":           ("#C9CCB6", "#6E7A5A"),
    "日军":           ("#E9D6B8", "#8A5B2A"),
    "以军":           ("#C3D8EE", "#2F5FA8"),
    "阿军":           ("#D6BAAC", "#8C4A2F"),
    "中立 灰":        ("#BFC0B6", "#6E6F63"),
    "深色 黑底":       ("#23201E", "#8C8C8C"),
    "纸白(打印)":      ("#FFFFFF", "#9A9A9A"),
}

# 编制（师）区分色：同师同色，跨师一眼可辨
FORMATION_COLORS = {
    "红": "#C0392B", "橙": "#D97A20", "黄": "#D8B62A", "橄榄": "#6E8B3D",
    "绿": "#2E7D4F", "青": "#2A8C93", "蓝": "#2F5FA8", "靛": "#3B3F8F",
    "紫": "#7A3E8F", "洋红": "#A63A6B", "棕": "#7A5230", "灰": "#6B6B6B",
}

# 移动力 / 装甲值的「底板色 + 边框 + 字色」（照 Unit Key 的分类配色）
MOVE_CLASS_STYLE = {
    "leg":   dict(fill="#FFFFFF", outline="#101010"),
    "truck": dict(fill="#1A1A1A", outline="#FFFFFF"),
    "tac":   dict(fill="#B3202A", outline="#FFFFFF"),
}
AV_CLASS_STYLE = {
    "red":      dict(fill="#B3202A", outline="#FFFFFF"),
    "limited":  dict(fill=None, outline="#101010"),
    "standoff": dict(fill="#1A1A1A", outline="#FFFFFF"),
    "light":    dict(fill="#FFFFFF", outline="#101010"),
}

MOVE_CLASS = {  # Unit Key 的 Movement Class 配色
    "TAC 战术(16)":  "#C0392B",
    "LEG 徒步(8)":   "#E8C10C",
    "TRUCK 卡车(12)": "#5B8FD6",
    "TRACK 履带":     "#7A6A55",
    "MECH 半履带":    "#8FA8C8",
    "无":            "none",
}

SYMBOLS = [
    ("inf", "步兵 Infantry"), ("mot", "摩托化步兵 Motorized"),
    ("arminf", "装甲步兵/掷弹兵 PG"), ("armor", "装甲 Armor/Pz"),
    ("tiger", "虎式 Tiger"), ("js", "约瑟夫·斯大林 JS"),
    ("light", "轻坦克 Light Tank"), ("td", "坦克歼击车 TD"),
    ("spgun", "自行火炮 SP Gun"), ("stug", "突击炮 StuG"),
    ("sturmtiger", "突击虎 SturmTiger"), ("brummbar", "灰熊 Brummbär"),
    ("cav", "骑兵 Cavalry"), ("recon", "装甲侦察 Arm Recon"),
    ("moto", "摩托车 Motorcycle"), ("eng", "工兵 Engineer"),
    ("armeng", "装甲工兵 Arm Engineer"), ("abn", "空降 Abn"),
    ("mtn", "山地 Mountain"), ("marine", "陆战 Marine"),
    ("glider", "滑翔 Glider"), ("amph", "两栖 Amphibious"),
    ("commando", "突击队 Commando"), ("ski", "滑雪 Ski"),
    ("bicycle", "自行车 Bicycle"), ("mg", "机枪 MG"),
    ("police", "警察 Polizei"), ("flak", "高炮 Flak"),
    ("armaa", "装甲防空 Arm AA"), ("oval", "椭圆(通用/HQ)"),
    ("none", "无符号"), ("text", "文字符号(自定义)"),
]

# 兵种符号 → 字母代号（玩家要求：暂时用字母代替图形）
SYMBOL_LETTERS = {
    "inf": "INF", "mot": "MOT", "arminf": "PG", "armor": "ARM", "tiger": "TIG",
    "js": "JS", "light": "LT", "td": "TD", "spgun": "SPG", "stug": "STG",
    "sturmtiger": "STT", "brummbar": "BRM", "cav": "CAV", "recon": "RCN",
    "moto": "MC", "eng": "ENG", "armeng": "AENG", "abn": "ABN", "mtn": "MTN",
    "marine": "MAR", "glider": "GLD", "amph": "AMP", "commando": "CDO",
    "ski": "SKI", "bicycle": "BIC", "mg": "MG", "police": "POL", "flak": "FLAK",
    "armaa": "AA", "oval": "HQ", "none": "", "text": "",
}

# 北约编制规模（NATO unit size）：竖杠=连/营/团，斜杠=旅/师/军/集团军
SIZE_PRESETS = [
    ("I", "连 Company"),
    ("II", "营 Battalion"),
    ("III", "团 Regiment"),
    ("X", "旅 Brigade"),
    ("XX", "师 Division"),
    ("XXX", "军 Corps"),
    ("KG", "战斗群 Kampfgruppe（BCS 文字）"),
    ("TF", "特遣队 Task Force（BCS 文字）"),
    ("Tm", "小队 Team（BCS 文字）"),
    ("Grp", "集群 Group（BCS 文字）"),
    ("(+)", "加强 Reinforced（BCS 文字）"),
    ("(-)", "缺编 Weak（BCS 文字）"),
]

KINDS = [
    ("av", "AV 装甲单位"),
    ("dual", "Dual 双能力单位"),
    ("inf", "步兵单位"),
    ("hq", "HQ 指挥部"),
    ("train", "Combat Train 辎重"),
    ("support", "支援单位 Support"),
    ("supply", "补给车 Supply Truck"),
    ("marker", "标记/文字算子"),
]


# ---------------------------------------------------------------- 规格
@dataclass
class Counter:
    kind: str = "inf"
    # 基本信息
    unit_id: str = "II/505"
    formation_id: str = "10 GD"
    size_label: str = "II"          # I II III KG TF Tm Grp X XX XXX (+)(-) 等
    name: str = ""                  # HQ / 辎重的大字（如 Peiper / KG）
    # 数值
    ar: str = "5"                   # 顶部小方框（兵力/行动值，按槽位用）
    av: str = ""                    # Armor Value 装甲值
    av_class: str = "red"           # red / limited / standoff / light
    move_class: str = "tac"         # leg / truck / tac
    no_rebuild: bool = False        # 不可补员/重建：素质值下加实心黄圈
    quality: str = ""               # 素质值（中轴上方）
    rng: str = "3"                  # 射程（中轴下方）
    rng2: str = ""                  # 射程第二行（1 格时留空）
    ma: str = "4"                   # Movement Allowance 机动力
    assault: bool = True            # 突击箭头
    hard: bool = False              # Hard（黄框）/ Not Hard（白框）
    breakthrough: bool = False      # 突破型 AV 小三角
    steps: str = ""                 # HQ: 剩余步骤 / AV: Steps Available
    command_radius: str = ""        # HQ 指挥半径
    activation: str = ""            # HQ 激活值
    arty: str = ""                  # HQ 炮兵点数
    # 符号
    symbol: str = "inf"
    symbol_text: str = ""
    symbol_mode: str = "letter"     # letter=字母代号（暂用）/ glyph=图形符号
    symbol_letters: str = ""        # 自定义字母，留空则按 symbol 自动取
    # 配色
    bg: str = "#A3BA68"
    band: str = "#E8C10C"           # 机动色带
    show_band: bool = False         # CS-3 / LB 系算子本身没有机动色带
    bar_color: str = "#C0392B"      # 编制色带（师/编制区分色）
    bar_pos: str = "bottom"         # top / bottom / left / right / none
    bar_thickness: float = 15.0     # 编制色带厚度（设计格，约算子高度 1/5）
    ink: str = ""                   # 主文字色，空=按底色自动
    value_ink: str = ""             # 数值色，空=红字/深色底自动反白
    gloss: bool = True              # 高光斜面
    # 面
    hq_box_tint: bool = True        # HQ 正面兵牌底色是否跟随编制色带
    support_label: str = "Support"  # 支援单位底层大字
    support_values: bool = False    # 支援单位是否在 Support 字样上叠 av/rng 数字
    side: str = "front"             # front 战斗面 / back 移动面（布局完全一致）
    kind_move: str = ""             # 反面的单位类型：留空=沿用 kind；如 av 正面 / support 反面
    ar_move: str = ""               # 移动面的行动值（留空=沿用 ar）
    quality_move: str = ""          # 移动面的素质值（留空=沿用 quality）
    av_move: str = ""               # 移动面的装甲值（留空=沿用 av）
    rng_move: str = ""              # 移动面的射程（留空=沿用 rng）
    rng2_move: str = ""             # 移动面的射程第二行（留空=沿用 rng2）
    ma_move: str = ""               # 移动面的机动力（留空=沿用 ma）
    move_class_move: str = ""       # 移动面的移动力类型 leg/truck/tac（留空=沿用 move_class）
    back_ghost: bool = True         # 移动面是否把 AR 画成虚化样式
    ar_style: str = "box"           # box / disc / ghost / none
    range_style: str = "plain"       # plain=直接印数字 / chip=白底小牌
    # 其他
    note: str = ""

    def copy(self, **kw) -> "Counter":
        d = asdict(self)
        d.update(kw)
        return Counter(**d)


def side_value(move_val, front_val: str) -> str:
    """正/反面的取值规则：留空=沿用正面；"-"=这一面不画；其余=覆盖。"""
    mv = "" if move_val is None else str(move_val).strip()
    if mv == "-":
        return ""
    return mv or (front_val or "")

DEF = Counter()


# ---------------------------------------------------------------- 绘制基元
class Ctx:
    """把设计单位换算成像素，并提供常用画法。"""

    def __init__(self, img: Image.Image, u: float, ink: str):
        self.img = img
        self.d = ImageDraw.Draw(img, "RGBA")
        self.u = u                      # 1 个设计单位 = u 像素
        self.ink = ink

    # 单位换算
    def p(self, v: float) -> float:
        return v * self.u

    def px(self, v: float) -> int:
        return max(1, int(round(v * self.u)))

    # 文本
    def text(self, xy, s, size, color=None, fnt="narrow_b", anchor="mm",
             max_w=None, max_h=None, outline=None, outline_w=1.2, tracking=0.0,
             rotate=0) -> tuple[float, float]:
        if s is None or s == "":
            return (0, 0)
        color = color or self.ink
        size_px = self.p(size)
        # 自适应缩小以塞进给定宽度
        for _ in range(24):
            f = font(fnt, size_px)
            bb = self.d.textbbox((0, 0), s, font=f)
            w = bb[2] - bb[0]
            h = bb[3] - bb[1]
            # 竖排时，字符串长度受 max_h 约束、字高受 max_w 约束
            lim_w, lim_h = (max_h, max_w) if rotate else (max_w, max_h)
            if (lim_w is None or w <= self.p(lim_w)) and (lim_h is None or h <= self.p(lim_h)):
                break
            size_px *= 0.92
            if size_px <= 5:
                break
        f = font(fnt, size_px)
        if rotate:
            return self._text_rotated(xy, s, f, color, outline, outline_w, rotate, anchor,
                                      tracking, max_w)
        if tracking:
            return self._text_tracked(xy, s, f, color, tracking, anchor, outline, outline_w)
        stroke = self.p(outline_w) if outline else 0
        self.d.text((self.p(xy[0]), self.p(xy[1])), s, font=f, fill=color, anchor=anchor,
                    stroke_width=int(stroke), stroke_fill=outline)
        return (size_px / self.u, w if 'w' in dir() else 0)

    def _text_tracked(self, xy, s, f, color, tracking, anchor, outline, outline_w):
        widths = [self.d.textlength(ch, font=f) for ch in s]
        total = sum(widths) + self.p(tracking) * (len(s) - 1)
        x = self.p(xy[0])
        if anchor[0] == "m":
            x -= total / 2
        elif anchor[0] == "r":
            x -= total
        y = self.p(xy[1])
        stroke = self.p(outline_w) if outline else 0
        for ch, w in zip(s, widths):
            a = anchor[1] + "m" if anchor[1] != "m" else "mm"
            a = {"l": "lm", "m": "mm", "r": "rm"}[anchor[1]]
            self.d.text((x, y), ch, font=f, fill=color, anchor=a,
                        stroke_width=int(stroke), stroke_fill=outline)
            x += w + self.p(tracking)
        return (0, total / self.u)

    def _text_rotated(self, xy, s, f, color, outline, outline_w, rotate, anchor, tracking, max_w):
        """把文本画到临时图上再旋转，得到干净竖排。rotate=90 读作自下而上，-90 自上而下。"""
        bb = self.d.textbbox((0, 0), s, font=f)
        pad = max(4, int(f.size * 0.25))
        w, h = int(bb[2] - bb[0]) + pad * 2, int(bb[3] - bb[1]) + pad * 2
        tmp = Image.new("RGBA", (max(w, 2), max(h, 2)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        stroke = self.p(outline_w) if outline else 0
        td.text((pad - bb[0], pad - bb[1]), s, font=f, fill=color,
                stroke_width=int(stroke), stroke_fill=outline)
        rot = tmp.rotate(rotate, expand=True, resample=Image.BICUBIC)
        cx, cy = self.p(xy[0]), self.p(xy[1])
        self.img.alpha_composite(rot, (int(cx - rot.width / 2), int(cy - rot.height / 2)))
        self.d = ImageDraw.Draw(self.img, "RGBA")
        return (f.size / self.u, rot.height / self.u)

    # 形状
    def rrect(self, box, r, fill=None, outline=None, width=1.0):
        self.d.rounded_rectangle([self.p(v) for v in box], radius=self.p(r),
                                 fill=fill, outline=outline, width=max(1, int(self.p(width))))

    def rect(self, box, fill=None, outline=None, width=1.0):
        self.d.rectangle([self.p(v) for v in box], fill=fill, outline=outline,
                         width=max(1, int(self.p(width))))

    def line(self, pts, color=None, width=1.2, joint="curve"):
        self.d.line([(self.p(x), self.p(y)) for x, y in pts], fill=color or self.ink,
                    width=max(1, int(self.p(width))), joint=joint)

    def poly(self, pts, fill=None, outline=None, width=1.0):
        self.d.polygon([(self.p(x), self.p(y)) for x, y in pts], fill=fill,
                       outline=outline, width=max(1, int(self.p(width))))

    def ellipse(self, box, fill=None, outline=None, width=1.0):
        self.d.ellipse([self.p(v) for v in box], fill=fill, outline=outline,
                       width=max(1, int(self.p(width))))

    def arc(self, box, a0, a1, color=None, width=1.2):
        self.d.arc([self.p(v) for v in box], a0, a1, fill=color or self.ink,
                   width=max(1, int(self.p(width))))


# ---------------------------------------------------------------- 兵种符号
def draw_symbol(c: Ctx, kind: str, box, color: str, lw: float = 1.8, label: str = ""):
    """box 为设计单位坐标 (x0,y0,x1,y1)：符号一律画在该框内。"""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def X():
        c.line([(x0, y0), (x1, y1)], color, lw)
        c.line([(x0, y1), (x1, y0)], color, lw)

    def oval(k=1.0, thick=0.0, dy=0.0):
        ew, eh = w * 0.52 * k, h * 0.62 * k
        yy = cy + h * dy
        c.ellipse((cx - ew / 2, yy - eh / 2, cx + ew / 2, yy + eh / 2),
                  outline=color, width=max(1, int(lw + thick)))

    k = kind
    if k == "inf":
        X()
    elif k == "mot":
        X()
        r = min(w, h) * 0.13
        for dx in (-1, 1):
            c.ellipse((cx + dx * w * 0.24 - r, y1 - r * 1.4, cx + dx * w * 0.24 + r, y1 + r * 0.6),
                      outline=color, width=lw)
    elif k in ("arminf",):
        X()
        oval(0.62)
    elif k == "armor":
        oval(1.0)
    elif k == "tiger":
        oval(1.0, lw * 1.0)
        ew, eh = w * 0.34, h * 0.40
        c.ellipse((cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2),
                  outline=color, width=max(1, int(lw * 0.55)))
    elif k == "js":
        oval(1.0, lw * 1.1)
        for dx in (-0.13, 0.13):
            c.line([(cx + w * dx, cy - h * 0.14), (cx + w * dx, cy + h * 0.14)], color, lw * 0.7)
    elif k == "light":
        oval(0.66)
        r = min(w, h) * 0.06
        c.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    elif k == "td":
        oval(0.9)
        c.line([(cx - w * 0.16, cy + h * 0.10), (cx, cy - h * 0.12), (cx + w * 0.16, cy + h * 0.10)],
               color, lw)
    elif k == "spgun":
        oval(0.76, 0, dy=0.14)
        c.line([(cx + w * 0.02, cy - h * 0.40), (cx + w * 0.48, cy - h * 0.40)], color, lw * 1.6)
        c.line([(cx + w * 0.42, cy - h * 0.50), (cx + w * 0.42, cy - h * 0.30)], color, lw * 1.2)
    elif k == "stug":
        oval(0.76, 0, dy=0.14)
        c.line([(cx + w * 0.04, cy - h * 0.36), (cx + w * 0.46, cy - h * 0.20)], color, lw * 1.9)
    elif k == "sturmtiger":
        oval(0.80, lw * 0.8, dy=0.14)
        c.line([(cx + w * 0.02, cy - h * 0.36), (cx + w * 0.48, cy - h * 0.36)], color, lw * 2.4)
    elif k == "brummbar":
        oval(0.78, 0, dy=0.16)
        c.line([(cx + w * 0.02, cy - h * 0.24), (cx + w * 0.46, cy - h * 0.24)], color, lw * 2.2)
    elif k == "cav":
        c.line([(x0 + w * 0.10, y1 - h * 0.10), (x1 - w * 0.10, y0 + h * 0.10)], color, lw * 1.4)
    elif k == "recon":
        oval(0.86)
        c.line([(x0, y1), (x1, y0)], color, lw)
    elif k == "moto":
        oval(0.7)
        r = min(w, h) * 0.12
        c.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=lw)
    elif k == "eng":
        c.text((cx, cy), "E", h * 0.86, color, "narrow_b", "mm", max_h=h * 0.9)
    elif k == "armeng":
        oval(0.55)
        c.text((cx, cy), "E", h * 0.62, color, "narrow_b", "mm", max_h=h * 0.7)
    elif k == "abn":
        X()
        c.arc((cx - w * 0.42, y0 - h * 0.30, cx + w * 0.42, y0 + h * 0.42), 200, 340, color, lw)
    elif k == "mtn":
        X()
        c.poly([(cx - w * 0.34, y1), (cx, y1 - h * 0.42), (cx + w * 0.34, y1)], None, color)
    elif k == "marine":
        X()
        c.line([(cx, cy - h * 0.30), (cx, cy + h * 0.28)], color, lw * 0.8)
        c.arc((cx - w * 0.18, cy - h * 0.02, cx + w * 0.18, cy + h * 0.34), 0, 180, color, lw * 0.8)
    elif k == "glider":
        X()
        c.line([(cx + w * 0.10, y0 - h * 0.02), (cx + w * 0.34, y0 - h * 0.30)], color, lw)
    elif k == "amph":
        X()
        for dy in (0.0, 0.12):
            c.arc((x0, y1 - h * 0.30 + h * dy, x1, y1 + h * 0.06 + h * dy), 200, 340, color, lw * 0.9)
    elif k == "commando":
        X()
        c.line([(cx - w * 0.16, cy + h * 0.22), (cx + w * 0.16, cy - h * 0.22)], color, lw * 1.2)
        c.line([(cx - w * 0.20, cy + h * 0.16), (cx - w * 0.10, cy + h * 0.30)], color, lw * 0.9)
    elif k == "ski":
        X()
        c.line([(x0, y1 - h * 0.06), (x1, y1 - h * 0.06)], color, lw * 1.2)
        c.line([(x0, y1 + h * 0.10), (x1, y1 + h * 0.10)], color, lw * 1.2)
    elif k == "bicycle":
        X()
        r = min(w, h) * 0.14
        c.ellipse((cx - r, ye := cy + h * 0.02, cx + r, ye + r * 2), outline=color, width=lw)
    elif k == "mg":
        X()
        r = min(w, h) * 0.09
        c.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    elif k == "police":
        X()
        c.text((cx, cy), "*", h * 0.8, color, "narrow_b", "mm")
    elif k == "flak":
        p0, p1 = (cx - w * 0.34, y1 - h * 0.06), (cx + w * 0.34, y1 - h * 0.06)
        c.line([p0, p1], color, lw)
        c.arc((cx - w * 0.30, y0 + h * 0.02, cx + w * 0.30, y1 - h * 0.06), 200, 340, color, lw)
        c.line([(cx, y1 - h * 0.06), (cx, y0 + h * 0.10)], color, lw)
    elif k == "armaa":
        c.ellipse((cx - w * 0.20, cy - h * 0.16, cx + w * 0.20, cy + h * 0.16), outline=color, width=lw)
        c.line([(x0 + w * 0.06, y1 - h * 0.04), (x1 - w * 0.06, y1 - h * 0.04)], color, lw)
    elif k == "oval":
        oval(1.0)
    elif k == "text":
        c.text((cx, cy), label or "PzJg", h * 0.78, color, "narrow_b", "mm",
               max_w=w * 0.98, max_h=h * 0.95)
    else:  # none
        pass


# ---------------------------------------------------------------- 底板
def draw_plate(c: Ctx, ct: Counter, box=(1.2, 1.2, DESIGN - 1.2, DESIGN - 1.2)):
    bg = ct.bg
    base = hx(bg)
    c.rrect(box, 2.6, fill=base)
    if ct.gloss:
        # 顶部一道亮边 + 底部暗边，模拟 Vassal 算子的斜切高光
        c.rrect((box[0], box[1], box[2], box[3]), 2.6,
                outline=lighten(base, 0.55), width=1.0)
        c.rrect((box[0] + 0.9, box[1] + 0.9, box[2] - 0.9, box[3] - 0.9), 2.2,
                outline=darken(base, 0.28), width=0.9)
        # 顶部渐变反光
        grad = Image.new("L", (1, 26))
        for i in range(26):
            grad.putpixel((0, i), int(46 * max(0.0, 1 - i / 22.0) ** 1.4))
        gw = int(c.p(box[2] - box[0]))
        gh = int(c.p(26))
        sheen = Image.new("RGBA", (max(gw, 2), max(gh, 2)), (255, 255, 255, 0))
        alpha = grad.resize((max(gw, 2), max(gh, 2)))
        sheen.putalpha(alpha)
        c.img.alpha_composite(sheen, (int(c.p(box[0])), int(c.p(box[1]))))
        c.d = ImageDraw.Draw(c.img, "RGBA")


def draw_border(c: Ctx, box=(1.2, 1.2, DESIGN - 1.2, DESIGN - 1.2), ink="#111111"):
    c.rrect(box, 2.6, outline=ink, width=1.1)


# ---------------------------------------------------------------- 色带
def draw_band(c: Ctx, ct: Counter, top: float, bottom: float, color: str):
    c.rect((1.2, top, DESIGN - 1.2, bottom), fill=hx(color))
    c.rect((1.2, top, DESIGN - 1.2, top + 0.7), fill=lighten(color, 0.35))
    c.rect((1.2, bottom - 0.5, DESIGN - 1.2, bottom), fill=darken(color, 0.25))


def draw_bar(c: Ctx, ct: Counter, color: str):
    if ct.bar_pos == "none" or ct.bar_thickness <= 0:
        return
    t = ct.bar_thickness
    if ct.bar_pos == "top":
        c.rect((1.2, 1.2, DESIGN - 1.2, 1.2 + t), fill=hx(color))
    elif ct.bar_pos == "bottom":
        y1 = DESIGN - 2.0                     # 贴底板内沿（留出圆角与边框）
        y0 = max(40.0, y1 - t)                # 上限：别吃掉符号框与中轴列
        c.rect((1.4, y0, DESIGN - 1.4, y1), fill=hx(color))
        c.rect((1.4, y0, DESIGN - 1.4, y0 + 0.8), fill=darken(color, 0.45))   # 上沿暗线
        c.rect((1.4, y0 + 0.8, DESIGN - 1.4, y0 + 1.5), fill=lighten(color, 0.35))
    elif ct.bar_pos == "left":
        c.rect((1.2, 1.2, 1.2 + t, DESIGN - 1.2), fill=hx(color))
    elif ct.bar_pos == "right":
        c.rect((DESIGN - 1.2 - t, 1.2, DESIGN - 1.2, DESIGN - 1.2), fill=hx(color))


# ---------------------------------------------------------------- 版式
# 坐标来自 BCSV/Example 的框选实测（75×75 原图），底部数值区按“关于中轴对称”重排：
#   中轴 CX=37.5；装甲值/移动力或箭头/移动力 分别落在 CX±FLANK 上，字号一致；
#   素质值与射程叠在中轴上（Q_Y 在上、R_Y 在下）。
L = dict(
    AR_BOX=(24.0, 5.0, 31.2, 15.4),
    SIZE=(37.2, 12.1),
    SIZE_TICK=(36.6, 7.0, 36.6, 8.4),
    SYM_BOX=(22.0, 16.4, 50.4, 37.4),
    ID_X=14.8, ID_Y=24.4,          # 左列竖排（自下而上）
    FORM_X=58.6, FORM_Y=24.4,      # 右列竖排（自上而下）
    ID_SIZE=12.4,                  # 两列共用字号
    ID_MAXLEN=32.0,                # 竖排长度上限（设计格），防止顶出上端
    ID_MAXH=11.8,                  # 字面（横向）高度上限
    CX=37.5,                       # 算子中轴
    FLANK=15.6,                    # 左右大数值到中轴的距离（AV/MA 对称）
    VAL_Y=52.6,                    # 左右大数值中心线
    VAL_SIZE=21.0,                 # 左右大数值字号（两侧完全一致）
    VAL_H=16.6,                    # 左右大数值墨迹高度（设计格；两位数不再顶到中轴列）
    VAL_MAXW=16.0,                 # 两位数的可用宽度
    Q_Y=45.4,                      # 素质值墨迹中心（中轴，上方）
    R_Y=57.4,                      # 射程墨迹中心（中轴，下方）
    SM_H=10.4,                     # 中轴两格的统一墨迹高度（素质值=射程，字号相同）
    SM_GAP=1.6,                    # 两格之间的净间距
    ARROW_W=4.2, ARROW_TOP=44.9, ARROW_BOT=59.9,
    ARROW_AV_GAP=13.6,             # 有 AV 时箭头在 AV 左侧再左移这么远
    BAND_TOP=56.0, BAND_BOT=69.0,
    CHIP=(30.4, 38.6, 44.6, 56.2),
    # ---- HQ（取自 HQ Eg 框选实测）
    HQ_RADIUS=(15.6, 14.8),        # 正面/背面：左上指挥范围
    HQ_SIZE=(37.0, 17.0),          # 正面：兵牌上方的规模标志（与兵牌留 0.8 格间隙）
    HQ_BOX=(22.0, 21.3, 52.0, 42.5),   # 正面：兵牌（30 × 21.2，长宽比 1.414:1 ≈ A4）
    HQ_ARTY_F=(63.0, 32.0),        # 正面：炮击点数（兵牌右侧空间的水平中心）
    HQ_NAME_F=(37.2, 55.0),        # 正面：兵牌下方番号
    HQ_DIE=(30.0, 8.6, 45.0, 24.6),    # 背面：激活骰面
    HQ_NAME_B=(37.2, 38.4),        # 背面：中央番号
    HQ_ARTY_B=(33.0, 58.3),        # 背面：番号下方炮击点数
    HQ_MA_B=(55.6, 58.3),          # 背面：炮击点数右侧移动力
    # ---- 补给车（取自 HQ Eg 补给车框选实测）
    SP_FRAME=(13.0, 13.0, 65.0, 49.0),   # 中央黑框
    SP_ARROW=(18.0, 9.6, 62.0, 9.6),     # 顶部行军箭头
    SP_TRUCK_Y=51.2,                     # 车体横杆
    SP_WHEELS=((23.0, 60.0), (50.0, 60.0)),   # 两个轮子中心
    SP_WHEEL_R=7.0,
    SP_TEXT_H=14.2,                      # 框内每行文字墨迹高
    SP_SIGN=(37.0, 31.0, 19.0),          # 禁止标志：中心 + 半径
    # 不可补员/重建：素质值下的实心黄圈（取自 BBC-CS-1-B_78 实测 15 格直径）
    NR_R=7.6, NR_FILL="#FFE400", NR_RING="#3A2222",
    HQ_NUM_H=13.6,                 # HQ 数字墨迹高
    HQ_MA_SCALE=1.45,              # 激活面移动力约为炮击值的 1.45 倍（中心仍对齐）
    HQ_NAME_H=18.0,                # 番号墨迹高度（≈算子高的 0.28，落在 1/3~1/4 之间）
    HQ_NAME_MAXW=58.0,             # 番号可用宽度（超出就横向压缩，得到原图那种瘦高字）
    HQ_BAND_H=30.0,                # 激活面白色水平色带厚度（2/5 算子高）
    HQ_BAND_COLOR="#FBFBF6",
)


def draw_ar(c: Ctx, ct: Counter, ink_value: str, box=None):
    """行动值：Unit Key 的红色描边浅黄小方框。"""
    x0, y0, x1, y1 = box or L["AR_BOX"]
    st = ct.ar_style
    if st == "none" or not ct.ar:
        return
    if st == "box":
        c.rrect((x0, y0, x1, y1), 1.2, fill="#F7E39A", outline="#C0392B", width=1.1)
        c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 0.3), ct.ar, 10.6, "#141414", "black", "mm",
               max_w=(x1 - x0) * 0.92, max_h=(y1 - y0) * 0.94)
    elif st == "disc":
        # 圆牌固定在下方中部（真实的 DF 式画法），正方形框留给 steps
        dx0, dy0, dx1, dy1 = 30.0, 39.4, 44.0, 54.4
        c.ellipse((dx0, dy0, dx1, dy1), fill="#F2C81E", outline="#C0392B", width=1.3)
        c.text(((dx0 + dx1) / 2, (dy0 + dy1) / 2 + 0.4), ct.ar, 10.4, "#141414", "black", "mm",
               max_w=(dx1 - dx0) * 0.78, max_h=(dy1 - dy0) * 0.78)
        if ct.steps:
            c.rrect((x0, y0, x1, y1), 1.2, fill="#F7E39A", outline="#C0392B", width=1.1)
            c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 0.3), ct.steps, 9.0, "#141414", "black", "mm",
                   max_w=(x1 - x0) * 0.86, max_h=(y1 - y0) * 0.86)
    elif st == "ghost":
        # 移动面的行动值：浅底 + 细灰边 + 灰字，表示“次要/虚化”面
        c.rrect((x0, y0, x1, y1), 1.2, fill="#EDEDE6", outline="#6F6F6F", width=1.2)
        c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 0.3), ct.ar, 10.0, "#3F3F3F", "black", "mm",
               max_w=(x1 - x0) * 0.88, max_h=(y1 - y0) * 0.90, outline="#FFFFFF", outline_w=0.5)


def draw_size(c: Ctx, ct: Counter, ink: str):
    """编制规模标志：I/II/III 画竖杠，X/XX/XXX/XXXX 画斜杠（北约规则），其余按文字。"""
    s = (ct.size_label or "").strip()
    if not s:
        return
    cx, cy = L["SIZE"]
    tok = s.replace(" ", "")
    is_nato = bool(tok) and (set(tok) == {"I"} or set(tok) == {"X"})
    if not is_nato:                          # 文字型标志才画上方小竖条，避免与竖杠叠在一起
        tx0, ty0, tx1, ty1 = L["SIZE_TICK"]
        c.line([(tx0, ty0), (tx1, ty1)], ink, 1.6)

    if tok and set(tok) == {"I"}:            # 连 / 营 / 团：竖杠
        n = len(tok)
        gap, h, lw = 2.10, 7.0, 1.55
        x0 = cx - (n - 1) * gap / 2
        for i in range(n):
            c.line([(x0 + i * gap, cy - h / 2), (x0 + i * gap, cy + h / 2)], ink, lw)
    elif tok and set(tok) == {"X"}:          # 旅：画「叉」——两条对角交叉（不是斜杠）
        n = len(tok)
        lw = 1.55
        half = 3.0 if n == 1 else 2.5
        step = 2 * half + (1.2 if n == 1 else 1.0)
        x0 = cx - (n - 1) * step / 2
        for i in range(n):
            gx = x0 + i * step
            c.line([(gx - half, cy - half), (gx + half, cy + half)], ink, lw)
            c.line([(gx - half, cy + half), (gx + half, cy - half)], ink, lw)
    else:                                     # KG / TF / Tm / Grp / (+) / (-) 等
        c.text((cx, cy + 0.2), s, 9.2 if len(s) <= 2 else 7.2, ink, "narrow_b", "mm", max_w=9.6)


def draw_die(c: Ctx, box, value: str, ink: str, pip: str = "#141414"):
    """六面骰的一面：白底方牌 + 按点数排布的黑点。"""
    x0, y0, x1, y1 = box
    c.rrect((x0, y0, x1, y1), 1.2, fill="#FCFCF6", outline=ink, width=1.8)
    try:
        n = max(0, min(6, int(str(value).strip()[:1])))
    except (TypeError, ValueError):
        n = 0
    if not n:
        return
    w, h = x1 - x0, y1 - y0
    lx, cx_, rx = x0 + w * 0.26, x0 + w * 0.5, x0 + w * 0.74
    ty, cy_, by = y0 + h * 0.24, y0 + h * 0.5, y0 + h * 0.76
    layout = {
        1: [(cx_, cy_)],
        2: [(lx, ty), (rx, by)],
        3: [(lx, ty), (cx_, cy_), (rx, by)],
        4: [(lx, ty), (rx, ty), (lx, by), (rx, by)],
        5: [(lx, ty), (rx, ty), (cx_, cy_), (lx, by), (rx, by)],
        6: [(lx, ty), (rx, ty), (lx, cy_), (rx, cy_), (lx, by), (rx, by)],
    }[n]
    r = min(w, h) * 0.11
    for px_, py_ in layout:
        c.ellipse((px_ - r, py_ - r, px_ + r, py_ + r), fill=pip)


def draw_badged_value(c: Ctx, xy, txt, h: float, style: dict, bg: str, fnt: str = None):
    """按分类给数字上色：fill = 字身色，outline = 描边色。

    fill 为 None 时用算子底色冒充“透明底”，只留一圈黑边（Limited AV）。
    fnt 留空时：两位数用窄体（横向占位 1.13×h），单数字用粗体。
    """
    if not txt:
        return
    fill = style.get("fill") or bg
    hollow = style.get("fill") is None
    txt = str(txt)
    if not fnt:
        fnt = "narrow_b" if len(txt) >= 2 else "black"
    draw_value_symmetric(c, xy, txt, fill, h,
                         halo_w=1.5 if hollow else 1.05, shadow=False, fnt=fnt)


def draw_soft_word(c: Ctx, xy, word: str, size: float, rgb, alpha: float,
                   max_w: float = None, max_h: float = None, fnt: str = "black"):
    """把文字画到独立图层再按 alpha 合成 —— 得到真正的半透明“底色字”。"""
    layer = Image.new("RGBA", c.img.size, (0, 0, 0, 0))
    lc = Ctx(layer, c.u, "#000000")
    lc.text(xy, word, size, rgb + (255,), fnt, "mm", max_w=max_w, max_h=max_h)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    c.img.alpha_composite(layer)
    c.d = ImageDraw.Draw(c.img, "RGBA")


def draw_support_plate(c: Ctx, ct: Counter, ink: str, value_ink: str):
    """支援单位：在装甲值/素质/射程/移动力那一片的底层铺 “Support” 大字。
    默认不画任何数值；support_values=True 时只把 av(左) 与 rng(中) 叠在字样上。"""
    word = (ct.support_label or "Support").strip()
    if word:
        dark_bg = luma(ct.bg) < 0.5
        rgb = (255, 255, 255) if dark_bg else (0, 0, 0)
        draw_soft_word(c, (L["CX"], 50.4), word, 14.0, rgb,
                       0.42 if dark_bg else 0.34, max_w=58.0, max_h=13.5)
    if not ct.support_values:
        return
    if ct.av:
        draw_value_symmetric(c, (L["CX"] - L["FLANK"], L["VAL_Y"]), ct.av, value_ink,
                             L["VAL_H"])
    if ct.rng or ct.rng2:
        draw_center_column(c, ct.copy(quality=""), value_ink)


def fit_id_size(c: Ctx, strings, size: float, max_len: float, max_h: float) -> float:
    """给左右两列求共同字号：任一串过长或字面过高就整体缩小，保证两侧字号一致。"""
    best = float(size)
    for _ in range(40):
        f = font("narrow_b", c.p(best))
        ok = True
        for t in strings:
            t = str(t or "")
            if not t:
                continue
            bb = c.d.textbbox((0, 0), t, font=f)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            if w > c.p(max_len) or h > c.p(max_h):   # 竖排：串长→纵向，字面→横向
                ok = False
                break
        if ok:
            return best
        best *= 0.94
        if best <= 4.5:
            break
    return best


def draw_ids(c: Ctx, ct: Counter, ink: str):
    """左侧 Lower Unit ID、右侧 Formation ID：同一字号、各自竖排、都居中于 ID_Y。"""
    if not (ct.unit_id or ct.formation_id):
        return
    shared = fit_id_size(c, [ct.unit_id, ct.formation_id], L["ID_SIZE"],
                         L["ID_MAXLEN"], L["ID_MAXH"])
    if ct.unit_id:
        c.text((L["ID_X"], L["ID_Y"]), ct.unit_id, shared, ink, "narrow_b", "mm",
               rotate=90)                             # 左列：自下而上
    if ct.formation_id:
        c.text((L["FORM_X"], L["FORM_Y"]), ct.formation_id, shared, ink, "narrow_b", "mm",
               rotate=-90)                            # 右列：自上而下


def draw_symbol_box(c: Ctx, ct: Counter, ink: str):
    x0, y0, x1, y1 = L["SYM_BOX"]
    fill = "#F2C81E" if ct.hard else "#FFFFFF"
    sym_ink = "#141414" if luma(fill) > 0.5 else ink
    # 底板浅色外框 → 深色粗框，和示例里的双层边框一致
    c.rect((x0 - 1.0, y0 - 1.0, x1 + 1.0, y1 + 1.0), fill=lighten(fill, 0.75),
           outline=mix(sym_ink, fill, 0.35), width=0.8)
    c.rect((x0, y0, x1, y1), fill=hx(fill), outline=sym_ink, width=2.2)
    if not ct.hard:                     # Not Hard：白框 + 内细线
        c.rect((x0 + 1.6, y0 + 1.6, x1 - 1.6, y1 - 1.6),
               outline=mix(sym_ink, fill, 0.55), width=0.7)
    if ct.symbol_mode == "letter":
        letters = (ct.symbol_letters or SYMBOL_LETTERS.get(ct.symbol, "")).upper()
        if letters:
            size = 11.6 if len(letters) <= 3 else (9.0 if len(letters) == 4 else 7.4)
            c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 0.4), letters, size, sym_ink,
                   "black", "mm", max_w=(x1 - x0) * 0.84, max_h=(y1 - y0) * 0.60)
    else:
        draw_symbol(c, ct.symbol, (x0 + 2.6, y0 + 2.4, x1 - 2.6, y1 - 2.4), sym_ink,
                    1.9, ct.symbol_text)
    if ct.breakthrough:
        c.poly([(x0 + 1.0, y0 + 1.0), (x0 + 6.4, y0 + 1.0), (x0 + 1.0, y0 + 6.4)],
               fill="#E8B60C", outline="#111111", width=0.8)


def draw_arrow(c: Ctx, x: float, ytop: float, ybot: float, ink: str, w: float = 5.4):
    """Unit Key 的突击箭头：白色实心粗箭头 + 深色描边，箭头占上部 45%。"""
    x0, x1 = x - w / 2, x + w / 2
    head = (ybot - ytop) * 0.34
    shaft = w * 0.26
    pts = [(x, ytop), (x1, ytop + head), (x + shaft, ytop + head),
           (x + shaft, ybot), (x - shaft, ybot), (x - shaft, ytop + head),
           (x0, ytop + head)]
    c.poly([(px + 0.45, py + 0.55) for px, py in pts], fill=(0, 0, 0, 110))
    c.poly(pts, fill="#FFFFFF", outline=ink, width=1.0)


def fit_value_size(c: Ctx, values, size: float, max_w: float, max_h: float) -> float:
    """给左右两枚数值求一个“共同字号”：任一枚超宽/超高就整体缩小，保证两侧字高一致。"""
    best = float(size)
    for _ in range(40):
        f = font("narrow_b", c.p(best))
        ok = True
        for v in values:
            v = str(v or "")
            if not v:
                continue
            bb = c.d.textbbox((0, 0), v, font=f)
            if (bb[2] - bb[0]) > c.p(max_w) or (bb[3] - bb[1]) > c.p(max_h):
                ok = False
                break
        if ok:
            return best
        best *= 0.94
        if best <= 5:
            break
    return best


def draw_value(c: Ctx, xy, s, size, color, max_w=None, shadow=True):
    """单个大数值（HQ/辎重等）：允许按 max_w 自适应。"""
    if not s:
        return
    x, y = xy
    halo = "#FFFFFF" if luma(color) < 0.62 else "#101010"
    if shadow:
        c.text((x + 0.8, y + 1.0), s, size, (0, 0, 0, 110), "black", "mm",
               max_w=max_w, max_h=size * 1.0)
    c.text((x, y), s, size, color, "narrow_b", "mm", max_w=max_w, max_h=size * 1.05,
           outline=halo, outline_w=1.35)


def _text_tight(c: Ctx, s: str, size_design: float, color, halo, halo_w: float, fnt: str = "narrow_b"):
    """Render a string into a bitmap cropped tight to its ink box (stroke included)."""
    size_px = max(6, int(round(size_design * c.u)))
    f = font(fnt, size_px)
    pad = max(6, int(size_px * 0.4))
    w = int(size_px * max(1.2, 0.62 * len(s))) + pad * 2
    h = int(size_px * 1.6) + pad * 2
    tmp = Image.new("RGBA", (max(w, 8), max(h, 8)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((pad, pad), s, font=f, fill=color,
           stroke_width=max(1, int(round(halo_w * c.u))), stroke_fill=halo)
    bb = tmp.getbbox()
    return tmp.crop(bb) if bb else tmp


def draw_value_symmetric(c: Ctx, xy, s, color,
                         target_h: float = 17.2, halo_w: float = 1.15, shadow=True,
                         aspect: float = None, fnt: str = "narrow_b"):
    """Left/right big numbers: ink height forced to target_h, ink centre at xy.

    Normalising by the ink box makes both sides share identical top/bottom edges
    and an identical centre line, and keeps the horizontal centre on the对称点.
    """
    if not s:
        return
    halo = "#FFFFFF" if luma(color) < 0.62 else "#101010"
    tight = _text_tight(c, str(s), target_h * 1.9, color, halo, halo_w, fnt)
    th = max(2, int(round(c.p(target_h))))
    th += th % 2                      # 强制偶数高度
    if aspect:                                   # 指定宽高比：用于把「10」这类两位数压成近正方形
        tw = max(2, int(round(th * aspect)))
    else:
        tw = max(2, int(round(tight.width * th / max(1, tight.height))))
    tw += tw % 2                      # 强制偶数宽度 → 墨迹中心必然落在整数像素上
    glyph = tight.resize((tw, th), Image.LANCZOS)
    cx = int(round(c.p(xy[0])))
    cy = int(round(c.p(xy[1])))
    px, py = cx - tw // 2, cy - th // 2
    if shadow:
        sil = Image.new("RGBA", glyph.size, (0, 0, 0, 0))
        sil.putalpha(glyph.getchannel("A").point(lambda a: int(a * 0.45)))
        c.img.alpha_composite(sil, (px + 1, py + 1))
    c.img.alpha_composite(glyph, (px, py))
    c.d = ImageDraw.Draw(c.img, "RGBA")


def draw_center_column(c: Ctx, ct: Counter, ink_value: str):
    """中轴列：素质值在上、射程在下，两者字号（墨迹高度）完全相同、都居中于中轴。

    两格总高 = 2*SM_H + SM_GAP ≈ 22.4，比左右大数值的 VAL_H=19.0 略高。
    """
    ink = "#1A1A1A" if luma(ct.bg) > 0.34 else "#FFFFFF"
    # 编制色带若压到「射程」那一格且颜色偏深 → 射程改白字（否则黑字糊在深色带上）
    bar_top = None
    if ct.bar_pos == "bottom" and ct.bar_thickness > 0:
        bar_top = DESIGN - 2.0 - max(0.0, min(ct.bar_thickness, DESIGN - 42.0))
    range_ink = ink
    if bar_top is not None and bar_top < L["R_Y"] + L["SM_H"] / 2 and luma(ct.bar_color) < 0.58:
        range_ink = "#FFFFFF"
    h = L["SM_H"]
    # 「不可补员 / 不可重建」标记：素质值底下垫一枚实心黄圈（取自 BBC-CS-1-B_78 实测：
    # 直径 ≈15 格、填充 #FFE400、深棕描边），数字改黑色以便在黄底上可读。
    if ct.no_rebuild and ct.quality:
        r = L["NR_R"]
        c.ellipse((L["CX"] - r, L["Q_Y"] - r, L["CX"] + r, L["Q_Y"] + r),
                  fill=L["NR_FILL"], outline=L["NR_RING"], width=1.8)
        ink = "#101010"
    if ct.range_style == "chip":
        draw_range_chip(c, ct, ink_value)
        if ct.quality:
            draw_value_symmetric(c, (L["CX"], L["Q_Y"]), ct.quality, ink, h,
                                 halo_w=0.72, shadow=False)
        return
    if ct.quality:
        draw_value_symmetric(c, (L["CX"], L["Q_Y"]), ct.quality, ink, h,
                             halo_w=0.72, shadow=False)
    if ct.rng or ct.rng2:
        if ct.rng2:      # 射程分两行：各自略缩，两行合计仍等于一格高
            sub = (h - 1.2) / 2
            draw_value_symmetric(c, (L["CX"], L["R_Y"] - sub / 2 - 0.6), ct.rng, range_ink, sub,
                                 halo_w=0.6, shadow=False)
            draw_value_symmetric(c, (L["CX"], L["R_Y"] + sub / 2 + 0.6), ct.rng2, range_ink, sub,
                                 halo_w=0.6, shadow=False)
        else:
            draw_value_symmetric(c, (L["CX"], L["R_Y"]), ct.rng, range_ink, h,
                                 halo_w=0.72, shadow=False)


def draw_range_chip(c: Ctx, ct: Counter, ink_value: str):
    """白底小牌样式：素质值在上、射程在下，整体仍居中于中轴。"""
    if not (ct.rng or ct.rng2):
        return
    x0, y0, x1, y1 = L["CHIP"]
    c.rrect((x0, y0, x1, y1), 1.0, fill="#FBFBF6", outline="#2A2A2A", width=0.9)
    sub = (L["SM_H"] - 1.6) / 2
    if ct.rng2:      # 射程两行（如 4 / 2）
        draw_value_symmetric(c, (L["CX"], L["R_Y"] - sub / 2 - 0.6), ct.rng,
                             "#141414", sub, halo_w=0.0, shadow=False)
        draw_value_symmetric(c, (L["CX"], L["R_Y"] + sub / 2 + 0.6), ct.rng2,
                             "#141414", sub, halo_w=0.0, shadow=False)
        c.line([(x0 + 1.6, L["R_Y"]), (x1 - 1.6, L["R_Y"])], "#B0B0B0", 0.5)
    else:
        draw_value_symmetric(c, (L["CX"], L["R_Y"]), ct.rng, "#141414",
                             L["SM_H"] * 0.86, halo_w=0.0, shadow=False)


def _hq_num(c: Ctx, xy, v, ink: str, h: float = None, force_black: bool = True, fnt: str = "black"):
    """HQ 上的数字：较宽字重（Arial Black）+ 白描边，按墨迹高度归一化。

    两位数按目标墨迹宽高比 ≈1.05 反推裁剪比 —— 「10」接近正方形；
    单数字保留字形原比例。默认强制黑色（force_black=False 时用主文字色）。
    """
    if not v:
        return
    txt = str(v).strip()
    hd = h or L["HQ_NUM_H"]
    halo = 0.55
    if len(txt) >= 2:
        asp = (1.05 * (hd - 2 * halo) + 2 * halo) / hd
    else:
        asp = None
    color = "#101010" if force_black else ink
    draw_value_symmetric(c, xy, v, color, hd, halo_w=halo, shadow=False,
                         aspect=asp, fnt=fnt)


def draw_fit_text(c: Ctx, xy, text: str, target_h: float, max_w: float, color,
                  halo: str, halo_w: float = 0.8, fnt: str = "black"):
    """把文字按“墨迹高度=target_h”绘制，超宽则横向压缩（保持高度不变）。"""
    if not text:
        return
    tight = _text_tight(c, str(text), target_h * 1.9, color, halo, halo_w, fnt)
    th = max(2, int(round(c.p(target_h))))
    th += th % 2
    tw = max(2, int(round(tight.width * th / max(1, tight.height))))
    tw += tw % 2
    limit = max(4, int(round(c.p(max_w))))
    if tw > limit:
        tw = limit - (limit % 2)
    glyph = tight.resize((tw, th), Image.LANCZOS)
    px_, py_ = int(round(c.p(xy[0]) - tw / 2)), int(round(c.p(xy[1]) - th / 2))
    c.img.alpha_composite(glyph, (px_, py_))
    c.d = ImageDraw.Draw(c.img, "RGBA")


def draw_hq(c: Ctx, ct: Counter, ink: str, value_ink: str):
    """HQ 双面版式：side=front 正常面，side=back 已激活面。"""
    if ct.command_radius:
        _hq_num(c, L["HQ_RADIUS"], ct.command_radius, ink, 14.6)

    if ct.side == "back":
        # 背面：白色水平色带（中线与番号对齐）→ 骰面 → 番号 → 炮击值 → 移动力
        band_h = L["HQ_BAND_H"]
        cy = L["HQ_NAME_B"][1]
        c.rect((1.6, cy - band_h / 2, DESIGN - 1.6, cy + band_h / 2),
               fill=hx(L["HQ_BAND_COLOR"]))
        c.line([(1.6, cy - band_h / 2), (DESIGN - 1.6, cy - band_h / 2)], "#C9C9BE", 0.8)
        c.line([(1.6, cy + band_h / 2), (DESIGN - 1.6, cy + band_h / 2)], "#C9C9BE", 0.8)

        draw_die(c, L["HQ_DIE"], ct.activation or ct.ar, "#141414", "#141414")
        name = ct.formation_id or ct.name
        # 空心样式：填充取白带底色、描边用黑 → 视觉上是“空心黑轮廓”
        draw_fit_text(c, L["HQ_NAME_B"], name, L["HQ_NAME_H"], L["HQ_NAME_MAXW"],
                      L["HQ_BAND_COLOR"], "#141414", 1.15, fnt="narrow_b")
        _hq_num(c, L["HQ_ARTY_B"], ct.arty, ink)
        draw_badged_value(c, L["HQ_MA_B"], ct.ma, L["HQ_NUM_H"] * L["HQ_MA_SCALE"],
                          MOVE_CLASS_STYLE.get(ct.move_class, MOVE_CLASS_STYLE["tac"]),
                          ct.bg, fnt="narrow_b")
        return

    # 正面：兵牌 + 规模标志 + 炮击点数 + 番号
    x0, y0, x1, y1 = L["HQ_BOX"]
    if ct.hq_box_tint and ct.bar_pos != "none" and ct.bar_thickness > 0:
        face = mix(ct.bar_color, ct.bg, 0.30)   # 跟随编制色带，略混底色以保可读
    else:
        face = mix(ct.bg, "#000000", 0.10)
    c.rect((x0, y0, x1, y1), fill=face, outline=ink, width=2.6)
    if ct.symbol_mode == "letter":
        letters = (ct.symbol_letters or SYMBOL_LETTERS.get(ct.symbol, "")).upper()
        if letters:
            c.text(((x0 + x1) / 2, (y0 + y1) / 2 + 0.3), letters, 12.0, ink, "black", "mm",
                   max_w=(x1 - x0) * 0.8, max_h=(y1 - y0) * 0.6)
    else:
        draw_symbol(c, ct.symbol or "none", (x0 + 2.8, y0 + 2.4, x1 - 2.8, y1 - 2.4),
                    ink, 2.2, ct.symbol_text)

    if ct.size_label:
        save = L["SIZE"]
        L["SIZE"] = L["HQ_SIZE"]
        try:
            draw_size(c, ct, ink)
        finally:
            L["SIZE"] = save

    _hq_num(c, L["HQ_ARTY_F"], ct.arty, ink)

    name = ct.formation_id or ct.name
    draw_fit_text(c, L["HQ_NAME_F"], name, L["HQ_NAME_H"], L["HQ_NAME_MAXW"], ink,
                  "#FFFFFF" if luma(ink) < 0.5 else "#101010", 0.6, fnt="narrow_b")


def draw_prohibit(c: Ctx, center, radius: float, color: str = "#C0392B"):
    """禁止标志：粗圆环 + 一道斜杠（左下 → 右上）。"""
    cx, cy = center
    r = radius
    c.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=4.6)
    k = r * 0.72
    c.line([(cx - k, cy + k), (cx + k, cy - k)], color, 4.6)


def draw_supply(c: Ctx, ct: Counter, ink: str):
    """补给车：正面 = 箭头 + 黑框番号 + 车体标志；背面 = 再叠一层禁止标志（在文字底下）。"""
    x0, y0, x1, y1 = L["SP_FRAME"]

    # 失常面：先在底层铺禁止标志（文字压在它上面）
    if ct.side == "back":
        draw_prohibit(c, L["SP_SIGN"][:2], L["SP_SIGN"][2])

    # 番号：支持 "\n" 手动两行；无换行则单行居中（黑框仅辅助定位，不绘制）
    text = (ct.formation_id or ct.name or "").strip()
    if text:
        lines = [ln for ln in text.split("\n") if ln.strip()] or [text]
        h = L["SP_TEXT_H"] if len(lines) > 1 else L["SP_TEXT_H"] * 1.6
        gap = h * 1.15
        cy = (y0 + y1) / 2 - (len(lines) - 1) * gap / 2
        for i, ln in enumerate(lines):
            draw_fit_text(c, ((x0 + x1) / 2, cy + i * gap), ln, h, (x1 - x0) - 3.0,
                          ink, ink, 0.0,
                          fnt="narrow_b")

    # 顶部行军箭头（纯白、细）
    ax0, ay0, ax1, ay1 = L["SP_ARROW"]
    c.line([(ax0, ay0), (ax1 - 4.2, ay1)], "#FFFFFF", 1.5)
    c.poly([(ax1, ay1), (ax1 - 6.2, ay1 - 2.8), (ax1 - 6.2, ay1 + 2.8)],
           fill="#FFFFFF")

    # 车体：横杆 + 两轮
    ty = L["SP_TRUCK_Y"]
    c.line([(13.6, ty), (61.6, ty)], "#FFFFFF", 3.2)
    for wx, wy in L["SP_WHEELS"]:
        r = L["SP_WHEEL_R"]
        c.ellipse((wx - r, wy - r, wx + r, wy + r), outline="#FFFFFF", width=3.0)


# ---------------------------------------------------------------- 主渲染
def render(ct: Counter, size: int = 75, ss: int = 4) -> Image.Image:
    px = int(round(size * ss))
    u = px / DESIGN
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    # —— 正/反面：布局一致，只换数值与 AR 画法（不再压暗纱）
    #    *_move 留空 = 沿用正面；填 "-" = 这一面不画该项；填值 = 覆盖
    if ct.side == "back":
        # 反面可以整枚换成另一种单位类型（如 M18 坦歼：正面装甲单位、反面支援单位）
        swapped = bool(ct.kind_move) and ct.kind_move != "-" and ct.kind_move != ct.kind
        ct = ct.copy(ar=side_value(ct.ar_move, ct.ar),
                     quality=side_value(ct.quality_move, ct.quality),
                     av=side_value(ct.av_move, ct.av),
                     rng=side_value(ct.rng_move, ct.rng),
                     rng2=side_value(ct.rng2_move, ct.rng2),
                     ma=side_value(ct.ma_move, ct.ma),
                     move_class=ct.move_class_move or ct.move_class,
                     kind=(ct.kind_move if swapped else ct.kind))
        # 换类型的反面是独立单位，AR 不做“虚化”（虚化只表示同一枚算子的另一面）
        if ct.back_ghost and ct.ar_style == "box" and not swapped:
            ct = ct.copy(ar_style="ghost")

    bg = ct.bg
    ink = ct.ink or readable_ink(bg)
    # 数值压在色带上，所以按“色带”的明度选红字/白字（与 Unit Key 一致）
    if ct.value_ink:
        value_ink = ct.value_ink
    elif ct.show_band and ct.band and ct.band != "none" and luma(ct.band) < 0.5:
        value_ink = "#FFFFFF"
    elif luma(bg) > 0.30:
        value_ink = "#A5121C"
    else:
        value_ink = "#FFFFFF"
    c = Ctx(img, u, ink)

    draw_plate(c, ct)

    # 机动色带
    if ct.show_band and ct.kind in ("av", "dual", "inf", "hq", "train"):
        draw_band(c, ct, L["BAND_TOP"], L["BAND_BOT"], ct.band)
    # 编制色带（战斗单位默认在底边，标记类不画）
    if ct.kind in ("hq", "supply"):
        # HQ 内容要居中，底边只留细色带
        draw_bar(c, ct.copy(bar_thickness=min(ct.bar_thickness, 4.4)), ct.bar_color)
    elif ct.kind != "marker":
        draw_bar(c, ct, ct.bar_color)

    CX, FLANK = L["CX"], L["FLANK"]

    if ct.kind == "support":
        draw_support_plate(c, ct, ink, value_ink)
        draw_ar(c, ct, value_ink)
        draw_size(c, ct, ink)
        draw_symbol_box(c, ct, ink)
        draw_ids(c, ct, ink)

    elif ct.kind in ("av", "dual", "inf"):
        has_av = bool(ct.av)
        # 左右大数值永远关于中轴对称，字号/字宽上限一致
        left_x, right_x = CX - FLANK, CX + FLANK
        arrow_x = (CX - FLANK - L["ARROW_AV_GAP"]) if has_av else (CX - FLANK)

        draw_center_column(c, ct, value_ink)
        draw_ar(c, ct, value_ink)
        draw_size(c, ct, ink)
        draw_symbol_box(c, ct, ink)
        draw_ids(c, ct, ink)
        if ct.steps:
            c.text((45.0, 12.2), ct.steps, 6.8, ink, "narrow_b", "mm", max_w=8.0)
        if ct.assault:
            draw_arrow(c, arrow_x, L["ARROW_TOP"], L["ARROW_BOT"], "#FFFFFF", L["ARROW_W"])
        # 两侧按墨迹高度归一化：高度/中心线严格一致，横向中心对称
        th = L["VAL_H"]
        if has_av:
            draw_badged_value(c, (left_x, L["VAL_Y"]), ct.av, th,
                              AV_CLASS_STYLE.get(ct.av_class, AV_CLASS_STYLE["red"]), bg)
        draw_badged_value(c, (right_x, L["VAL_Y"]), ct.ma, th,
                          MOVE_CLASS_STYLE.get(ct.move_class, MOVE_CLASS_STYLE["tac"]), bg)

    elif ct.kind == "hq":
        draw_hq(c, ct, ink, value_ink)

    elif ct.kind == "supply":
        draw_supply(c, ct, ink)

    elif ct.kind == "train":
        # 辎重：编制名 + KG + 底带内“卡车/挂车”轮组
        if ct.formation_id:
            c.text((DESIGN / 2, 15.8), ct.formation_id, 10.2, ink, "black", "mm", max_w=54)
        c.text((DESIGN / 2, 27.6), ct.name or "KG", 11.2, ink, "black", "mm", max_w=44,
               outline="#101010" if luma(ink) > 0.62 else None, outline_w=0.5)
        wy = L["BAND_TOP"] + 6.2
        c.line([(18.0, wy - 3.0), (57.0, wy - 3.0)], "#141414", 1.6)
        bw = 7.0
        for xx in (27.0, 48.0):
            c.ellipse((xx - bw / 2, wy - bw / 2, xx + bw / 2, wy + bw / 2), fill="#FFFFFF",
                      outline="#141414", width=1.4)
            c.ellipse((xx - bw / 5, wy - bw / 5, xx + bw / 5, wy + bw / 5), fill="#141414")
        if ct.ma:
            draw_value_symmetric(c, (L["CX"] - L["FLANK"], L["VAL_Y"] + 1.0), ct.ma, value_ink, L["VAL_H"])

    else:  # marker / 通用文字
        c.rrect((5.0, 6.0, DESIGN - 5.0, DESIGN - 6.0), 1.6,
                fill="#FDFDF8", outline="#141414", width=1.5)
        c.text((DESIGN / 2, DESIGN / 2 - 3.0), ct.name or "MARKER", 10.4, "#141414",
               "black", "mm", max_w=58, max_h=20)
        if ct.note:
            c.text((DESIGN / 2, DESIGN / 2 + 11.0), ct.note, 5.8, "#141414", "narrow_b", "mm",
                   max_w=56, max_h=14)

    draw_border(c, ink="#111111")
    return img.resize((size, size), Image.LANCZOS)


def render_pair(ct: Counter, size: int = 75, ss: int = 4) -> Image.Image:
    """战斗面 + 移动面并排（两面版式相同，数值/AR 画法按 side 自动切换）。"""
    a = render(ct.copy(side="front"), size, ss)
    b = render(ct.copy(side="back"), size, ss)
    gap = max(2, size // 20)
    out = Image.new("RGBA", (size * 2 + gap, size), (0, 0, 0, 0))
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (size + gap, 0))
    return out


def contact_sheet(specs, cols: int = 6, size: int = 75, pad: int = 8,
                  bg=(24, 24, 26, 255)) -> Image.Image:
    n = len(specs)
    rows = max(1, math.ceil(n / cols))
    W = cols * size + (cols + 1) * pad
    H = rows * size + (rows + 1) * pad
    sheet = Image.new("RGBA", (W, H), bg)
    for i, ct in enumerate(specs):
        r, cc = divmod(i, cols)
        sheet.alpha_composite(render(ct, size), (pad + cc * (size + pad), pad + r * (size + pad)))
    return sheet


# ---------------------------------------------------------------- 保存 / 读入
def save_specs(specs, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in specs], f, ensure_ascii=False, indent=2)


def load_specs(path):
    data = None
    for enc in ("utf-8-sig", "utf-8", "utf-16", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                data = json.load(f)
            break
        except (UnicodeError, ValueError):
            continue
    if data is None:
        raise ValueError("无法解析 JSON：" + str(path))
    if isinstance(data, dict):
        data = [data]
    return [Counter(**{k: v for k, v in d.items() if k in Counter.__dataclass_fields__})
            for d in data]
