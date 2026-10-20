# -*- coding: utf-8 -*-
"""HQ 双面样张。

- `samples/hq_sides.png`   ：只用本项目的渲染器出正常面 / 已激活面，可随仓库发布。
- `out/hq_compare.png`     ：再并排官方扫描件做逐格对照。官方素材是商业美术资源，
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
EG = os.path.join(BCSV, "HQ Eg")

HQ = R.Counter(kind="hq", command_radius="10", formation_id="30 Inf", size_label="XX",
               activation="4", arty="4", ma="8", ar="4",
               symbol="inf", symbol_mode="glyph", bg="#7E9B3D", bar_color="#6E8B3D")

S = 8
CELL = 75 * S
PAD = 14


def compose(labels, imgs, path, mark_from=None):
    """把若干等大格子横向排成一张图；mark_from 之后（含）的格子顶部画红杠，标出「非本项目渲染」。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet = Image.new("RGBA", (len(imgs) * CELL + (len(imgs) + 1) * PAD, CELL + 62),
                      (26, 26, 30, 255))
    d = ImageDraw.Draw(sheet)
    for i, img in enumerate(imgs):
        x = PAD + i * (CELL + PAD)
        sheet.alpha_composite(img, (x, 40))
        d.text((x + CELL / 2, 14), labels[i], fill="#e2e2e2", anchor="ma",
               font=R.font("narrow_b", 20))
        if mark_from is not None and i >= mark_from:
            d.line([(x, 40), (x + CELL, 40)], fill=(255, 90, 90), width=2)
    sheet.convert("RGB").save(path)
    print("ok", path)


gen = [("gen front", R.render(HQ.copy(side="front"), 75).resize((CELL, CELL), Image.NEAREST)),
       ("gen back", R.render(HQ.copy(side="back"), 75).resize((CELL, CELL), Image.NEAREST))]
compose([l for l, _ in gen], [i for _, i in gen], os.path.join(SAMPLES, "hq_sides.png"))

extra_l, extra_i = [], []
for fn, label in (("HQ-正常.png", "example front"), ("HQ-已激活.png", "example back")):
    p = os.path.join(EG, fn)
    if not os.path.exists(p):
        print("跳过官方对照：缺", p)
        print("  （官方扫描件是商业素材，不随仓库分发；需要对照时用 BCSV_ROOT 指向素材根目录）")
        extra_l = []
        break
    extra_l.append(label)
    extra_i.append(Image.open(p).convert("RGBA").resize((CELL, CELL), Image.NEAREST))

if extra_l:
    compose([l for l, _ in gen] + extra_l, [i for _, i in gen] + extra_i,
            os.path.join(OUT, "hq_compare.png"), mark_from=len(gen))
