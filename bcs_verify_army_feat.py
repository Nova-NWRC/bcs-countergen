# -*- coding: utf-8 -*-
"""军队编辑器新增两功能的回归：整编制复制 + CSV 往返。"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_army as A  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "out", "_army_feat")
os.makedirs(TMP, exist_ok=True)

root = tk.Tk()
root.withdraw()
app = A.ArmyApp(root)

n0 = len(app.army["rows"])
f0 = len(app.army["formations"])
print(f"起始：{n0} 行 / {f0} 编制 {sorted(app.army['formations'])}")

# ---- 1) 整编制复制
added = A.duplicate_formation(app.army, "10 GD", "11 GD", hq_id="11 GD HQ", suffix="/11")
print(f"复制编制：新增 {added} 行 → 共 {len(app.army['rows'])} 行 / "
      f"{len(app.army['formations'])} 编制 {sorted(app.army['formations'])}")
c11 = [r for r in app.army["rows"] if r["formation_id"] == "11 GD"]
print("  新编制行:", [(r["kind"], r["unit_id"]) for r in c11])
print("  配色沿用:", app.army["formations"]["11 GD"])

# 同名复制应被拒绝
print("  自复制返回:", A.duplicate_formation(app.army, "10 GD", "10 GD"))

# ---- 2) CSV 往返
csv_path = os.path.join(TMP, "army.csv")
n = A.export_csv(app.army, csv_path)
print(f"导出 CSV：{n} 行 → {csv_path}")

back = A.import_csv(csv_path)
print(f"读回 CSV：{len(back['rows'])} 行 / {len(back['formations'])} 编制")

# 逐字段比对
keys = ("kind", "unit_id", "formation_id", "size_label", "ar", "av", "quality",
        "rng", "ma", "move_class", "av_class", "hard", "assault", "no_rebuild",
        "breakthrough", "command_radius", "arty", "activation")
diff = 0
for a, b in zip(app.army["rows"], back["rows"]):
    for k in keys:
        va = a.get(k, "")
        vb = b.get(k, "")
        if isinstance(va, bool) or isinstance(vb, bool):
            if bool(va) != bool(vb):
                diff += 1
                print("  差异", k, va, vb)
        elif str(va) != str(vb):
            diff += 1
            print("  差异", k, repr(va), repr(vb))
print("字段差异数:", diff)
print("配色回读:", back["formations"].get("11 GD"))

# ---- 3) 复制后的军队能正常出图
res = A.export_army(back, os.path.join(TMP, "png"), size=75)
print(f"读回后出图：{res['count']} 枚 / {len(res['files'])} 文件")

root.destroy()
print("OK")
