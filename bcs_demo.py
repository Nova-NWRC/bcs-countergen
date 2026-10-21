# -*- coding: utf-8 -*-
"""生成对比样张：覆盖各类型 + 各配色，用于校验版式。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bcs_render import Counter, contact_sheet, render, render_pair  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
os.makedirs(OUT, exist_ok=True)

specs = [
    # 装甲：德军
    Counter(kind="av", unit_id="I/33", formation_id="10 GD", size_label="II", ar="5",
            av="4", quality="4", rng="2", rng2="", ma="16", hard=True, symbol="armor",
            bg="#A3BA68", band="#C0392B", bar_color="#6E8B3D"),
    # 装甲：美军
    Counter(kind="av", unit_id="B/37", formation_id="4 AD", size_label="II", ar="6",
            av="3", av_class="standoff", quality="3", rng="", ma="16", move_class="tac", hard=True, symbol="tiger", no_rebuild=True,
            bg="#B7D5EC", band="#5B8FD6", bar_color="#2F5FA8"),
    # 步兵（徒步）
    Counter(kind="inf", unit_id="II/505", formation_id="10 GD", size_label="II", ar="5",
            quality="3", rng="", ma="8", move_class="leg", ma_move="12", move_class_move="truck", hard=False, symbol="inf",
            bg="#F2DCB0", band="#E8C10C", bar_color="#D97A20"),
    # 双能力
    Counter(kind="dual", unit_id="23", formation_id="Pape", size_label="I", ar="5",
            av="1", av_class="light", quality="5", rng="", ma="12", move_class="truck", hard=False, symbol="recon",
            bg="#BFC0B6", band="#8FA8C8", bar_color="#7A3E8F"),
    # HQ（正面=正常面）
    Counter(kind="hq", side="front", formation_id="30 Inf", command_radius="10",
            size_label="XX", arty="4", activation="4", ma="8", move_class="leg", symbol="inf",
            symbol_mode="glyph", bg="#7E9B3D", bar_color="#6E8B3D"),
    # 辎重
    Counter(kind="train", formation_id="Pape", name="KG", ma="12",
            bg="#BFC0B6", band="#5B8FD6", bar_color="#8C4A2F"),
    # 空降
    Counter(kind="inf", unit_id="G/504", formation_id="82 Abn", size_label="I", ar="5",
            quality="3", rng="", ma="8", move_class="leg", hard=False, symbol="abn", assault=True,
            bg="#C8DEEE", band="#5B8FD6", bar_color="#2A8C93"),
    # 山地
    Counter(kind="inf", unit_id="GebJg", formation_id="1 GJ", size_label="II", ar="4",
            quality="2", rng="", ma="8", move_class="leg", hard=True, symbol="mtn",
            bg="#9AA46C", band="#E8C10C", bar_color="#2E7D4F"),
    # 突击炮
    Counter(kind="av", unit_id="StuG", formation_id="3 GD", size_label="III", ar="4",
            av="4", av_class="red", quality="4", rng="", ma="8", move_class="leg", hard=True, symbol="stug", breakthrough=True,
            bg="#7E9B4B", band="#7A6A55", bar_color="#A63A6B"),
    # 工兵
    Counter(kind="inf", unit_id="Pio", formation_id="10 GD", size_label="I", ar="3",
            quality="2", rng="", ma="8", move_class="leg", hard=False, symbol="eng",
            bg="#D6BAAC", band="#E8C10C", bar_color="#7A5230"),
    # 以军装甲
    Counter(kind="av", unit_id="7/6", formation_id="7 ArBde", size_label="X", ar="5",
            av="5", av_class="limited", quality="5", rng="", ma="16", move_class="tac", hard=True, symbol="js",
            bg="#C3D8EE", band="#C0392B", bar_color="#3B3F8F"),
    # 标记
    Counter(kind="marker", name="Blown Bridge", note="Bridge tried and did not blow",
            bg="#FFFFFF"),
    # 补给车（正面=正常面 / 背面=失常面，禁止标志在文字底层）
    Counter(kind="supply", side="front", formation_id="90 Inf\nDiv", bg="#7E9B3D",
            bar_pos="none"),
    Counter(kind="supply", side="back", formation_id="90 Inf\nDiv", bg="#7E9B3D",
            bar_pos="none"),
    # 支援单位（版式与战斗单位相同，只在底部色带印 Support）
    Counter(kind="support", unit_id="Spt", formation_id="10 GD", size_label="II", ar="6",
            quality="3", ma="8", symbol="oval", symbol_mode="glyph",
            bg="#A3BA68", bar_color="#6E8B3D"),
    Counter(kind="support", unit_id="Arty", formation_id="82 Abn", size_label="X", ar="5",
            symbol="text", symbol_letters="ARTY", av="2", quality="3", rng="3", ma="6",
            bg="#C8DEEE", bar_color="#2A8C93"),
    # 图形符号 + 机动色带（DF / 老作风格）
    Counter(kind="av", unit_id="B/37", formation_id="4 AD", size_label="II", ar="6",
            av="3", av_class="standoff", quality="3", rng="", ma="16", move_class="tac", hard=True, symbol="tiger", no_rebuild=True, symbol_mode="glyph",
            bg="#B7D5EC", band="#5B8FD6", show_band=True, bar_color="#2F5FA8"),
    # 字母代号 + 机动色带
    Counter(kind="inf", unit_id="Pio", formation_id="10 GD", size_label="I", ar="3",
            quality="2", rng="", ma="4", symbol="eng", bg="#A3BA68", band="#E8C10C",
            show_band=True, bar_color="#5E7A33"),
    # 与 Example 同款（CS-3：无底带、深红数值）
    Counter(kind="inf", unit_id="2", formation_id="110/28", size_label="II", ar="6",
            quality="4", rng="", ma="4", symbol="inf", symbol_mode="glyph", bg="#7E9B3D",
            bar_pos="none"),
]

sheet = contact_sheet(specs, cols=6, size=150, pad=10)
sheet.save(os.path.join(OUT, "demo_sheet_150.png"))

sheet75 = contact_sheet(specs, cols=6, size=75, pad=6)
sheet75.save(os.path.join(OUT, "demo_sheet_75.png"))

big = contact_sheet(specs[:6], cols=3, size=300, pad=12)
big.save(os.path.join(OUT, "demo_sheet_300.png"))

render_pair(specs[0], 150).save(os.path.join(OUT, "pair_av_150.png"))

# 编制卡样张：两个编制并排（250×356 与官方卡同尺寸）
import bcs_chart as _C
_chart_army = {"meta": {}, "formations": {
    "10 GD": {"bg": "#A3BA68", "band": "#E8C10C", "bar_color": "#6E8B3D", "symbol": "armor"},
    "90 Inf Div": {"bg": "#E9D6B8", "band": "#E8C10C", "bar_color": "#A63A6B", "symbol": "inf"},
}, "rows": []}
_charts = [_C.chart_from_formation(_chart_army, n, size=250)
           for n in ("10 GD", "90 Inf Div")]
from PIL import Image as _Im  # noqa: E402
_pad, _bg = 14, (34, 33, 31)
_sheet = _Im.new("RGB", (250 * 2 + _pad * 3, 356 + _pad * 2), _bg)
for _i, _im in enumerate(_charts):
    _sheet.paste(_im, (_pad + _i * (250 + _pad), _pad), _im)
_sheet.save(os.path.join(OUT, "formation_chart.png"))

# 同时导出可直接编辑的算子库 JSON（GUI/CLI 都能载入）
import bcs_render as _R
_R.save_specs(specs, os.path.join(OUT, "units.json"))
print("ok:", os.path.join(OUT, "demo_sheet_150.png"))
