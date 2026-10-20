# -*- coding: utf-8 -*-
"""校验军队编辑器的“移动面/高级”字段真的落到了渲染上。

覆盖四件事：
1. *_move 只改反面，正面必须逐字节不变；
2. 反面的覆盖/留空/- 三态与 render.side_value 的约定一致；
3. 旧版 army_demo.json（没有新键）加载后仍能渲染出正确默认值；
4. CSV 往返不丢新字段。
"""
import hashlib
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
FORM = {"bg": "#A3BA68", "bar_color": "#6E8B3D", "band": "#E8C10C", "symbol": "inf"}
ok_all = True


def check(name: str, got, want, tol: float = 0.0):
    global ok_all
    good = (got == want) if tol == 0 else abs(got - want) <= tol
    if not good:
        ok_all = False
    print(f"{'一致' if good else '不一致'}  {name}: {got}  (期望 {want})")
    return good


def make(**kw):
    row = A.new_row("inf", "10 GD", unit_id="I/33", size_label="II", ar="4", av="2",
                    quality="3", rng="2", ma="4", symbol="inf")
    row.update(kw)
    return A.counter_from(row, FORM)


def sig(ct, side: str, size: int = 150) -> str:
    return hashlib.sha256(R.render(ct.copy(side=side), size, ss=2).tobytes()).hexdigest()[:16]


print("=== 1. 正面不受 *_move 影响 ===")
plain = make()
side = make(quality_move="1", av_move="-", ma_move="8", move_class_move="leg")
check("正面指纹", sig(side, "front"), sig(plain, "front"))
check("反面指纹已变", sig(side, "back") != sig(plain, "back"), True)

print("\n=== 2. 三态约定 ===")
# 留空 = 沿用正面：反面与“正面值直接当反面值”一致
check("留空沿用正面", sig(make(), "back"), sig(make(ar_move="4", quality_move="3",
                                              av_move="2", rng_move="2", ma_move="4"), "back"))
# "-" = 这一面不画：与把该值清空等价
check("av_move='-' 等价于无 AV", sig(make(av="", av_move="") , "back"),
      sig(make(av_move="-"), "back"))
check("rng_move='-' 等价于无射程", sig(make(rng="", rng_move=""), "back"),
      sig(make(rng_move="-"), "back"))
# 覆盖 = 用新值
check("ma_move 覆盖生效", sig(make(ma_move="9"), "back") != sig(make(), "back"), True)
check("quality_move 覆盖生效", sig(make(quality_move="1"), "back") != sig(make(), "back"), True)
# move_class_move 换 move_class → 反面字号/颜色变
check("move_class_move 生效", sig(make(move_class="leg", move_class_move="truck"), "back")
      != sig(make(move_class="leg"), "back"), True)
# back_ghost 关掉后反面 AR 不再虚化
ghost_off = make()
ghost_off = A.counter_from(dict(A.new_row("inf", "10 GD", unit_id="I/33", ar="4", av="2",
                                          quality="3", ma="4", symbol="inf",
                                          back_ghost=False)), FORM)
check("back_ghost=False 与默认不同", sig(ghost_off, "back") != sig(make(), "back"), True)

print("\n=== 3. 高级字段 ===")
ct = make(rng2="2", name="Gren", steps="2", ar_style="disc", range_style="chip",
          ink="#101010", value_ink="#A5121C", bar_pos="top", bar_thickness="10",
          support_label="Sup", support_values=True, gloss=False, show_band=True,
          band="#3A6EA5", note="n1", symbol_text="AB", symbol_mode="letter")
check("rng2", ct.rng2, "2")
check("name", ct.name, "Gren")
check("steps", ct.steps, "2")
check("ar_style", ct.ar_style, "disc")
check("range_style", ct.range_style, "chip")
check("bar_pos", ct.bar_pos, "top")
check("bar_thickness", ct.bar_thickness, 10.0, 1e-9)
check("gloss", ct.gloss, False)
check("show_band", ct.show_band, True)
check("band", ct.band, "#3A6EA5")
check("support_values", ct.support_values, True)
check("note", ct.note, "n1")
check("symbol_text", ct.symbol_text, "AB")

print("\n=== 4. 旧 JSON（缺新键）落默认值 ===")
old_row = {"kind": "inf", "unit_id": "X/1", "formation_id": "10 GD", "ar": "4",
           "quality": "3", "ma": "4"}
old = A.counter_from(old_row, FORM)
check("move_class 缺省", old.move_class, "tac")
check("av_class 缺省", old.av_class, "red")
check("ar_style 缺省", old.ar_style, "box")
check("range_style 缺省", old.range_style, "plain")
check("bar_pos 缺省", old.bar_pos, "bottom")
check("gloss 缺省", old.gloss, True)
check("back_ghost 缺省", old.back_ghost, True)
check("旧行可渲染", R.render(old, 75, ss=2).size, (75, 75))

print("\n=== 5. CSV 往返 ===")
army = A.empty_army()
A.add_formation(army, "10 GD", "#A3BA68", "#6E8B3D", "armor", hq_id="10 GD HQ")
row = A.new_row("inf", "10 GD", unit_id="I/33", ar="4", av="2", quality="3", ma="4")
row.update(quality_move="1", av_move="-", ma_move="8", move_class_move="leg",
           rng2="2", name="Gren", steps="2", ar_style="disc", gloss=False,
           show_band=True, band="#3A6EA5", note="n1")
army["rows"].append(row)
csv_path = os.path.join(HERE, "out", "_side_check.csv")
A.export_csv(army, csv_path)
back = A.import_csv(csv_path)
got = [r for r in back["rows"] if r.get("unit_id") == "I/33"][0]
for k in ("quality_move", "av_move", "ma_move", "move_class_move", "rng2", "name",
          "steps", "ar_style", "band", "note"):
    check(f"CSV {k}", str(got.get(k, "")), str(row.get(k, "")))
check("CSV gloss", str(got.get("gloss")), "False")
check("CSV show_band", str(got.get("show_band")), "True")

print("\n=== 6. 图形界面接线 ===")
try:
    import tkinter as tk
    import bcs_army as AB

    root = tk.Tk()
    root.withdraw()
    app = AB.ArmyApp(root)
    app.army = back
    app._refresh_tree(keep=1)
    app.load_row()
    app.v["ma_move"].set("6")
    app.push("ma_move")
    check("GUI 写回 ma_move", str(app.cur().get("ma_move")), "6")
    check("GUI 移动面列", AB.side_note(app.cur()) != "", True)
    app.redraw_preview()
    check("GUI 预览有内容", len(app.canvas.find_all()) > 0, True)
    root.destroy()
except Exception as exc:                                  # pragma: no cover
    ok_all = False
    print("不一致  GUI 接线:", exc)

print("\n=== 7. 与单枚编辑器对齐的剩余控件 ===")
check("每行符号覆盖生效", sig(make(), "front") != sig(make(symbol="armor"), "front"), True)
check("符号留空沿用编制", make(symbol="").symbol, "inf")
_army = A.empty_army()
A.add_formation(_army, "10 GD", "#A3BA68", "#6E8B3D", "armor", hq_id="10 GD HQ")
_army["rows"].append(A.new_row("inf", "10 GD", unit_id="I/33"))
try:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    app = A.ArmyApp(root)
    app.army = _army
    _idx = next(i for i, r in enumerate(_army["rows"]) if r.get("unit_id") == "I/33")
    app._refresh_tree(keep=_idx)
    app.load_row()
    app.apply_row_preset("bg", "苏军")
    check("底色预设写回 bg", app.cur().get("bg"), R.BG_PRESETS["苏军"][0])
    check("底色预设写回 band", app.cur().get("band"), R.BG_PRESETS["苏军"][1])
    check("底色预设同时开色带", bool(app.cur().get("show_band")), True)
    app.apply_row_preset("band", "TRUCK 卡车(12)")
    check("机动等级预设写回 band", app.cur().get("band"), R.MOVE_CLASS["TRUCK 卡车(12)"])
    app.apply_row_preset("band", "无")
    check("机动等级-无 关色带", bool(app.cur().get("show_band")), False)
    app.v["name"].set("临时")
    app.push("name")
    app.reset_row()
    check("重置本行清掉大字名", app.cur().get("name"), "")
    check("重置本行保留类型", app.cur().get("kind"), "inf")
    check("重置本行保留编制", app.cur().get("formation_id"), "10 GD")
    root.destroy()
except Exception as exc:                                  # pragma: no cover
    ok_all = False
    print("不一致  预设/重置:", exc)

for p in (csv_path,):
    try:
        os.remove(p)
    except OSError:
        pass

print("\n" + ("OK" if ok_all else "存在不一致"))
sys.exit(0 if ok_all else 1)
