# -*- coding: utf-8 -*-
"""
BCS 算子生成器 —— 命令行 / 批量工具

用法：
  python bcs_cli.py --demo                      # 生成 samples/ 样张
  python bcs_cli.py --spec units.json --out out --size 75 --pair
  python bcs_cli.py --sheet units.json --out out/sheet.png --cols 6 --size 150
  python bcs_cli.py --template > units.json     # 输出一份可编辑模板
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
import bcs_render as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = [
    {"kind": "av", "unit_id": "I/33", "formation_id": "10 GD", "size_label": "II", "ar": "5",
     "av": "4", "quality": "4", "rng": "2", "rng2": "", "ma": "16", "hard": True,
     "symbol": "armor", "bg": "#A3BA68", "band": "#C0392B", "bar_color": "#4A5A22"},
    {"kind": "inf", "unit_id": "II/505", "formation_id": "10 GD", "size_label": "II", "ar": "5",
     "quality": "3", "rng": "", "ma": "4", "hard": False, "symbol": "inf", "assault": True,
     "bg": "#F2DCB0", "band": "#E8C10C", "bar_color": "#8C4A2F"},
    {"kind": "hq", "formation_id": "KG", "name": "Peiper", "ar": "5", "ma": "8",
     "command_radius": "2", "symbol": "oval", "bg": "#23201E", "band": "#5B8FD6"},
    {"kind": "train", "formation_id": "Pape", "name": "KG", "ma": "12",
     "bg": "#BFC0B6", "band": "#5B8FD6", "bar_color": "#8C4A2F"},
]


def safe(name: str, i: int) -> str:
    base = (name or f"c{i:03d}").replace("/", "-").replace("\\", "-").replace(" ", "_")
    return f"{i:03d}_{base}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="BCS 算子生成器")
    ap.add_argument("--spec", help="算子 JSON（单个对象或列表）")
    ap.add_argument("--out", help="输出目录或 PNG 路径")
    ap.add_argument("--size", type=int, default=75, help="边长像素，默认 75（Vassal 原生）")
    ap.add_argument("--pair", action="store_true", help="同时输出背面")
    ap.add_argument("--sheet", action="store_true", help="输出拼版总览")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--demo", action="store_true", help="生成 samples/ 样张")
    ap.add_argument("--template", action="store_true", help="打印 JSON 模板")
    a = ap.parse_args(argv)

    if a.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return 0

    if a.demo:
        import bcs_demo  # noqa: F401
        print("样张已写入", os.path.join(HERE, "samples"))
        return 0

    if not a.spec:
        ap.print_help()
        return 1
    specs = R.load_specs(a.spec)
    out = a.out or os.path.join(HERE, "out")
    if a.sheet:
        path = out if out.lower().endswith(".png") else os.path.join(out, "sheet.png")
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        R.contact_sheet(specs, cols=a.cols, size=a.size).save(path)
        print("已写出", path, f"({len(specs)} 枚)")
        return 0

    os.makedirs(out, exist_ok=True)
    for i, ct in enumerate(specs):
        tag = safe(ct.name or ct.unit_id or ct.formation_id, i)
        R.render(ct, a.size).save(os.path.join(out, tag + "_F.png"))
        if a.pair:
            R.render(ct.copy(side="back",
                             ar_style="ghost" if ct.ar_style == "box" else ct.ar_style),
                     a.size).save(os.path.join(out, tag + "_B.png"))
    print(f"已写出 {len(specs)} 枚算子 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
