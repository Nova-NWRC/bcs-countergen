# -*- coding: utf-8 -*-
"""「不可补员 / 不可重建」黄圈样张。

- `samples/no_rebuild.png`      ：只用本项目的渲染器出「带黄圈 / 不带」两枚，可随仓库发布。
- `out/no_rebuild_compare.png`  ：再并排官方 BC 算子对照。官方素材是商业美术资源，
  只在本机存在，输出落在 out/（gitignored），不进仓库。

素材根目录默认取本仓库的上一级（即 BCSV/），可用环境变量 BCSV_ROOT 覆盖。
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcs_render as R  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")
OUT = os.path.join(HERE, "out")
BCSV = os.environ.get("BCSV_ROOT") or os.path.dirname(HERE)
ROOT = os.path.join(BCSV, "Counter", "BC")

base = dict(kind="av", unit_id="1/33", formation_id="10 GD", size_label="II", ar="5",
            av="4", quality="4", rng="2", ma="12", move_class="truck",
            symbol="inf", bg="#A3BA68", bar_color="#6E8B3D")
on = R.Counter(**base, no_rebuild=True)
off = R.Counter(**base, no_rebuild=False)

S = 7
CELL = 75 * S
GAP = 12


def compose(tiles, path, mark_from=None):
    """横向拼格；mark_from 之后（含）的格子顶部画红杠，标出「非本项目渲染」。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet = Image.new("RGBA", (len(tiles) * (CELL + GAP) + GAP, CELL + 34), (24, 24, 28, 255))
    d = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(tiles):
        x = GAP + i * (CELL + GAP)
        sheet.alpha_composite(img.resize((CELL, CELL), Image.NEAREST), (x, 28))
        d.text((x + CELL / 2, 8), label, fill="#e2e2e2", anchor="ma", font=R.font("narrow_b", 15))
        if mark_from is not None and i >= mark_from:
            d.line([(x, 28), (x + CELL, 28)], fill=(255, 90, 90), width=2)
    sheet.convert("RGB").save(path)
    print("ok", path)


gen = [("gen · no rebuild", R.render(on, 75)), ("gen · plain", R.render(off, 75))]
compose(gen, os.path.join(SAMPLES, "no_rebuild.png"))

extra = []
for fn, label in (("BBC-CS-1-B_78.png", "official · no rebuild"), ("BBC-CS-1-B_1.png", "official · plain")):
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        print("跳过官方对照：缺", p)
        print("  （官方扫描件是商业素材，不随仓库分发；需要对照时用 BCSV_ROOT 指向素材根目录）")
        extra = []
        break
    extra.append((label, Image.open(p).convert("RGBA")))

if extra:
    compose(gen + extra, os.path.join(OUT, "no_rebuild_compare.png"), mark_from=len(gen))
