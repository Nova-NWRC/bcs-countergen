# -*- coding: utf-8 -*-
"""军队编辑器无界面自检：建模 → 编辑 → 预览 → 导出。"""
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
root = tk.Tk()
root.withdraw()
app = A.ArmyApp(root)

print("行数:", len(app.army["rows"]), " 编制:", sorted(app.army["formations"]))
print("表格行:", len(app.tree.get_children()))

# 选中第 3 行（战斗单位），改 AV 与移动力类型
app.tree.selection_set("2")
app.load_row()
print("选中行:", app.army["rows"][2]["unit_id"], app.army["rows"][2]["av"])
app.v["av"].set("2")
app.push("av")
app.v["move_class"].set("leg")
app.push("move_class")
print("改后:", app.army["rows"][2]["av"], app.army["rows"][2]["move_class"])

# 勾选不可重建
app.b["no_rebuild"].set(True)
app.push_flag("no_rebuild")
print("不可重建:", app.army["rows"][2]["no_rebuild"])

# 预览
app.redraw_preview()
print("预览图:", app._img.width() if app._img else None, "x",
      app._img.height() if app._img else None)

# 新增 / 复制 / 删除 / 移动
n0 = len(app.army["rows"])
app.add_row("av")
app.copy_row()
app.move_row(-1)
app.del_row()
print("增删后行数:", len(app.army["rows"]), "(起始", n0, ")")

# 导出到临时目录
out = os.path.join(HERE, "out", "_army_check")
res = A.export_army(app.army, out, size=75)
print("导出:", res["count"], "枚 /", len(res["files"]), "文件")
print("含清单:", any(f.endswith("_army.json") for f in res["files"]))

root.destroy()
print("OK")
