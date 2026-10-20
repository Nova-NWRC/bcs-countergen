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
        root.geometry("1220x880")
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
        ttk.Button(bar2, text="军队编辑器…", command=self.open_army).pack(side="left", padx=(10, 4))

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

        # ---- 小工具 ----------------------------------------------------
        def group(title, hint=None):
            f = ttk.LabelFrame(p, text=title, padding=(8, 4))
            f.pack(fill="x", pady=(4, 2))
            if hint:
                ttk.Label(f, text=hint, foreground="#777", wraplength=390,
                          justify="left").grid(row=90, column=0, columnspan=4,
                                               sticky="w", pady=(3, 0))
            return f

        def row(f, label, widget, r, col=0):
            ttk.Label(f, text=label, width=9, anchor="e").grid(
                row=r, column=col * 2, sticky="e", padx=(0, 4), pady=1)
            widget.grid(row=r, column=col * 2 + 1, sticky="we", pady=1)
            f.columnconfigure(col * 2 + 1, weight=1)

        def row2(f, r, l1, w1, l2, w2):
            row(f, l1, w1, r, 0)
            row(f, l2, w2, r, 1)

        def chk(f, key, text, r, col=0, span=2):
            self.vars[key] = tk.BooleanVar()
            ttk.Checkbutton(f, text=text, variable=self.vars[key],
                            command=lambda k=key: self._push(k, bool(self.vars[k].get()))
                            ).grid(row=r, column=col, columnspan=span, sticky="w", pady=1)

        def combo(f, key, values, label, r, col=0):
            self.vars[key] = tk.StringVar()
            w = ttk.Combobox(f, textvariable=self.vars[key], state="readonly", values=values)
            row(f, label, w, r, col)
            w.bind("<<ComboboxSelected>>",
                   lambda e, k=key: self._push(k, self.vars[k].get()))
            return w

        # ---- ① 基本 ----------------------------------------------------
        g = group("① 基本：类型 · 符号")
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

        row2(g, 2, "符号画法", combo(g, "symbol_mode", ["letter", "glyph"], "", 2, 1),
             "字母代号", self._entry(g, "symbol_letters"))
        row(g, "符号文字", self._entry(g, "symbol_text"), 3)

        # ---- ② 番号 ----------------------------------------------------
        g = group("② 番号 · 编制 · 规模")
        row2(g, 0, "单位番号", self._entry(g, "unit_id"),
             "编制 ID", self._entry(g, "formation_id"))

        self.vars["size_label"] = tk.StringVar()
        cb_size = ttk.Combobox(g, textvariable=self.vars["size_label"],
                               values=[f"{k} · {n}" for k, n in R.SIZE_PRESETS])
        row2(g, 1, "单位规模", cb_size, "大字名/KG", self._entry(g, "name"))
        cb_size.bind("<<ComboboxSelected>>",
                     lambda e: self._push("size_label", self.vars["size_label"].get().split(" · ")[0]))
        cb_size.bind("<KeyRelease>", lambda e: self._push("size_label", self.vars["size_label"].get()))

        # ---- ③ 战斗值（正面）-------------------------------------------
        g = group("③ 战斗值 · 正面", "数值与它的「类型」同行；类型决定数字的底色与描边色。")
        row2(g, 0, "顶部小框值", self._entry(g, "ar"),
             "AR 样式", combo(g, "ar_style", ["box", "disc", "ghost", "none"], "", 0, 1))
        row2(g, 1, "装甲值 AV", self._entry(g, "av"),
             "类型", combo(g, "av_class", ["red", "limited", "standoff", "light"], "", 1, 1))
        row2(g, 2, "机动力 MA", self._entry(g, "ma"),
             "类型", combo(g, "move_class", ["leg", "truck", "tac"], "", 2, 1))
        row2(g, 3, "素质值", self._entry(g, "quality"),
             "射程", self._entry(g, "rng"))
        row2(g, 4, "射程第二行", self._entry(g, "rng2"),
             "中轴样式", combo(g, "range_style", ["plain", "chip"], "", 4, 1))
        row(g, "Steps", self._entry(g, "steps"), 5)
        chk(g, "assault", "突击箭头", 6, 0)
        chk(g, "hard", "Hard 黄框", 6, 2)
        chk(g, "breakthrough", "突破小三角", 7, 0, span=4)
        chk(g, "no_rebuild", "不可补员 / 不可重建（素质值加黄圈）", 8, 0, span=4)

        # ---- ④ 移动面覆写（背面）---------------------------------------
        g = group("④ 移动面覆写 · 背面",
                  "留空 = 沿用正面；填 - = 这一面不画该项；填值 = 覆盖正面。")
        row2(g, 0, "装甲值", self._entry(g, "av_move"),
             "射程", self._entry(g, "rng_move"))
        row2(g, 1, "素质值", self._entry(g, "quality_move"),
             "机动力", self._entry(g, "ma_move"))
        row2(g, 2, "射程第二行", self._entry(g, "rng2_move"),
             "顶部小框值", self._entry(g, "ar_move"))
        row(g, "移动力类型", combo(g, "move_class_move", ["", "leg", "truck", "tac"], "", 3), 3)
        row(g, "反面类型", combo(g, "kind_move", [""] + [k for k, _ in R.KINDS], "", 4), 4)
        chk(g, "back_ghost", "移动面 AR 虚化（灰字）", 5, 0, span=4)

        # ---- ⑤ HQ · 支援 ----------------------------------------------
        g = group("⑤ 指挥部 · 支援单位", "只有对应类型的算子会用到这些字段。")
        row2(g, 0, "指挥半径", self._entry(g, "command_radius"),
             "激活骰点", self._entry(g, "activation"))
        row2(g, 1, "炮兵点数", self._entry(g, "arty"),
             "Support 文字", self._entry(g, "support_label"))
        chk(g, "hq_box_tint", "HQ 兵牌底色跟随编制色带", 2, 0, span=4)
        chk(g, "support_values", "支援单位叠加数值", 3, 0, span=4)

        # ---- ⑥ 配色 · 色带 --------------------------------------------
        g = group("⑥ 配色 · 色带")
        self.vars["bg_preset"] = tk.StringVar()
        cbp = ttk.Combobox(g, textvariable=self.vars["bg_preset"], state="readonly",
                           values=list(R.BG_PRESETS.keys()))
        row(g, "底色预设", cbp, 0)
        cbp.bind("<<ComboboxSelected>>", lambda e: self._apply_bg_preset())

        self.sw_bg = tk.Button(g, text="  底色  ", bg="#A3BA68", command=lambda: self._pick("bg"))
        self.sw_band = tk.Button(g, text="  色带  ", bg="#E8C10C", command=lambda: self._pick("band"))
        self.sw_bar = tk.Button(g, text=" 编制色带 ", bg="#C0392B", command=lambda: self._pick("bar_color"))
        row2(g, 1, "底色", self.sw_bg, "机动色带", self.sw_band)

        self.vars["band_preset"] = tk.StringVar()
        cbm = ttk.Combobox(g, textvariable=self.vars["band_preset"], state="readonly",
                           values=list(R.MOVE_CLASS.keys()))
        row2(g, 2, "机动等级", cbm, "编制色带", self.sw_bar)
        cbm.bind("<<ComboboxSelected>>", lambda e: self._apply_band_preset())

        sw = ttk.Frame(g)
        sw.grid(row=3, column=0, columnspan=4, sticky="we", pady=2)
        for i, (_nm, _hx) in enumerate(R.FORMATION_COLORS.items()):
            tk.Button(sw, width=2, bg=_hx, relief="flat", bd=1,
                      command=lambda c=_hx: self._set_bar_color(c)
                      ).grid(row=i // 6, column=i % 6, padx=1, pady=1, sticky="we")
            sw.columnconfigure(i % 6, weight=1)

        self.vars["bar_thickness"] = tk.DoubleVar(value=4.0)
        row2(g, 4, "色带位置", combo(g, "bar_pos", ["bottom", "top", "left", "right", "none"], "", 5),
             "色带厚度", ttk.Scale(g, from_=0.0, to=8.0,
                                   variable=self.vars["bar_thickness"], command=self._lazy))
        chk(g, "show_band", "显示机动色带", 5, 0)
        chk(g, "gloss", "高光斜面", 5, 2)

        # ---- 底部按钮 --------------------------------------------------
        foot = ttk.Frame(p)
        foot.pack(fill="x", pady=8)
        ttk.Button(foot, text="重置为默认", command=self.reset).pack(fill="x")
        ttk.Button(foot, text="按当前编制导出编制卡", command=self.export_chart).pack(
            fill="x", pady=(4, 0))
        ttk.Label(p, text="提示：改动即时生效；左侧预览同时显示正面 / 背面 / 1:1 小样。",
                  foreground="#555", wraplength=400).pack(fill="x", pady=(6, 0))

    def _entry(self, parent, key):
        if key not in self.vars:
            self.vars[key] = tk.StringVar()
        e = ttk.Entry(parent, textvariable=self.vars[key])
        e.bind("<KeyRelease>", lambda ev, k=key: self._push(k, self.vars[k].get()))
        return e

    def open_army(self):
        """另开一个进程启动军队编辑器（表格批量编辑）。"""
        import subprocess
        cmd = ([sys.executable, "--army"] if FROZEN
               else [sys.executable, os.path.join(HERE, "bcs_army.py")])
        try:
            subprocess.Popen(cmd)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

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

    def export_chart(self):
        """按当前算子的编制信息（编制名/底色/色带/兵种符号）导出编制卡。"""
        import bcs_chart
        ct = self.ct
        name = ct.formation_id or "formation"
        symbol = ct.symbol if ct.symbol in R.SYMBOLS else "inf"
        band = ct.bar_color if ct.bar_color not in ("", "none") else ct.band
        chart = bcs_chart.render_chart(name=name, symbol=symbol, bg=ct.bg, band=band)
        base = (name or "chart").replace("/", "-")
        path = filedialog.asksaveasfilename(initialdir=OUTDIR, defaultextension=".png",
                                            filetypes=[("PNG", "*.png")],
                                            initialfile=f"{base}__chart.png")
        if path:
            chart.save(path)
            messagebox.showinfo("完成", f"编制卡已写出\n{path}")

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
