# -*- coding: utf-8 -*-
"""生成一份“示例军队”：两个编制，每个编制 = HQ + 补给车 + 若干战斗单位。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_army as A  # noqa: E402
import bcs_render as R  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples", "army_demo.json")

army = A.empty_army()
army["meta"] = {"name": "示例军队 · 第 10 装甲师 + 90 步兵师", "game": "BCS"}

# ---- 编制 1：10 GD
A.add_formation(army, "10 GD", "#A3BA68", "#6E8B3D", "armor", hq_id="10 GD HQ")
rows = army["rows"]
rows[0].update(ar="10", size_label="XX", command_radius="10", arty="4", ma="8",
               activation="4", quality="4")
rows[1].update(unit_id="10 GD Sup")
rows[2].update(unit_id="I/33", size_label="II", ar="5", av="4", quality="4", symbol="armor",
               rng="2", ma="16", move_class="tac", av_class="red", hard=True)
army["rows"].append(A.new_row("av", "10 GD", unit_id="II/33", size_label="II", ar="5", symbol="tiger",
                              av="3", quality="3", rng="2", ma="12",
                              move_class="truck", av_class="standoff", hard=True))
army["rows"].append(A.new_row("inf", "10 GD", unit_id="I/505", size_label="II", ar="5", symbol="inf",
                              quality="3", rng="", ma="8", move_class="leg",
                              assault=True, no_rebuild=True, assault_move="-"))
army["rows"].append(A.new_row("support", "10 GD", unit_id="Spt 10 GD", size_label="II", symbol="inf",
                              ar="6", av="", quality="3", rng="", ma="8"))

# ---- 编制 2：90 Inf Div
A.add_formation(army, "90 Inf Div", "#E9D6B8", "#A63A6B", "inf", hq_id="90 ID HQ")
rows = army["rows"]
b = len(rows) - 3
rows[b].update(ar="10", size_label="XX", command_radius="8", arty="3", ma="8",
               activation="4", quality="3")
rows[b + 1].update(unit_id="90 ID Sup")
rows[b + 2].update(unit_id="1/90", size_label="III", ar="4", quality="2", symbol="inf",
                   rng="", ma="8", move_class="leg",
                   quality_move="1", ma_move="4")     # 移动面：素质 1、MA 4
army["rows"].append(A.new_row("inf", "90 Inf Div", unit_id="2/90", symbol="inf", size_label="III",
                              ar="4", quality="2", rng="", ma="8", move_class="leg"))
army["rows"].append(A.new_row("inf", "90 Inf Div", unit_id="3/90", symbol="inf", size_label="III",
                              ar="3", quality="2", rng="", ma="12",
                              move_class="truck", no_rebuild=True))
# M18 坦歼：正面是可独立作战的装甲单位，反面整枚变成支援单位
army["rows"].append(A.new_row("av", "90 Inf Div", unit_id="M18/90", size_label="II", ar="4",
                              symbol="td", av="3", quality="3", rng="3", ma="8",
                              move_class="tac", av_class="red",
                              kind_move="support", support_label="M18 TD"))

A.save_army(army, OUT)
print("ok", OUT, len(army["rows"]), "rows")

res = A.export_army(army, os.path.join(HERE, "out", "army"), size=75)
print("exported", res["count"], "counters /", len(res["files"]), "files")
