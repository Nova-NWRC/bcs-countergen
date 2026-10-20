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
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else HERE
OUTDIR = os.path.join(BASE, "out", "army")
SPEC = os.path.join(BASE, "samples", "army_demo.json")

TEXT_COLS = ("unit_id", "formation_id", "size_label", "ar", "av", "quality", "rng", "ma")
COLUMNS = [
    ("kind", "类型", 82),
    ("unit_id", "番号", 84),
    ("formation_id", "编制", 76),
    ("size_label", "规模", 54),
    ("ar", "AR", 38),
    ("av", "AV", 38),
    ("quality", "素质", 42),
    ("rng", "射程", 42),
    ("ma", "MA", 40),
    ("move_class", "移动力", 58),
    ("av_class", "装甲类", 62),
    ("flags", "标记", 74),
]

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
               ar="5", av="", quality="3", rng="", ma="8",
               move_class="tac", av_class="red",
               hard=False, assault=False, no_rebuild=False, breakthrough=False,
               command_radius="", arty="", activation="")
    row.update(kw)
    return row


def counter_from(row: dict, form: dict) -> R.Counter:
    """把表格行 + 编制设置落成一枚 Counter。"""
    kind = row.get("kind", "inf")
    sym = (row.get("symbol") or "").strip() or form.get("symbol") or KIND_SYMBOL.get(kind, "inf")
    ct = R.Counter(
        kind=kind,
        unit_id=str(row.get("unit_id", "") or ""),
        formation_id=str(row.get("formation_id", "") or ""),
        size_label=str(row.get("size_label", "") or ""),
        ar=str(row.get("ar", "") or ""),
        av=str(row.get("av", "") or ""),
        quality=str(row.get("quality", "") or ""),
        rng=str(row.get("rng", "") or ""),
        ma=str(row.get("ma", "") or ""),
        move_class=row.get("move_class") or "tac",
        av_class=row.get("av_class") or "red",
        symbol=sym,
        symbol_mode="glyph" if kind in ("hq",) else "letter",
        bg=form.get("bg", "#A3BA68"),
        band=form.get("band", "#E8C10C"),
        bar_color=form.get("bar_color", "#6E8B3D"),
        show_band=False,
        command_radius=str(row.get("command_radius", "") or ""),
        arty=str(row.get("arty", "") or ""),
        activation=str(row.get("activation", "") or ""),
        no_rebuild=bool(row.get("no_rebuild")),
        hard=bool(row.get("hard")),
        assault=bool(row.get("assault")),
        breakthrough=bool(row.get("breakthrough")),
    )
    if kind == "supply":
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



CSV_FIELDS = ["kind", "unit_id", "formation_id", "size_label", "ar", "av", "quality",
              "rng", "ma", "move_class", "av_class", "hard", "assault", "no_rebuild",
              "breakthrough", "command_radius", "arty", "activation",
              "bg", "bar_color", "symbol"]
CSV_TEXT = ["kind", "unit_id", "formation_id", "size_label", "ar", "av", "quality",
            "rng", "ma", "move_class", "av_class", "command_radius", "arty", "activation",
            "symbol"]
CSV_BOOL = ["hard", "assault", "no_rebuild", "breakthrough"]
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
                    out[k] = 1 if row.get(k) else 0
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
                sheet: bool = True) -> dict:
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
        box = ttk.LabelFrame(parent, text="行属性", padding=6)
        box.pack(fill="x")

        def row(widget, r, label, col=0):
            ttk.Label(box, text=label, width=8, anchor="e").grid(
                row=r, column=col * 2, sticky="e", padx=(0, 4), pady=1)
            widget.grid(row=r, column=col * 2 + 1, sticky="we", pady=1)
            box.columnconfigure(col * 2 + 1, weight=1)

        self.v = {k: tk.StringVar() for k in
                  ("kind", "unit_id", "formation_id", "size_label", "ar", "av",
                   "quality", "rng", "ma", "move_class", "av_class",
                   "command_radius", "arty", "activation")}
        self.b = {k: tk.BooleanVar() for k in
                  ("hard", "assault", "no_rebuild", "breakthrough")}

        cb_kind = ttk.Combobox(box, textvariable=self.v["kind"], state="readonly",
                               values=[k for k, _ in R.KINDS], width=10)
        row(cb_kind, 0, "类型")
        cb_kind.bind("<<ComboboxSelected>>", lambda e: self.push("kind"))

        e_unit = ttk.Entry(box, textvariable=self.v["unit_id"])
        row(e_unit, 1, "番号")
        e_unit.bind("<KeyRelease>", lambda e: self.push("unit_id"))

        cb_form = ttk.Combobox(box, textvariable=self.v["formation_id"], width=10,
                               values=[])
        self.cb_form = cb_form
        row(cb_form, 2, "编制")
        cb_form.bind("<<ComboboxSelected>>", lambda e: self.push("formation_id"))
        cb_form.bind("<KeyRelease>", lambda e: self.push("formation_id"))

        cb_size = ttk.Combobox(box, textvariable=self.v["size_label"],
                               values=[k for k, _ in R.SIZE_PRESETS], width=10)
        row(cb_size, 3, "规模")
        cb_size.bind("<<ComboboxSelected>>", lambda e: self.push("size_label"))
        cb_size.bind("<KeyRelease>", lambda e: self.push("size_label"))

        for i, (key, label) in enumerate((("ar", "AR"), ("av", "AV"),
                                          ("quality", "素质"), ("rng", "射程"),
                                          ("ma", "MA"))):
            e = ttk.Entry(box, textvariable=self.v[key], width=8)
            row(e, 4 + i, label)
            e.bind("<KeyRelease>", lambda ev, k=key: self.push(k))

        cb_mc = ttk.Combobox(box, textvariable=self.v["move_class"], state="readonly",
                             values=["leg", "truck", "tac"], width=10)
        row(cb_mc, 9, "移动力")
        cb_mc.bind("<<ComboboxSelected>>", lambda e: self.push("move_class"))

        cb_ac = ttk.Combobox(box, textvariable=self.v["av_class"], state="readonly",
                             values=["red", "limited", "standoff", "light"], width=10)
        row(cb_ac, 10, "装甲类")
        cb_ac.bind("<<ComboboxSelected>>", lambda e: self.push("av_class"))

        for i, (key, label) in enumerate((("hard", "Hard 黄框"), ("assault", "突击箭头"),
                                          ("no_rebuild", "不可重建"), ("breakthrough", "突破"))):
            ttk.Checkbutton(box, text=label, variable=self.b[key],
                            command=lambda k=key: self.push_flag(k)
                            ).grid(row=11 + i // 2, column=(i % 2) * 2,
                                   columnspan=2, sticky="w")

        for i, (key, label) in enumerate((("command_radius", "指挥半径"),
                                          ("arty", "炮兵点数"), ("activation", "激活骰点"))):
            e = ttk.Entry(box, textvariable=self.v[key], width=8)
            row(e, 13 + i, label)
            e.bind("<KeyRelease>", lambda ev, k=key: self.push(k))

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
            vals = [row.get(k, "") for k in
                    ("kind", "unit_id", "formation_id", "size_label", "ar", "av",
                     "quality", "rng", "ma", "move_class", "av_class")]
            vals.append(flags_of(row))
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
            var.set(bool(row.get(k)))
        fid = str(row.get("formation_id", "") or "")
        form = formation_of(self.army, fid) if fid else {}
        self.v_form.set(f"当前编制：{fid or '（未填）'}")
        self.sw_bg.configure(bg=form.get("bg", "#A3BA68"))
        self.sw_bar.configure(bg=form.get("bar_color", "#6E8B3D"))
        self.v_sym.set(form.get("symbol", "inf"))
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
        res = export_army(self.army, outdir, size=size)
        self.set_status(f"已生成 {res['count']} 枚算子 / {len(res['files'])} 个文件 → {outdir}")
        messagebox.showinfo("完成", f"已生成 {res['count']} 枚算子\n共 {len(res['files'])} 个文件\n\n{outdir}")

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
        res = export_army(army, out, size=size)
        print(f"已生成 {res['count']} 枚算子 / {len(res['files'])} 个文件 → {out}")
        return 0
    root = tk.Tk()
    ArmyApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
