# -*- coding: utf-8 -*-
"""
BCS 算子生成器 —— 图形界面
左侧实时预览正面/背面，右侧参数面板；支持导出单张 PNG、成对 PNG、JSON 存档与批量导出。
运行： python bcs_gui.py
"""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from dataclasses import asdict, fields
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import ImageTk

import bcs_render as R

FROZEN = getattr(sys, "frozen", False)
HERE = os.path.dirname(os.path.abspath(__file__))
RES = getattr(sys, "_MEIPASS", HERE)                 # 打包成 exe 后的资源目录
BASE = os.path.dirname(sys.executable) if FROZEN else HERE
OUTDIR = os.path.join(BASE, "out")


def hexed(t):
    return R.tohex(t) if not isinstance(t, str) else t


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("BCS 算子生成器 · Unit-Key 版式")
        root.geometry("1200x800")
        root.minsize(1080, 720)

        self.ct = R.Counter(kind="inf", unit_id="II/505", formation_id="10 GD")
        self.zoom = tk.IntVar(value=4)
        self.out_size = tk.IntVar(value=75)
        self.vars: dict[str, tk.Variable] = {}
        self._imgrefs = []
        self._job = None

        self._build_preview()
        self._build_panel()
        self._sync_to_widgets()
        self.refresh()

    # ------------------------------------------------------------ 预览区
    def _build_preview(self):
        left = ttk.Frame(self.root, padding=10)
        left.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(left, bg="#18181c", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Label(bar, text="预览缩放").pack(side="left")
        ttk.Spinbox(bar, from_=1, to=8, width=4, textvariable=self.zoom,
                    command=self.refresh).pack(side="left", padx=4)
        ttk.Label(bar, text="导出尺寸").pack(side="left", padx=(14, 0))
        ttk.Combobox(bar, values=[70, 75, 94, 120, 150, 300], width=5,
                     textvariable=self.out_size).pack(side="left", padx=4)
        ttk.Button(bar, text="导出正面 PNG", command=lambda: self.export("front")).pack(side="left", padx=4)
        ttk.Button(bar, text="导出背面 PNG", command=lambda: self.export("back")).pack(side="left", padx=4)
        ttk.Button(bar, text="导出成对 PNG", command=self.export_pair).pack(side="left", padx=4)

        bar2 = ttk.Frame(left)
        bar2.pack(fill="x", pady=(6, 0))
        ttk.Button(bar2, text="保存算子 JSON", command=self.save_json).pack(side="left")
        ttk.Button(bar2, text="载入算子 JSON", command=self.load_json).pack(side="left", padx=4)
        ttk.Button(bar2, text="批量导出 (JSON 列表 → 文件夹)", command=self.batch).pack(side="left", padx=4)
        ttk.Button(bar2, text="导出样例样张", command=self.export_sheet).pack(side="left", padx=4)
        ttk.Separator(bar2, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar2, text="◀ 上一枚", command=lambda: self.browse(-1)).pack(side="left")
        ttk.Button(bar2, text="下一枚 ▶", command=lambda: self.browse(1)).pack(side="left", padx=4)
        ttk.Button(bar2, text="载入示例库", command=self.load_gallery).pack(side="left", padx=4)

    # ------------------------------------------------------------ 参数面板
    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, width=430, highlightthickness=0, bg="#f2f2f2")
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, padding=(8, 6))
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # 滚轮
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        return inner

    def _build_panel(self):
        right = ttk.Frame(self.root)
        right.pack(side="right", fill="y")
        p = self._scrollable(right)

        def group(title):
            f = ttk.LabelFrame(p, text=title, padding=6)
            f.pack(fill="x", pady=4)
            return f

        def row(f, label, widget, r):
            ttk.Label(f, text=label, width=13, anchor="e").grid(row=r, column=0, sticky="e", pady=2)
            widget.grid(row=r, column=1, sticky="we", pady=2)
            f.columnconfigure(1, weight=1)

        # --- 类型
        g = group("① 类型与符号")
        self.vars["kind"] = tk.StringVar()
        cb = ttk.Combobox(g, textvariable=self.vars["kind"], state="readonly",
                          values=[f"{k} · {n}" for k, n in R.KINDS])
        row(g, "算子类型", cb, 0)
        cb.bind("<<ComboboxSelected>>", lambda e: self._apply_choice("kind", R.KINDS))

        self.vars["symbol"] = tk.StringVar()
        cb2 = ttk.Combobox(g, textvariable=self.vars["symbol"], state="readonly",
                           values=[f"{k} · {n}" for k, n in R.SYMBOLS])
        row(g, "兵种符号", cb2, 1)
        cb2.bind("<<ComboboxSelected>>", lambda e: self._apply_choice("symbol", R.SYMBOLS))

        self.vars["symbol_mode"] = tk.StringVar()
        cb4 = ttk.Combobox(g, textvariable=self.vars["symbol_mode"], state="readonly",
                           values=["letter", "glyph"])
        row(g, "符号画法", cb4, 2)
        cb4.bind("<<ComboboxSelected>>", lambda e: self._push("symbol_mode", self.vars["symbol_mode"].get()))

        self.vars["symbol_letters"] = tk.StringVar()
        row(g, "字母代号", self._entry(g, "symbol_letters"), 3)
        self.vars["symbol_text"] = tk.StringVar()
        row(g, "符号文字", self._entry(g, "symbol_text"), 4)
        ttk.Label(g, text="（letter=用字母代号，留空自动取 INF/ARM/RCN…；glyph=图形符号；"
                          "text 用自定义符号文字）",
                  foreground="#666", wraplength=380).grid(row=5, column=0, columnspan=2, sticky="w")

        # --- 番号
        g = group("② 番号 · 编制 · 规模")
        for i, (key, label) in enumerate([
                ("unit_id", "单位番号(左竖)"), ("formation_id", "编制 ID(右竖)")]):
            self.vars[key] = tk.StringVar()
            row(g, label, self._entry(g, key), i)

        # 编制规模：北约符号下拉（I 连 / II 营 / III 团 / X 旅 / XX 师 / XXX 军 …），也可手输
        self.vars["size_label"] = tk.StringVar()
        cb_size = ttk.Combobox(g, textvariable=self.vars["size_label"],
                               values=[f"{k} · {n}" for k, n in R.SIZE_PRESETS])
        row(g, "单位规模", cb_size, 2)
        cb_size.bind("<<ComboboxSelected>>",
                     lambda e: self._push("size_label", self.vars["size_label"].get().split(" · ")[0]))
        cb_size.bind("<KeyRelease>", lambda e: self._push("size_label", self.vars["size_label"].get()))

        self.vars["name"] = tk.StringVar()
        row(g, "大字名 / KG 名", self._entry(g, "name"), 3)

        # --- 数值
        g = group("③ 数值")
        for i, (key, label) in enumerate([
                ("ar", "顶部小框值"), ("quality", "素质值(中轴上)"), ("av", "装甲值 AV"),
                ("rng", "射程(中轴下)"), ("rng2", "射程第二行"), ("ma", "机动力 MA"),
                ("steps", "Steps"), ("activation", "激活骰点"),
                ("ma_move", "移动面机动力"), ("quality_move", "移动面素质"),
                ("command_radius", "指挥半径"), ("arty", "炮兵点数")]):
            self.vars[key] = tk.StringVar()
            row(g, label, self._entry(g, key), i)
        self.vars["ar_style"] = tk.StringVar()
        cb3 = ttk.Combobox(g, textvariable=self.vars["ar_style"], state="readonly",
                           values=["box", "disc", "ghost", "none"])
        row(g, "AR 样式", cb3, 13)
        cb3.bind("<<ComboboxSelected>>", lambda e: self._push("ar_style", self.vars["ar_style"].get()))

        self.vars["range_style"] = tk.StringVar()
        cb5 = ttk.Combobox(g, textvariable=self.vars["range_style"], state="readonly",
                           values=["plain", "chip"])
        row(g, "中轴列样式", cb5, 14)
        cb5.bind("<<ComboboxSelected>>", lambda e: self._push("range_style", self.vars["range_style"].get()))

        self.vars["support_values"] = tk.BooleanVar()
        ttk.Checkbutton(g, text="支援单位叠加数值", variable=self.vars["support_values"],
                        command=lambda: self._push(
                            "support_values", bool(self.vars["support_values"].get()))
                        ).grid(row=15, column=0, columnspan=2, sticky="w")

        for i, (key, label) in enumerate([("assault", "突击箭头"), ("hard", "Hard 黄框"),
                                          ("breakthrough", "突破型小三角")]):
            self.vars[key] = tk.BooleanVar()
            cbx = ttk.Checkbutton(g, text=label, variable=self.vars[key],
                                  command=lambda k=key: self._push(k, bool(self.vars[k].get())))
            cbx.grid(row=16 + i, column=0, columnspan=2, sticky="w")

        self.vars["move_class"] = tk.StringVar()
        cb_mc = ttk.Combobox(g, textvariable=self.vars["move_class"], state="readonly",
                             values=["leg", "truck", "tac"])
        row(g, "移动力类型", cb_mc, 20)
        cb_mc.bind("<<ComboboxSelected>>",
                   lambda e: self._push("move_class", self.vars["move_class"].get()))

        self.vars["av_class"] = tk.StringVar()
        cb_ac = ttk.Combobox(g, textvariable=self.vars["av_class"], state="readonly",
                             values=["red", "limited", "standoff", "light"])
        row(g, "装甲值类型", cb_ac, 21)
        cb_ac.bind("<<ComboboxSelected>>",
                   lambda e: self._push("av_class", self.vars["av_class"].get()))

        self.vars["hq_box_tint"] = tk.BooleanVar()
        ttk.Checkbutton(g, text="HQ 兵牌底色跟随编制色带", variable=self.vars["hq_box_tint"],
                        command=lambda: self._push("hq_box_tint",
                                                   bool(self.vars["hq_box_tint"].get()))
                        ).grid(row=22, column=0, columnspan=2, sticky="w")

        self.vars["move_class_move"] = tk.StringVar()
        cb_mcm = ttk.Combobox(g, textvariable=self.vars["move_class_move"], state="readonly",
                              values=["", "leg", "truck", "tac"])
        row(g, "移动面移动力类型", cb_mcm, 24)
        cb_mcm.bind("<<ComboboxSelected>>",
                    lambda e: self._push("move_class_move", self.vars["move_class_move"].get()))

        self.vars["back_ghost"] = tk.BooleanVar()
        ttk.Checkbutton(g, text="移动面 AR 虚化（背面）", variable=self.vars["back_ghost"],
                        command=lambda: self._push(
                            "back_ghost", bool(self.vars["back_ghost"].get()))
                        ).grid(row=25, column=0, columnspan=2, sticky="w")

        for i, (key, label) in enumerate([("av_move", "移动面装甲值"),
                                          ("rng_move", "移动面射程"),
                                          ("rng2_move", "移动面射程第二行")]):
            self.vars[key] = tk.StringVar()
            row(g, label, self._entry(g, key), 26 + i)
        ttk.Label(g, text="移动面：留空 = 沿用正面；填 - = 这一面不画该项",
                  foreground="#666", wraplength=380).grid(row=29, column=0, columnspan=2,
                                                          sticky="w")

        # --- 配色
        g = group("④ 配色 · 色带")
        self.vars["bg_preset"] = tk.StringVar()
        cbp = ttk.Combobox(g, textvariable=self.vars["bg_preset"], state="readonly",
                           values=list(R.BG_PRESETS.keys()))
        row(g, "底色预设", cbp, 0)
        cbp.bind("<<ComboboxSelected>>", lambda e: self._apply_bg_preset())

        self.sw_bg = tk.Button(g, text="  底色  ", bg="#A3BA68", command=lambda: self._pick("bg"))
        row(g, "底色", self.sw_bg, 1)

        self.vars["band_preset"] = tk.StringVar()
        cbm = ttk.Combobox(g, textvariable=self.vars["band_preset"], state="readonly",
                           values=list(R.MOVE_CLASS.keys()))
        row(g, "机动等级", cbm, 2)
        cbm.bind("<<ComboboxSelected>>", lambda e: self._apply_band_preset())

        self.sw_band = tk.Button(g, text="  色带  ", bg="#E8C10C", command=lambda: self._pick("band"))
        row(g, "机动色带", self.sw_band, 3)

        self.sw_bar = tk.Button(g, text=" 编制色带 ", bg="#C0392B", command=lambda: self._pick("bar_color"))
        row(g, "编制色带", self.sw_bar, 4)

        # 师/编制配色快选（12 色，点一下即套到底边编制色带）
        sw = ttk.Frame(g)
        sw.grid(row=5, column=0, columnspan=2, sticky="we", pady=2)
        for i, (_nm, _hx) in enumerate(R.FORMATION_COLORS.items()):
            tk.Button(sw, width=2, bg=_hx, relief="flat", bd=1,
                      command=lambda c=_hx: self._set_bar_color(c)
                      ).grid(row=i // 6, column=i % 6, padx=1, pady=1, sticky="we")
            sw.columnconfigure(i % 6, weight=1)

        self.vars["bar_pos"] = tk.StringVar()
        cbb = ttk.Combobox(g, textvariable=self.vars["bar_pos"], state="readonly",
                           values=["bottom", "top", "left", "right", "none"])
        row(g, "色带位置", cbb, 6)
        cbb.bind("<<ComboboxSelected>>", lambda e: self._push("bar_pos", self.vars["bar_pos"].get()))

        self.vars["bar_thickness"] = tk.DoubleVar(value=4.0)
        sc = ttk.Scale(g, from_=0.0, to=8.0, variable=self.vars["bar_thickness"], command=self._lazy)
        row(g, "色带厚度", sc, 7)

        self.vars["show_band"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text="显示机动色带", variable=self.vars["show_band"],
                        command=lambda: self._push("show_band", bool(self.vars["show_band"].get()))
                        ).grid(row=8, column=0, columnspan=2, sticky="w")
        self.vars["gloss"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(g, text="高光斜面（Vassal 质感）", variable=self.vars["gloss"],
                        command=lambda: self._push("gloss", bool(self.vars["gloss"].get()))
                        ).grid(row=9, column=0, columnspan=2, sticky="w")

        # --- 底部按钮
        g = ttk.Frame(p)
        g.pack(fill="x", pady=8)
        ttk.Button(g, text="重置为默认", command=self.reset).pack(fill="x")
        ttk.Label(p, text="提示：改动即时生效；导出的 PNG 可直接黏进 Vassal 模块的 images 目录。",
                  foreground="#555", wraplength=400).pack(fill="x", pady=(6, 0))

    def _entry(self, parent, key):
        e = ttk.Entry(parent, textvariable=self.vars[key])
        e.bind("<KeyRelease>", lambda ev, k=key: self._push(k, self.vars[k].get()))
        return e

    # ------------------------------------------------------------ 数据同步
    def _sync_to_widgets(self):
        ct = self.ct
        for f in fields(ct):
            key = f.name
            if key in self.vars:
                try:
                    self.vars[key].set(getattr(ct, key))
                except tk.TclError:
                    pass
        self.vars["kind"].set(f"{ct.kind} · {dict(R.KINDS).get(ct.kind, ct.kind)}")
        self.vars["symbol"].set(f"{ct.symbol} · {dict(R.SYMBOLS).get(ct.symbol, ct.symbol)}")
        self.vars["size_label"].set(
            f"{ct.size_label} · {dict(R.SIZE_PRESETS).get(ct.size_label, ct.size_label)}"
            if ct.size_label else "")
        self.vars["bar_pos"].set(ct.bar_pos)
        self.vars["bar_thickness"].set(ct.bar_thickness)
        self.sw_bg.configure(bg=hexed(ct.bg))
        self.sw_band.configure(bg=hexed(ct.band))
        self.sw_bar.configure(bg=hexed(ct.bar_color))

    def _push(self, key, value):
        setattr(self.ct, key, value)
        self._lazy()

    def _apply_choice(self, key, table):
        raw = self.vars[key].get().split(" · ")[0]
        setattr(self.ct, key, raw)
        self._lazy()

    def _apply_bg_preset(self):
        name = self.vars["bg_preset"].get()
        bg, band = R.BG_PRESETS[name]
        self.ct.bg, self.ct.band = bg, band
        self.sw_bg.configure(bg=bg)
        self.sw_band.configure(bg=band)
        self._lazy()

    def _apply_band_preset(self):
        col = R.MOVE_CLASS[self.vars["band_preset"].get()]
        if col == "none":
            self.ct.show_band = False
        else:
            self.ct.band = col
            self.ct.show_band = True
        self.sw_band.configure(bg=self.ct.band)
        self._lazy()

    def _set_bar_color(self, hx):
        self.ct.bar_color = hx
        self.sw_bar.configure(bg=hx)
        if self.ct.bar_pos == "none":
            self.ct.bar_pos = "bottom"
            self.vars["bar_pos"].set("bottom")
        self._lazy()

    def _pick(self, key):
        cur = hexed(getattr(self.ct, key))
        rgb, hx = colorchooser.askcolor(color=cur, title="选择颜色")
        if hx:
            setattr(self.ct, key, hx)
            {"bg": self.sw_bg, "band": self.sw_band, "bar_color": self.sw_bar}[key].configure(bg=hx)
            self._lazy()

    def reset(self):
        self.ct = R.Counter()
        self._sync_to_widgets()
        self.refresh()

    # ------------------------------------------------------------ 刷新
    def _lazy(self, *_):
        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(120, self.refresh)

    def browse(self, step: int):
        if not getattr(self, "gallery", None):
            self.load_gallery(verbose=False)
        if not getattr(self, "gallery", None):
            return
        self.gal_idx = (getattr(self, "gal_idx", 0) + step) % len(self.gallery)
        self.ct = self.gallery[self.gal_idx].copy()
        self._sync_to_widgets()
        self.refresh()

    def load_gallery(self, verbose=True):
        path = os.path.join(RES, "samples", "units.json")
        if not os.path.exists(path):
            path = filedialog.askopenfilename(initialdir=OUTDIR, filetypes=[("JSON", "*.json")])
        if not path or not os.path.exists(path):
            return
        try:
            self.gallery = R.load_specs(path)
            self.gal_idx = 0
            self.ct = self.gallery[0].copy()
            self._sync_to_widgets()
            self.refresh()
            if verbose:
                messagebox.showinfo("示例库", f"已载入 {len(self.gallery)} 枚示例算子，可用「上一枚/下一枚」翻看。")
        except Exception as e:
            messagebox.showerror("载入失败", str(e))

    def refresh(self):
        try:
            z = int(self.zoom.get())
        except Exception:
            z = 4
        size = 75 * max(1, z)
        front = R.render(self.ct, size)
        back = R.render(self.ct.copy(side="back",
                                     ar_style="ghost" if self.ct.ar_style == "box" else self.ct.ar_style),
                        size)
        self._imgrefs = [ImageTk.PhotoImage(front), ImageTk.PhotoImage(back)]
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 700
        gap = 24
        total = size * 2 + gap
        x0 = max(10, (w - total) // 2)
        y0 = max(10, (h - size) // 2 - 10)
        self.canvas.create_image(x0, y0, image=self._imgrefs[0], anchor="nw")
        self.canvas.create_image(x0 + size + gap, y0, image=self._imgrefs[1], anchor="nw")
        self.canvas.create_text(x0 + size / 2, y0 + size + 14, text="正面 (Deployed)",
                                fill="#cfcfcf", font=("Segoe UI", 9))
        self.canvas.create_text(x0 + size * 1.5 + gap, y0 + size + 14, text="背面 (Unprepared)",
                                fill="#cfcfcf", font=("Segoe UI", 9))
        # 1:1 小样
        one = ImageTk.PhotoImage(R.render(self.ct, 75))
        self._imgrefs.append(one)
        self.canvas.create_image(x0, y0 - 90, image=one, anchor="nw")
        self.canvas.create_text(x0 + 44, y0 - 78, text="← 1:1 实际大小", fill="#8f8f8f",
                                font=("Segoe UI", 8))

    # ------------------------------------------------------------ 导出
    def _name(self, suffix=""):
        base = (self.ct.name or self.ct.unit_id or self.ct.formation_id or "counter").replace("/", "-")
        return f"{base}{suffix}.png"

    def export(self, side):
        os.makedirs(OUTDIR, exist_ok=True)
        path = filedialog.asksaveasfilename(
            initialdir=OUTDIR, initialfile=self._name("" if side == "front" else "-back"),
            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        ct = self.ct.copy(side=side,
                          ar_style="ghost" if side == "back" and self.ct.ar_style == "box" else self.ct.ar_style)
        R.render(ct, int(self.out_size.get())).save(path)
        messagebox.showinfo("已导出", path)

    def export_pair(self):
        os.makedirs(OUTDIR, exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, initialfile=self._name("-pair"),
                                            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        R.render_pair(self.ct, int(self.out_size.get())).save(path)
        messagebox.showinfo("已导出", path)

    def export_sheet(self):
        os.makedirs(OUTDIR, exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, initialfile="sheet.png",
                                            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        R.contact_sheet([self.ct, self.ct.copy(ar_style="ghost")], cols=2,
                        size=int(self.out_size.get()) * 2).save(path)
        messagebox.showinfo("已导出", path)

    def save_json(self):
        os.makedirs(OUTDIR, exist_ok=True)
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, initialfile="counter.json",
                                            defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        R.save_specs([self.ct], path)
        messagebox.showinfo("已保存", path)

    def load_json(self):
        path = filedialog.askopenfilename(initialdir=OUTDIR, filetypes=[("JSON", "*.json")])
        if not path:
            return
        specs = R.load_specs(path)
        if specs:
            self.ct = specs[0]
            self._sync_to_widgets()
            self.refresh()

    def batch(self):
        path = filedialog.askopenfilename(initialdir=OUTDIR, filetypes=[("JSON", "*.json")])
        if not path:
            return
        specs = R.load_specs(path)
        out = filedialog.askdirectory(initialdir=OUTDIR, title="选择输出文件夹")
        if not out:
            return
        size = int(self.out_size.get())
        n = 0
        for i, ct in enumerate(specs):
            name = (ct.name or ct.unit_id or ct.formation_id or f"c{i:03d}").replace("/", "-")
            R.render(ct, size).save(os.path.join(out, f"{i:03d}_{name}_F.png"))
            R.render(ct.copy(side="back",
                             ar_style="ghost" if ct.ar_style == "box" else ct.ar_style),
                     size).save(os.path.join(out, f"{i:03d}_{name}_B.png"))
            n += 2
        messagebox.showinfo("批量导出", f"共导出 {n} 张 PNG → {out}")


def main():
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.25)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
