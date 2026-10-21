# -*- coding: utf-8 -*-
"""军队编辑器（Army Editor）：表格批量编辑 + 一键出整套算子。

一行一枚算子，按「编制」分组：同一个编制（formation_id）共用一个番号、一套底色与编制色带；
新建编制会自动带上一枚 HQ 与一枚补给车（BCS 里每个编制通常就是 HQ + 补给车 + 若干战斗单位）。

命令行（无界面批量出图）：
    python bcs_army.py --spec samples\\army_demo.json --out out\\army
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402
from PIL import Image, ImageTk  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)
RES = getattr(sys, "_MEIPASS", HERE)                    # 打包后随 exe 解包的数据目录
BASE = os.path.dirname(sys.executable) if FROZEN else HERE
OUTDIR = os.path.join(BASE, "out", "army")
SPEC = os.path.join(RES, "samples", "army_demo.json")    # 示例编制：跟着 exe 的数据走

TEXT_COLS = ("unit_id", "formation_id", "size_label", "ar", "av", "quality", "rng", "rng2",
             "ma")
COLUMNS = [
    ("kind", "类型", 82),
    ("unit_id", "番号", 84),
    ("formation_id", "编制", 76),
    ("size_label", "规模", 54),
    ("ar", "AR", 38),
    ("av", "AV", 38),
    ("quality", "素质", 42),
    ("rng", "射程", 42),
    ("rng2", "射程2", 44),
    ("ma", "MA", 40),
    ("move_class", "移动力", 58),
    ("av_class", "装甲类", 62),
    ("side", "移动面", 96),
    ("flags", "标记", 74),
]

# 行里能存的全部字段：与 render.Counter 一一对应，缺省值与 Counter 保持一致
ROW_TEXT_KEYS = ("kind", "unit_id", "formation_id", "size_label", "ar", "av",
                 "quality", "rng", "rng2", "ma", "move_class", "av_class",
                 "command_radius", "arty", "activation", "steps", "name",
                 "symbol_text", "symbol_letters", "symbol_mode",
                 "band", "bar_pos", "bar_thickness", "ink", "value_ink",
                 "support_label", "ar_style", "range_style", "note",
                 # 移动面覆盖：留空 = 沿用正面，"-" = 这一面不画该项
                 "kind_move", "ar_move", "quality_move", "av_move", "rng_move",
                 "rng2_move", "ma_move", "move_class_move",
                 # 布尔量的面级三态：留空 = 沿用，"-" = 不画，其余 = 画
                 "assault_move", "hard_move", "breakthrough_move")
ROW_BOOL_KEYS = ("hard", "assault", "no_rebuild", "breakthrough", "gloss",
                 "hq_box_tint", "show_band", "back_ghost")
ROW_BOOL_ON = {"gloss", "hq_box_tint", "back_ghost"}   # Counter 里默认 True 的几项
# 单行可以覆盖的「编制级」属性：留空 = 用编制的值
ROW_EXTRA_KEYS = ("symbol",)

SIDE_FIELDS = ("kind_move", "ar_move", "quality_move", "av_move", "rng_move",
               "rng2_move", "ma_move", "move_class_move",
               "assault_move", "hard_move", "breakthrough_move")
SIDE_SHORT = {"kind_move": "型→", "ar_move": "AR", "quality_move": "质",
              "av_move": "AV", "rng_move": "射", "rng2_move": "射2",
              "ma_move": "MA", "move_class_move": "移",
              "assault_move": "突", "hard_move": "硬", "breakthrough_move": "破"}
# 留空时落成 Counter 的合法默认值，否则渲染会走到不该走的分支
_TEXT_FALLBACK = {"move_class": "tac", "av_class": "red", "ar_style": "box",
                  "range_style": "plain", "bar_pos": "bottom"}

KIND_SYMBOL = {"av": "armor", "dual": "armor", "inf": "inf", "hq": "inf",
               "supply": "inf", "support": "inf", "train": "train", "marker": "none"}


def slug(text: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "-", str(text or "").strip())
    return s.strip("-") or "counter"


def flags_of(row: dict) -> str:
    out = []
    if row.get("hard"):
        out.append("H")
    if row.get("assault"):
        out.append("A")
    if row.get("no_rebuild"):
        out.append("N")
    if row.get("breakthrough"):
        out.append("B")
    return " ".join(out)


def new_row(kind: str, formation_id: str, **kw) -> dict:
    row = dict(kind=kind, unit_id="", formation_id=formation_id, size_label="II", symbol="",
               ar="5", av="", quality="3", rng="", rng2="", ma="8",
               move_class="tac", av_class="red",
               hard=False, assault=False, no_rebuild=False, breakthrough=False,
               command_radius="", arty="", activation="", steps="", name="",
               symbol_text="", symbol_letters="", symbol_mode="",
               band="", bar_pos="", bar_thickness="",
               ink="", value_ink="", gloss=True, hq_box_tint=True, show_band=False,
               support_label="",
               ar_style="", range_style="", note="",
               ar_move="", quality_move="", av_move="", rng_move="", rng2_move="",
               ma_move="", move_class_move="", back_ghost=True,
               kind_move="", assault_move="", hard_move="", breakthrough_move="")
    row.update(kw)
    return row


def _text(row: dict, key: str, default: str = "") -> str:
    v = row.get(key, None)
    return default if v is None else str(v)


def _num(row: dict, key: str, default: float) -> float:
    try:
        return float(str(row.get(key, "") or "").strip())
    except Exception:
        return default


def _flag(row: dict, key: str, default: bool = False) -> bool:
    v = row.get(key, None)
    return default if v is None else bool(v)


def side_note(row: dict) -> str:
    """「移动面」列摘要：只列真正被覆盖的项。"""
    out = []
    for k in SIDE_FIELDS:
        v = _text(row, k).strip()
        if v:
            out.append(f"{SIDE_SHORT[k]}{'无' if v == '-' else v}")
    if not _flag(row, "back_ghost", True):
        out.append("AR实")
    return " ".join(out)


def counter_from(row: dict, form: dict) -> R.Counter:
    """把表格行 + 编制设置落成一枚 Counter（正反面差异交给 render 处理）。"""
    kind = row.get("kind", "inf")
    sym = (_text(row, "symbol").strip() or form.get("symbol")
           or KIND_SYMBOL.get(kind, "inf"))
    kw = {k: _text(row, k) for k in ROW_TEXT_KEYS}
    for k, v in _TEXT_FALLBACK.items():
        if not kw[k]:
            kw[k] = v
    for k in ROW_BOOL_KEYS:
        kw[k] = _flag(row, k, k in ROW_BOOL_ON)
    kw["symbol"] = sym
    kw["symbol_mode"] = kw["symbol_mode"] or ("glyph" if kind == "hq" else "letter")
    kw["bg"] = form.get("bg", "#A3BA68")
    kw["band"] = kw["band"] or form.get("band", "#E8C10C")
    kw["bar_color"] = form.get("bar_color", "#6E8B3D")
    kw["bar_thickness"] = _num(row, "bar_thickness", 15.0)
    kw["support_label"] = kw["support_label"] or "Support"
    ct = R.Counter(**kw)
    if kind == "supply" and not _text(row, "bar_pos"):
        ct = ct.copy(bar_pos="none")
    return ct


# --------------------------------------------------------------------- 数据
def empty_army() -> dict:
    return {"meta": {"name": "新军队", "game": "BCS"},
            "formations": {}, "rows": []}


def load_army(path: str) -> dict:
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        with open(path, encoding="gbk") as f:
            data = json.load(f)
    data.setdefault("formations", {})
    data.setdefault("rows", [])
    data.setdefault("meta", {})
    return data


def save_army(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def formation_of(army: dict, fid: str) -> dict:
    fs = army["formations"]
    if fid not in fs:
        fs[fid] = {"bg": "#A3BA68", "bar_color": "#6E8B3D", "symbol": "inf",
                   "band": "#E8C10C"}
    return fs[fid]


def add_formation(army: dict, fid: str, bg: str, bar: str, symbol: str,
                  hq_id: str = "", supply_id: str = "") -> None:
    """新建一个编制：HQ + 补给车 + 一枚空白战斗单位。"""
    formation_of(army, fid).update(bg=bg, bar_color=bar, symbol=symbol)
    army["rows"].append(new_row("hq", fid, unit_id=hq_id or fid,
                                size_label="XX", ar="10", av="", quality="",
                                rng="", ma="8", command_radius="10",
                                arty="4", activation="4"))
    army["rows"].append(new_row("supply", fid, unit_id=supply_id or (fid + " Sup"),
                                size_label="", ar="", av="", quality="", rng="", ma=""))
    army["rows"].append(new_row("inf", fid, unit_id="", symbol=None))



CSV_BOOL = ["hard", "assault", "no_rebuild", "breakthrough", "gloss", "hq_box_tint",
            "show_band", "back_ghost"]
CSV_TEXT = [k for k in ROW_TEXT_KEYS if k not in CSV_BOOL] + ["symbol"]
CSV_FIELDS = CSV_TEXT + CSV_BOOL + ["bg", "bar_color"]
CSV_TRUE = {"1", "true", "yes", "y", "是", "√", "on"}


def duplicate_formation(army: dict, src: str, dst: str, hq_id: str = "",
                        copy_colors: bool = True, suffix: str = "") -> int:
    """整编制复制：把 src 的所有行原样复制到 dst（含 HQ / 补给车 / 战斗单位）。

    - 行的 formation_id 换成 dst；HQ 的番号可指定，未指定则沿用原来的
    - suffix 非空时，追加到每个番号后面（例如把 "I/33" 变成 "I/33/11"）
    - 新行紧跟在源编制的最后一行之后，方便连着看
    """
    if not src or not dst or src == dst:
        return 0
    form = formation_of(army, src)
    new_form = formation_of(army, dst)
    if copy_colors:
        for k in ("bg", "band", "bar_color", "symbol"):
            if k in form:
                new_form[k] = form[k]

    idxs = [i for i, r in enumerate(army["rows"])
            if str(r.get("formation_id", "") or "") == src]
    if not idxs:
        return 0

    clones = []
    for i in idxs:
        row = dict(army["rows"][i])
        row["formation_id"] = dst
        if suffix:
            row["unit_id"] = (str(row.get("unit_id", "") or "") + suffix).strip()
        if row.get("kind") == "hq" and hq_id:
            row["unit_id"] = hq_id
        clones.append(row)

    at = max(idxs) + 1
    army["rows"][at:at] = clones
    return len(clones)


def export_csv(army: dict, path: str) -> int:
    """把军队导出成 CSV（utf-8-sig，Excel 直接双击不乱码）。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in army["rows"]:
            fid = str(row.get("formation_id", "") or "")
            form = formation_of(army, fid) if fid else {}
            out = {}
            for k in CSV_FIELDS:
                if k in CSV_BOOL:
                    out[k] = 1 if _flag(row, k, k in ROW_BOOL_ON) else 0
                elif k == "symbol":
                    out[k] = (row.get("symbol") or "").strip() or form.get("symbol", "")
                elif k in ("bg", "bar_color"):
                    out[k] = form.get(k, "")
                else:
                    out[k] = row.get(k, "")
            w.writerow(out)
    return len(army["rows"])


def import_csv(path: str) -> dict:
    """从 CSV 读回军队；同一编制的底色/色带/符号取该编制第一行里出现的值。"""
    army = empty_army()
    army["meta"]["name"] = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        have = set(reader.fieldnames or [])
        for rec in reader:
            kind = (rec.get("kind") or "inf").strip() or "inf"
            fid = (rec.get("formation_id") or "").strip()
            row = new_row(kind, fid)
            for k in CSV_TEXT:
                if k in have:                    # 表里有这一列 → 原样采用（空值也照抄）
                    row[k] = (rec.get(k) or "").strip()
            for k in CSV_BOOL:
                if k in have:                    # 列不存在时保留 new_row 的缺省值
                    row[k] = str(rec.get(k, "")).strip().lower() in CSV_TRUE
            army["rows"].append(row)
            if fid:
                form = formation_of(army, fid)
                fresh = not any(str(r.get("formation_id", "")) == fid
                                for r in army["rows"][:-1])
                if fresh:
                    for k in ("bg", "bar_color", "symbol"):
                        v = (rec.get(k) or "").strip()
                        if v:
                            form[k] = v
    return army

# --------------------------------------------------------------------- 导出
def export_army(army: dict, outdir: str, size: int = 75, pair: bool = True,
                sheet: bool = True, charts: bool = False) -> dict:
    os.makedirs(outdir, exist_ok=True)
    made, specs = [], []
    for row in army["rows"]:
        fid = str(row.get("formation_id", "") or "").strip()
        if not fid or not row.get("kind"):
            continue
        form = formation_of(army, fid)
        ct = counter_from(row, form)
        name = f"{slug(fid)}__{slug(row.get('unit_id') or row['kind'])}"
        if pair:
            for suffix, side in (("_F", "front"), ("_B", "back")):
                p = os.path.join(outdir, name + suffix + ".png")
                R.render(ct.copy(side=side), size).save(p)
                made.append(p)
        else:
            p = os.path.join(outdir, name + ".png")
            R.render(ct, size).save(p)
            made.append(p)
        specs.append(ct)
    if sheet and specs:
        R.contact_sheet(specs, cols=6, size=size).save(
            os.path.join(outdir, "_army_sheet.png"))
        made.append(os.path.join(outdir, "_army_sheet.png"))
    spec_path = os.path.join(outdir, "_army.json")
    save_army(army, spec_path)
    made.append(spec_path)
    if charts:
        import bcs_chart
        res = bcs_chart.export_charts(army, outdir)
        made.extend(res["files"])
    return {"files": made, "count": len(specs)}


# --------------------------------------------------------------------- 界面
class ArmyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("BCS 军队编辑器 · 表格批量出算子")
        root.geometry("1280x820")
        root.minsize(1120, 720)

        self.army = load_army(SPEC) if os.path.exists(SPEC) else empty_army()
        self.site = ""
        self._job = None
        self._img = None
        self._editor = None          # 内联编辑用的 Entry

        self._build_toolbar()
        self._build_body()
        self._refresh_tree()
        self._select_first()

    # ---------------- 顶部工具栏
    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="新建编制…", command=self.new_formation).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="＋ 战斗单位", command=lambda: self.add_row("inf")).pack(side="left")
        ttk.Button(bar, text="＋ AV", command=lambda: self.add_row("av")).pack(side="left", padx=2)
        ttk.Button(bar, text="＋ HQ", command=lambda: self.add_row("hq")).pack(side="left")
        ttk.Button(bar, text="＋ 补给车", command=lambda: self.add_row("supply")).pack(side="left", padx=2)
        ttk.Button(bar, text="复制行", command=self.copy_row).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="删除行", command=self.del_row).pack(side="left", padx=2)
        ttk.Button(bar, text="↑", width=3, command=lambda: self.move_row(-1)).pack(side="left")
        ttk.Button(bar, text="↓", width=3, command=lambda: self.move_row(1)).pack(side="left", padx=2)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="生成全部 PNG", command=self.export_all).pack(side="left")
        ttk.Button(bar, text="生成编制卡", command=self.export_charts).pack(side="left", padx=(2, 0))
        ttk.Label(bar, text="尺寸").pack(side="left", padx=(8, 2))
        self.size_var = tk.IntVar(value=75)
        ttk.Combobox(bar, values=[70, 75, 94, 120, 150], width=5,
                     textvariable=self.size_var).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="载入 JSON", command=self.load_json).pack(side="left")
        ttk.Button(bar, text="保存 JSON", command=self.save_json).pack(side="left", padx=2)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="复制编制…", command=self.dup_formation).pack(side="left")
        ttk.Button(bar, text="导出 CSV", command=self.export_csv_file).pack(side="left", padx=2)
        ttk.Button(bar, text="导入 CSV", command=self.import_csv_file).pack(side="left")

    # ---------------- 主体：左表格 / 右编辑
    def _build_body(self):
        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew")
        cols = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=24,
                                 selectmode="browse")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center",
                             stretch=(key in ("unit_id", "formation_id")))
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("hq", background="#eef3e4")
        self.tree.tag_configure("supply", background="#f4f0e2")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.load_row())
        self.tree.bind("<Double-1>", self.begin_edit)
        self.tree.bind("<Delete>", lambda e: self.del_row())

        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        right.grid(row=0, column=1, sticky="ns")
        self._build_form(right)
        self._build_preview(right)

        self.status = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status, foreground="#444",
                  padding=(10, 4)).pack(fill="x")

    def _build_form(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="x")
        self.nb = nb
        tab_basic = ttk.Frame(nb, padding=6)
        tab_side = ttk.Frame(nb, padding=6)
        tab_adv = ttk.Frame(nb, padding=6)
        nb.add(tab_basic, text="基本")
        nb.add(tab_side, text="移动面")
        nb.add(tab_adv, text="高级")

        self.v = {k: tk.StringVar() for k in ROW_TEXT_KEYS + ROW_EXTRA_KEYS}
        self.b = {k: tk.BooleanVar() for k in ROW_BOOL_KEYS}
        self.sw = {}

        def cell(box, r, text, widget, col=0):
            ttk.Label(box, text=text, width=7, anchor="e").grid(
                row=r, column=col * 2, sticky="e", padx=(0, 4), pady=1)
            widget.grid(row=r, column=col * 2 + 1, sticky="we", pady=1)
            box.columnconfigure(col * 2 + 1, weight=1)

        def entry(box, r, key, text, col=0, width=8):
            e = ttk.Entry(box, textvariable=self.v[key], width=width)
            cell(box, r, text, e, col)
            e.bind("<KeyRelease>", lambda ev, k=key: self.push(k))
            return e

        cb_kind = ttk.Combobox(tab_basic, textvariable=self.v["kind"], state="readonly",
                               values=[k for k, _ in R.KINDS], width=10)
        cell(tab_basic, 0, "类型", cb_kind)
        cb_kind.bind("<<ComboboxSelected>>", lambda e: self.push("kind"))

        cb_row_sym = ttk.Combobox(tab_basic, textvariable=self.v["symbol"], state="readonly",
                                  values=[""] + [k for k, _ in R.SYMBOLS], width=10)
        cell(tab_basic, 0, "符号", cb_row_sym, 1)
        cb_row_sym.bind("<<ComboboxSelected>>", lambda e: self.push("symbol"))

        e_unit = ttk.Entry(tab_basic, textvariable=self.v["unit_id"])
        cell(tab_basic, 1, "番号", e_unit)
        e_unit.bind("<KeyRelease>", lambda e: self.push("unit_id"))

        cb_form = ttk.Combobox(tab_basic, textvariable=self.v["formation_id"], width=10,
                               values=[])
        self.cb_form = cb_form
        cell(tab_basic, 2, "编制", cb_form)
        cb_form.bind("<<ComboboxSelected>>", lambda e: self.push("formation_id"))
        cb_form.bind("<KeyRelease>", lambda e: self.push("formation_id"))

        cb_size = ttk.Combobox(tab_basic, textvariable=self.v["size_label"],
                               values=[k for k, _ in R.SIZE_PRESETS], width=10)
        cell(tab_basic, 3, "规模", cb_size)
        cb_size.bind("<<ComboboxSelected>>", lambda e: self.push("size_label"))
        cb_size.bind("<KeyRelease>", lambda e: self.push("size_label"))

        for i, (key, text) in enumerate((("ar", "AR"), ("av", "AV"), ("quality", "素质"),
                                         ("rng", "射程"), ("rng2", "射程2"), ("ma", "MA"))):
            entry(tab_basic, 4 + i % 3, key, text, i // 3)

        cb_mc = ttk.Combobox(tab_basic, textvariable=self.v["move_class"], state="readonly",
                             values=["leg", "truck", "tac"], width=10)
        cell(tab_basic, 7, "移动力", cb_mc)
        cb_mc.bind("<<ComboboxSelected>>", lambda e: self.push("move_class"))

        cb_ac = ttk.Combobox(tab_basic, textvariable=self.v["av_class"], state="readonly",
                             values=["red", "limited", "standoff", "light"], width=10)
        cell(tab_basic, 7, "装甲类", cb_ac, 1)
        cb_ac.bind("<<ComboboxSelected>>", lambda e: self.push("av_class"))

        for i, (key, text) in enumerate((("hard", "Hard 黄框"), ("assault", "突击箭头"),
                                         ("no_rebuild", "不可重建"), ("breakthrough", "突破"))):
            ttk.Checkbutton(tab_basic, text=text, variable=self.b[key],
                            command=lambda k=key: self.push_flag(k)
                            ).grid(row=8 + i // 2, column=(i % 2) * 2,
                                   columnspan=2, sticky="w")

        for i, (key, text) in enumerate((("command_radius", "指挥半径"),
                                         ("arty", "炮兵点数"), ("activation", "激活骰点"))):
            entry(tab_basic, 10 + i, key, text)

        # ---- 移动面：只填需要与正面不同的项
        ttk.Label(tab_side, text="留空 = 沿用正面；填 - = 这一面不画该项。",
                  foreground="#666").grid(row=0, column=0, columnspan=4, sticky="w")
        for i, (key, text) in enumerate((("ar_move", "AR"), ("quality_move", "素质"),
                                         ("av_move", "AV"), ("rng_move", "射程"),
                                         ("rng2_move", "射程2"), ("ma_move", "MA"))):
            entry(tab_side, 1 + i // 2, key, text, i % 2)

        cb_mcm = ttk.Combobox(tab_side, textvariable=self.v["move_class_move"],
                              state="readonly", values=["", "leg", "truck", "tac"],
                              width=10)
        cell(tab_side, 4, "移动力", cb_mcm)
        cb_mcm.bind("<<ComboboxSelected>>", lambda e: self.push("move_class_move"))

        cb_kind_mv = ttk.Combobox(tab_side, textvariable=self.v["kind_move"],
                                  state="readonly", values=[""] + [k for k, _ in R.KINDS],
                                  width=10)
        cell(tab_side, 4, "反面类型", cb_kind_mv, 1)
        cb_kind_mv.bind("<<ComboboxSelected>>", lambda e: self.push("kind_move"))

        ttk.Label(tab_side, text="反面类型不同 = 整枚换一种算子（如正面 av、反面 support）。",
                  foreground="#666").grid(row=5, column=0, columnspan=4, sticky="w")

        # 布尔量的面级三态：留空 = 沿用正面，- = 这一面不画，1/有 = 这一面画
        for i, (key, text) in enumerate((("assault_move", "突击"),
                                         ("hard_move", "Hard"),
                                         ("breakthrough_move", "突破"))):
            cb = ttk.Combobox(tab_side, textvariable=self.v[key], state="readonly",
                              values=["", "-", "1"], width=8)
            cell(tab_side, 7 + i // 2, text, cb, i % 2)
            cb.bind("<<ComboboxSelected>>", lambda e, k=key: self.push(k))

        ttk.Label(tab_side, text="突击箭头等：留空=沿用正面，- = 反面不画，1 = 反面画。",
                  foreground="#666").grid(row=10, column=0, columnspan=4, sticky="w")

        ttk.Checkbutton(tab_side, text="反面 AR 虚化", variable=self.b["back_ghost"],
                        command=lambda: self.push_flag("back_ghost")
                        ).grid(row=11, column=0, columnspan=4, sticky="w")

        # ---- 高级：字号、配色、符号等单算子编辑器的其余选项
        adv = (("name", "大字名"), ("steps", "剩余步数"), ("symbol_text", "符号文字"),
               ("symbol_letters", "自定义字母"), ("support_label", "支援字样"))
        for i, (key, text) in enumerate(adv):
            entry(tab_adv, i // 2, key, text, i % 2, width=11)

        for i, (key, text, vals) in enumerate((
                ("symbol_mode", "符号模式", ["", "letter", "glyph"]),
                ("bar_pos", "色带位置", ["", "top", "bottom", "left", "right", "none"]),
                ("ar_style", "AR画法", ["", "box", "disc", "ghost", "none"]),
                ("range_style", "射程画法", ["", "plain", "chip"]))):
            cb = ttk.Combobox(tab_adv, textvariable=self.v[key], state="readonly",
                              values=vals, width=11)
            cell(tab_adv, 3 + i // 2, text, cb, i % 2)
            cb.bind("<<ComboboxSelected>>", lambda e, k=key: self.push(k))

        for i, (key, text) in enumerate((("band", "机动色带"), ("ink", "主文字色"),
                                         ("value_ink", "数值色"))):
            sw = tk.Button(tab_adv, text="  ", width=5,
                           command=lambda k=key: self.pick_row_color(k))
            cell(tab_adv, 5 + i, text, sw, 0)
            self.sw[key] = sw
            ttk.Button(tab_adv, text="清空", width=4,
                       command=lambda k=key: self.clear_row_color(k)
                       ).grid(row=5 + i, column=2, sticky="w")

        entry(tab_adv, 8, "bar_thickness", "色带厚度")
        entry(tab_adv, 8, "note", "备注", 1, width=11)

        self.v_bgp = tk.StringVar()
        cb_bgp = ttk.Combobox(tab_adv, textvariable=self.v_bgp, state="readonly",
                              values=[""] + list(R.BG_PRESETS.keys()), width=11)
        cell(tab_adv, 9, "底色预设", cb_bgp)
        cb_bgp.bind("<<ComboboxSelected>>",
                    lambda e: self.apply_row_preset("bg", self.v_bgp.get()))

        self.v_bcp = tk.StringVar()
        cb_bcp = ttk.Combobox(tab_adv, textvariable=self.v_bcp, state="readonly",
                              values=list(R.MOVE_CLASS.keys()), width=11)
        cell(tab_adv, 9, "机动等级", cb_bcp, 1)
        cb_bcp.bind("<<ComboboxSelected>>",
                    lambda e: self.apply_row_preset("band", self.v_bcp.get()))

        ttk.Button(tab_adv, text="重置本行", width=10, command=self.reset_row).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(4, 0))

        for i, (key, text) in enumerate((("show_band", "显示机动色带"),
                                         ("gloss", "高光斜面"),
                                         ("hq_box_tint", "HQ 兵牌随色带"))):
            ttk.Checkbutton(tab_adv, text=text, variable=self.b[key],
                            command=lambda k=key: self.push_flag(k)
                            ).grid(row=5 + i, column=4, columnspan=2, sticky="w")

        # ---- 编制设置
        fb = ttk.LabelFrame(parent, text="编制设置（作用于该编制全部算子）", padding=6)
        fb.pack(fill="x", pady=(6, 0))
        self.v_form = tk.StringVar()
        ttk.Label(fb, textvariable=self.v_form, foreground="#333").grid(
            row=0, column=0, columnspan=4, sticky="w")

        ttk.Label(fb, text="底色", width=6, anchor="e").grid(row=1, column=0, sticky="e")
        self.sw_bg = tk.Button(fb, text="  ", bg="#A3BA68", width=6,
                               command=lambda: self.pick_form_color("bg"))
        self.sw_bg.grid(row=1, column=1, sticky="w", pady=2)
        self.v_preset = tk.StringVar()
        cb_pre = ttk.Combobox(fb, textvariable=self.v_preset, state="readonly",
                              values=list(R.BG_PRESETS.keys()), width=14)
        cb_pre.grid(row=1, column=2, columnspan=2, sticky="we", padx=(6, 0))
        cb_pre.bind("<<ComboboxSelected>>", lambda e: self.apply_preset())

        ttk.Label(fb, text="编制色带", width=6, anchor="e").grid(row=2, column=0, sticky="e")
        self.sw_bar = tk.Button(fb, text="  ", bg="#6E8B3D", width=6,
                                command=lambda: self.pick_form_color("bar_color"))
        self.sw_bar.grid(row=2, column=1, sticky="w", pady=2)
        sw = ttk.Frame(fb)
        sw.grid(row=2, column=2, columnspan=2, sticky="w", padx=(6, 0))
        for i, (_nm, hx) in enumerate(R.FORMATION_COLORS.items()):
            tk.Button(sw, width=2, bg=hx, relief="flat", bd=1,
                      command=lambda c=hx: self.set_form_color("bar_color", c)
                      ).grid(row=0, column=i, padx=1)

        ttk.Label(fb, text="兵种符号", width=6, anchor="e").grid(row=3, column=0, sticky="e")
        self.v_sym = tk.StringVar()
        cb_sym = ttk.Combobox(fb, textvariable=self.v_sym, state="readonly", width=14,
                              values=[k for k, _ in R.SYMBOLS])
        cb_sym.grid(row=3, column=1, columnspan=3, sticky="we", pady=2)
        cb_sym.bind("<<ComboboxSelected>>", lambda e: self.set_form_symbol())

    def _build_preview(self, parent):
        box = ttk.LabelFrame(parent, text="预览", padding=6)
        box.pack(fill="both", expand=True, pady=(6, 0))
        self.canvas = tk.Canvas(box, width=380, height=300, bg="#1b1b20",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    # ---------------- 行 ↔ 表单
    def cur(self):
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        return self.army["rows"][idx] if 0 <= idx < len(self.army["rows"]) else None

    def _refresh_tree(self, keep=None):
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.army["rows"]):
            vals = []
            for key, _title, _width in COLUMNS:
                if key == "flags":
                    vals.append(flags_of(row))
                elif key == "side":
                    vals.append(side_note(row))
                else:
                    vals.append(row.get(key, ""))
            tag = row.get("kind") if row.get("kind") in ("hq", "supply") else ""
            self.tree.insert("", "end", iid=str(i), values=vals, tags=(tag,))
        self.cb_form.configure(values=sorted(self.army["formations"].keys()))
        if keep is not None and 0 <= keep < len(self.army["rows"]):
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))

    def _select_first(self):
        if self.army["rows"]:
            self.tree.selection_set("0")
            self.load_row()
        self.set_status()

    def load_row(self):
        row = self.cur()
        if not row:
            return
        for k, var in self.v.items():
            var.set(str(row.get(k, "") or ""))
        for k, var in self.b.items():
            var.set(bool(row.get(k, k in ROW_BOOL_ON)))
        fid = str(row.get("formation_id", "") or "")
        form = formation_of(self.army, fid) if fid else {}
        self.v_form.set(f"当前编制：{fid or '（未填）'}")
        self.sw_bg.configure(bg=form.get("bg", "#A3BA68"))
        self.sw_bar.configure(bg=form.get("bar_color", "#6E8B3D"))
        self.v_sym.set(form.get("symbol", "inf"))
        for key, btn in self.sw.items():
            val = str(row.get(key, "") or "") or (
                form.get("band", "#E8C10C") if key == "band" else "#4a4a52")
            btn.configure(bg=val)
        self.redraw_preview()

    def push(self, key, *_):
        row = self.cur()
        if not row:
            return
        row[key] = self.v[key].get()
        sel = self.tree.selection()
        self._touch()
        self._refresh_tree(keep=int(sel[0]) if sel else None)

    def push_flag(self, key):
        row = self.cur()
        if not row:
            return
        row[key] = bool(self.b[key].get())
        sel = self.tree.selection()
        self._touch()
        self._refresh_tree(keep=int(sel[0]) if sel else None)

    def apply_row_preset(self, kind, name):
        row = self.cur()
        if not row or not name:
            return
        if kind == "bg":
            bg, band = R.BG_PRESETS[name]
            row["bg"], row["band"] = bg, band
            row["show_band"] = True
        else:
            col = R.MOVE_CLASS[name]
            if col == "none":
                row["band"], row["show_band"] = "", False
            else:
                row["band"], row["show_band"] = col, True
        self.b["show_band"].set(bool(row["show_band"]))
        sel = self.tree.selection()
        self.load_row()
        self._touch()
        self._refresh_tree(keep=int(sel[0]) if sel else None)

    def reset_row(self):
        row = self.cur()
        if not row:
            return
        keep_kind = str(row.get("kind", "inf") or "inf")
        keep_form = str(row.get("formation_id", "") or "")
        row.clear()
        row.update(new_row(keep_kind, keep_form))
        sel = self.tree.selection()
        self.load_row()
        self._touch()
        self._refresh_tree(keep=int(sel[0]) if sel else None)

    def _touch(self):
        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(150, self._after_touch)

    def _after_touch(self):
        self._job = None
        self.redraw_preview()
        self.set_status()

    # ---------------- 内联编辑（双击单元格）
    def begin_edit(self, event):
        iid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not iid or not col:
            return
        keys = [c[0] for c in COLUMNS]
        idx = int(col.replace("#", "")) - 1
        if idx < 0 or idx >= len(keys) or keys[idx] not in TEXT_COLS:
            return
        key = keys[idx]
        x, y, w, h = self.tree.bbox(iid, col)
        if not w:
            return
        row = self.army["rows"][int(iid)]
        ent = ttk.Entry(self.tree)
        ent.insert(0, str(row.get(key, "") or ""))
        ent.select_range(0, "end")
        ent.place(x=x, y=y, width=w, height=h)
        ent.focus_set()

        def commit(_=None):
            if not ent.winfo_exists():
                return
            row[key] = ent.get()
            ent.destroy()
            self._touch()
            self._refresh_tree(keep=int(iid))
            if key == "formation_id":
                self.load_row()

        ent.bind("<Return>", commit)
        ent.bind("<FocusOut>", commit)
        ent.bind("<Escape>", lambda e: ent.destroy())

    # ---------------- 增删改
    def add_row(self, kind):
        row = self.cur()
        fid = row.get("formation_id") if row else ""
        if not fid and self.army["formations"]:
            fid = sorted(self.army["formations"])[0]
        if not fid:
            messagebox.showinfo("提示", "请先「新建编制」，再往里加算子。")
            return
        extra = {}
        if kind == "hq":
            extra = dict(ar="10", ma="8", command_radius="10", arty="4",
                         activation="4", size_label="XX")
        elif kind == "supply":
            extra = dict(ar="", quality="", ma="", size_label="")
        self.army["rows"].append(new_row(kind, fid, **extra))
        self._refresh_tree(keep=len(self.army["rows"]) - 1)
        self.load_row()

    def copy_row(self):
        row = self.cur()
        if not row:
            return
        idx = self.army["rows"].index(row)
        self.army["rows"].insert(idx + 1, dict(row))
        self._refresh_tree(keep=idx + 1)
        self.load_row()

    def del_row(self):
        row = self.cur()
        if not row:
            return
        idx = self.army["rows"].index(row)
        del self.army["rows"][idx]
        self._refresh_tree(keep=min(idx, len(self.army["rows"]) - 1))
        self.load_row()

    def move_row(self, step):
        row = self.cur()
        if not row:
            return
        idx = self.army["rows"].index(row)
        j = idx + step
        if 0 <= j < len(self.army["rows"]):
            self.army["rows"][idx], self.army["rows"][j] = (
                self.army["rows"][j], self.army["rows"][idx])
            self._refresh_tree(keep=j)
            self.load_row()


    # ---------------- 整编制复制 / CSV
    def dup_formation(self):
        row = self.cur()
        src0 = str(row.get("formation_id", "") or "") if row else ""
        if not self.army["formations"]:
            messagebox.showinfo("提示", "还没有编制可复制。")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("整编制复制")
        dlg.transient(self.root)
        dlg.grab_set()
        f = ttk.Frame(dlg, padding=12)
        f.pack(fill="both", expand=True)

        v = {k: tk.StringVar() for k in ("src", "dst", "hq", "suffix")}
        v["src"].set(src0 or sorted(self.army["formations"])[0])
        v["dst"].set((src0 or "New") + " (copy)")
        copy_colors = tk.BooleanVar(value=True)

        ttk.Label(f, text="源编制", width=10, anchor="e").grid(row=0, column=0, sticky="e", pady=2)
        cb_src = ttk.Combobox(f, textvariable=v["src"], state="readonly",
                              values=sorted(self.army["formations"]))
        cb_src.grid(row=0, column=1, sticky="we", pady=2)
        ttk.Label(f, text="新编制番号", width=10, anchor="e").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(f, textvariable=v["dst"]).grid(row=1, column=1, sticky="we", pady=2)
        ttk.Label(f, text="新 HQ 番号", width=10, anchor="e").grid(row=2, column=0, sticky="e", pady=2)
        ttk.Entry(f, textvariable=v["hq"]).grid(row=2, column=1, sticky="we", pady=2)
        ttk.Label(f, text="番号后缀", width=10, anchor="e").grid(row=3, column=0, sticky="e", pady=2)
        ttk.Entry(f, textvariable=v["suffix"]).grid(row=3, column=1, sticky="we", pady=2)
        ttk.Checkbutton(f, text="沿用源编制的底色 / 色带 / 符号", variable=copy_colors
                        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(f, text="提示：HQ 番号留空则沿用原值；后缀会拼在每行番号之后（如 /11）。",
                  foreground="#666", wraplength=320).grid(row=5, column=0, columnspan=2,
                                                          sticky="w", pady=(6, 0))
        f.columnconfigure(1, weight=1)

        def ok():
            src, dst = v["src"].get().strip(), v["dst"].get().strip()
            if not dst:
                messagebox.showwarning("提示", "新编制番号不能为空。", parent=dlg)
                return
            n = duplicate_formation(self.army, src, dst, v["hq"].get().strip(),
                                    bool(copy_colors.get()), v["suffix"].get().strip())
            dlg.destroy()
            if n:
                self._refresh_tree(keep=len(self.army["rows"]) - 1)
                self.set_status(f"已复制编制「{src}」→「{dst}」，共 {n} 行")
            else:
                messagebox.showinfo("提示", "没有可复制的行（源编制为空？）")

        ttk.Button(f, text="复制", command=ok).grid(row=6, column=0, columnspan=2,
                                                   sticky="we", pady=(10, 0))

    def export_csv_file(self):
        os.makedirs(OUTDIR, exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            initialfile="army.csv")
        if not path:
            return
        n = export_csv(self.army, path)
        self.set_status(f"已导出 {n} 行 → {path}")
        messagebox.showinfo("完成", f"已导出 {n} 行到\n{path}\n\n可用 Excel 直接打开（UTF-8 BOM）。")

    def import_csv_file(self):
        path = filedialog.askopenfilename(initialdir=OUTDIR,
                                          filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            army = import_csv(path)
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))
            return
        if not army["rows"]:
            messagebox.showwarning("提示", "这个 CSV 里没有可用的行。")
            return
        self.army = army
        self._refresh_tree()
        self._select_first()
        self.set_status(f"已导入 {len(army['rows'])} 行 / "
                        f"{len(army['formations'])} 个编制：{path}")

    # ---------------- 编制
    def new_formation(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("新建编制")
        dlg.transient(self.root)
        dlg.grab_set()
        f = ttk.Frame(dlg, padding=12)
        f.pack(fill="both", expand=True)
        v = {k: tk.StringVar() for k in ("fid", "hq_id", "bg", "bar", "symbol")}
        v["bg"].set("#A3BA68")
        v["bar"].set("#6E8B3D")
        v["symbol"].set("inf")
        for i, (key, label) in enumerate((("fid", "编制番号"), ("hq_id", "HQ 番号"),
                                          ("bg", "底色"), ("bar", "编制色带"))):
            ttk.Label(f, text=label, width=10, anchor="e").grid(row=i, column=0, sticky="e", pady=2)
            ttk.Entry(f, textvariable=v[key]).grid(row=i, column=1, sticky="we", pady=2)
        ttk.Label(f, text="兵种符号", width=10, anchor="e").grid(row=4, column=0, sticky="e")
        cb = ttk.Combobox(f, textvariable=v["symbol"], state="readonly",
                          values=[k for k, _ in R.SYMBOLS])
        cb.grid(row=4, column=1, sticky="we", pady=2)
        f.columnconfigure(1, weight=1)

        def ok():
            fid = v["fid"].get().strip()
            if not fid:
                messagebox.showwarning("提示", "编制番号不能为空。", parent=dlg)
                return
            add_formation(self.army, fid, v["bg"].get().strip() or "#A3BA68",
                          v["bar"].get().strip() or "#6E8B3D", v["symbol"].get(),
                          hq_id=v["hq_id"].get().strip())
            dlg.destroy()
            self._refresh_tree(keep=len(self.army["rows"]) - 3)
            self.load_row()

        ttk.Button(f, text="创建", command=ok).grid(row=5, column=0, columnspan=2,
                                                   sticky="we", pady=(8, 0))

    def pick_row_color(self, key):
        row = self.cur()
        if not row:
            return
        _rgb, hx = colorchooser.askcolor(color=str(row.get(key, "") or "#808080"))
        if hx:
            self.v[key].set(hx.upper())
            self.push(key)

    def clear_row_color(self, key):
        self.v[key].set("")
        self.push(key)

    def set_form_color(self, key, hx):
        row = self.cur()
        if not row:
            return
        fid = str(row.get("formation_id", "") or "")
        if not fid:
            return
        formation_of(self.army, fid)[key] = hx
        if key == "bg":
            self.sw_bg.configure(bg=hx)
        else:
            self.sw_bar.configure(bg=hx)
        self.redraw_preview()

    def pick_form_color(self, key):
        row = self.cur()
        if not row:
            return
        fid = str(row.get("formation_id", "") or "")
        if not fid:
            messagebox.showinfo("提示", "这一行还没填编制。")
            return
        form = formation_of(self.army, fid)
        rgb, hx = colorchooser.askcolor(color=form.get(key, "#808080"))
        if hx:
            self.set_form_color(key, hx)

    def apply_preset(self):
        row = self.cur()
        if not row:
            return
        fid = str(row.get("formation_id", "") or "")
        if not fid:
            return
        bg, band = R.BG_PRESETS[self.v_preset.get()]
        form = formation_of(self.army, fid)
        form["bg"], form["band"] = bg, band
        self.sw_bg.configure(bg=bg)
        self.redraw_preview()

    def set_form_symbol(self):
        row = self.cur()
        if not row:
            return
        fid = str(row.get("formation_id", "") or "")
        if not fid:
            return
        formation_of(self.army, fid)["symbol"] = self.v_sym.get()
        self.redraw_preview()

    # ---------------- 预览 / 导出 / 存取
    def redraw_preview(self):
        row = self.cur()
        if not row:
            return
        fid = str(row.get("formation_id", "") or "")
        if not fid:
            return
        form = formation_of(self.army, fid)
        ct = counter_from(row, form)
        a = R.render(ct.copy(side="front"), 190)
        b = R.render(ct.copy(side="back"), 190)
        w = a.width + b.width + 12
        canvas = Image.new("RGBA", (w, max(a.height, b.height)), (27, 27, 32, 255))
        canvas.alpha_composite(a, (0, 0))
        canvas.alpha_composite(b, (a.width + 12, 0))
        self._img = ImageTk.PhotoImage(canvas)
        self.canvas.delete("all")
        self.canvas.create_image(4, 4, image=self._img, anchor="nw")

    def export_all(self):
        row = self.cur()
        site = "all"
        if row:
            fid = str(row.get("formation_id", "") or "")
            site = slug(fid) if fid else "all"
        outdir = os.path.join(OUTDIR, site) if len(self.army["formations"]) > 1 else OUTDIR
        size = int(self.size_var.get() or 75)
        res = export_army(self.army, outdir, size=size, charts=True)
        self.set_status(f"已生成 {res['count']} 枚算子 / {len(res['files'])} 个文件 → {outdir}")
        messagebox.showinfo("完成", f"已生成 {res['count']} 枚算子\n共 {len(res['files'])} 个文件\n\n{outdir}")

    def export_charts(self):
        """只出编制卡（每个编制一张 + 总览）。"""
        import bcs_chart
        outdir = os.path.join(OUTDIR, "charts")
        res = bcs_chart.export_charts(self.army, outdir)
        self.set_status(f"已生成 {res['count']} 张编制卡 → {outdir}")
        messagebox.showinfo("完成", f"已生成 {res['count']} 张编制卡\n共 {len(res['files'])} 个文件\n\n{outdir}")

    def save_json(self):
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="army.json")
        if path:
            save_army(self.army, path)
            self.set_status(f"已保存 {path}")

    def load_json(self):
        path = filedialog.askopenfilename(initialdir=OUTDIR, filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.army = load_army(path)
        except Exception as exc:
            messagebox.showerror("载入失败", str(exc))
            return
        self._refresh_tree()
        self._select_first()
        self.set_status(f"已载入 {path}（{len(self.army['rows'])} 行）")

    def set_status(self, text: str = None):
        if text:
            self.status.set(text)
        else:
            n = len(self.army["rows"])
            f = len(self.army["formations"])
            self.status.set(f"{n} 行 · {f} 个编制 · 双击单元格可直接改番号/规模/数值；"
                            f"「生成全部 PNG」输出到 {OUTDIR}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    def _arg(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    # CSV 导出（从现有军队 json 或示例军队出发）
    if "--export-csv" in argv:
        src = _arg("--spec", SPEC if os.path.exists(SPEC) else None)
        dst = _arg("--export-csv")
        army = load_army(src) if src else empty_army()
        n = export_csv(army, dst)
        print(f"已导出 {n} 行 → {dst}")
        return 0

    # CSV 导入后直接出图
    if "--import-csv" in argv:
        army = import_csv(_arg("--import-csv"))
        out = _arg("--out", OUTDIR)
        size = int(_arg("--size", 75))
        res = export_army(army, out, size=size)
        print(f"已导入 {len(army['rows'])} 行；生成 {res['count']} 枚算子 / "
              f"{len(res['files'])} 个文件 → {out}")
        return 0

    if "--spec" in argv:
        spec = argv[argv.index("--spec") + 1]
        out = argv[argv.index("--out") + 1] if "--out" in argv else OUTDIR
        size = int(argv[argv.index("--size") + 1]) if "--size" in argv else 75
        army = load_army(spec)
        res = export_army(army, out, size=size, charts="--charts" in argv)
        extra = ""
        if "--charts" in argv:
            import bcs_chart
            charts = len(army["formations"])
            extra = f"（含 {charts} 张编制卡）"
        print(f"已生成 {res['count']} 枚算子 / {len(res['files'])} 个文件{extra} → {out}")
        return 0
    root = tk.Tk()
    ArmyApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
