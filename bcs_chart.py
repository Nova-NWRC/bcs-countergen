"""编制卡（Formation Chart）绘制。

版式取自 BCS 官方编制卡（`BCSV/Formation Charts/*.png`，250×356）：

    ┌───────────────────────────┐   ← 白卡
    │ ┌───────────┬───────────┐ │
    │ │ 师徽标/兵种 │  Fatigue  │ │  第 1 行
    │ │  符号 + 编制 │   Level   │ │
    │ ├───────────┼───────────┤ │
    │ │ Artillery │ Prepared  │ │  第 2 行
    │ │  Points   │  Defense  │ │
    │ ├───────────┴───────────┤ │
    │ │        Support        │ │  第 3 行（整行合并）
    │ │ █████████████████████ │ │  ← 编制色带
    │ └───────────────────────┘ │
    └───────────────────────────┘

格子 106×106 设计单位，比算子（75）略大，支援/标记算子放得下。
"""

from __future__ import annotations

import os
import sys

from PIL import Image

import bcs_render as R

# ---------------------------------------------------------------- 版式常量
CH = dict(
    W=250.0, H=356.0,          # 整张卡（白卡）尺寸，设计单位
    GX0=18.0, GX1=231.0,       # 网格左右边线
    GY0=18.0, GY1=336.0,       # 网格上下边线
    COL=124.5,                 # 中缝竖线
    R1=124.0, R2=230.0,        # 第 1、2 行之间的两条横线
    BAND_Y0=300.0, BAND_Y1=324.0,   # 底部色带（在 Support 格里）
    LINE=2.2,                  # 网格线宽
    LABEL=21.0,                # Fatigue/Artillery/Prepared 字号
    SUPPORT=23.0,              # Support 字号
    NAME=15.0,                 # 编制名字号
    BADGE=58.0,                # 师徽标（兵种符号）边长
    EDGE=1.4,                  # 白卡描边
)

DEFAULT_LABELS = dict(fatigue=("Fatigue", "Level"),
                      arty=("Artillery", "Points"),
                      prep=("Prepared", "Defense"),
                      support="Support")


def _white_card(c: R.Ctx):
    """白卡 + 极浅的右下投影，模仿纸质卡片的观感。"""
    w, h = CH["W"], CH["H"]
    # 投影：三层递减的半透明描边，做出柔和边缘
    for i, alpha in enumerate((22, 34, 48)):
        off = 1.2 + i * 1.2
        c.rect((off, off, w - 1.0 + off, h - 1.0 + off),
               fill=None, outline=(0, 0, 0, alpha), width=2.4)
    c.rect((0, 0, w, h), fill="#FFFFFF")
    c.rect((0, 0, w, h), outline="#D8D8D4", width=CH["EDGE"])


def _grid(c: R.Ctx, bg: str):
    """三行两列的格子：先铺底色，再压网格线。"""
    gx0, gx1, gy0, gy1 = CH["GX0"], CH["GX1"], CH["GY0"], CH["GY1"]
    col, r1, r2 = CH["COL"], CH["R1"], CH["R2"]
    lw = CH["LINE"]
    # 底色（整块网格，含 Support 行）
    c.rect((gx0, gy0, gx1, gy1), fill=bg)
    # 外框
    c.rect((gx0, gy0, gx1, gy1), outline="#191919", width=lw)
    # 中缝 + 两条横线（Support 行不再分栏）
    c.line([(col, gy0), (col, r2)], "#191919", lw)
    c.line([(gx0, r1), (gx1, r1)], "#191919", lw)
    c.line([(gx0, r2), (gx1, r2)], "#191919", lw)


def _band(c: R.Ctx, band: str):
    """编制色带：铺在 Support 格的下部，两侧顶到网格边线。"""
    if not band or band == "none":
        return
    c.rect((CH["GX0"], CH["BAND_Y0"], CH["GX1"], CH["BAND_Y1"]), fill=band)


def _badge(c: R.Ctx, symbol: str, ink: str, frame: bool = False):
    """师徽标：用兵种符号代替（画在左上格上部；frame=True 时加方框）。"""
    gx0, col, gy0 = CH["GX0"], CH["COL"], CH["GY0"]
    size = CH["BADGE"]
    cx = (gx0 + col) / 2
    x0 = cx - size / 2
    y0 = gy0 + 8.0
    box = (x0, y0, x0 + size, y0 + size)
    if frame:
        c.rect(box, outline=ink, width=1.6)
        inner = 0.14
    else:
        inner = 0.02
    R.draw_symbol(c, symbol, (x0 + size * inner, y0 + size * inner,
                              x0 + size * (1 - inner), y0 + size * (1 - inner)),
                  ink, 1.6)
    return y0 + size


def _label(c: R.Ctx, box, lines, size: float, ink: str):
    """格内文字：一到两行，整体垂直居中。"""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    lines = [s for s in lines if s]
    n = len(lines)
    step = size * 1.18
    top = cy - step * (n - 1) / 2
    for i, s in enumerate(lines):
        c.text((cx, top + i * step), s, size, ink, fnt="italic", anchor="mm",
               max_w=(x1 - x0) - 12)


def render_chart(name: str, symbol: str = "inf", bg: str = "#BFBDB6",
                 band: str = "#A5121C", ink: str | None = None,
                 size: int = 250, ss: int = 4, labels: dict | None = None,
                 show_labels: bool = True) -> Image.Image:
    """画一张编制卡。

    name   —— 编制名（HQ 兵牌上的那个，如 ``10 GD``）
    symbol —— 师徽标用的兵种符号键（``R.SYMBOLS`` 里的值）
    bg     —— 格子底色（一般取编制的 ``bg``）
    band   —— 编制色带（一般取编制的 ``band``）
    """
    labels = dict(DEFAULT_LABELS, **(labels or {}))
    px = int(round(size * ss))
    u = px / CH["W"]
    hp = int(round(CH["H"] * u))
    img = Image.new("RGBA", (px, hp), (0, 0, 0, 0))
    ink = ink or R.readable_ink(bg)
    c = R.Ctx(img, u, ink)

    _white_card(c)
    _grid(c, bg)
    _band(c, band)

    gx0, gx1, gy0, gy1 = CH["GX0"], CH["GX1"], CH["GY0"], CH["GY1"]
    col, r1, r2 = CH["COL"], CH["R1"], CH["R2"]

    # 左上：徽标 + 编制名
    if symbol and symbol != "none":
        badge_bottom = _badge(c, symbol, ink)
    else:
        badge_bottom = gy0 + 6.0
    if name:
        c.text(((gx0 + col) / 2, (badge_bottom + r1) / 2 + 1.0), name, CH["NAME"], ink,
               fnt="italic_b", anchor="mm", max_w=(col - gx0) - 12)

    if show_labels:
        _label(c, (col, gy0, gx1, r1), labels["fatigue"], CH["LABEL"], ink)
        _label(c, (gx0, r1, col, r2), labels["arty"], CH["LABEL"], ink)
        _label(c, (col, r1, gx1, r2), labels["prep"], CH["LABEL"], ink)
        # Support 文字只占色带以上那一段，视觉上与其他格对齐
        _label(c, (gx0, r2, gx1, CH["BAND_Y0"]), [labels["support"]], CH["SUPPORT"], ink)
    return img.resize((size, int(round(CH["H"] * size / CH["W"]))), Image.LANCZOS)


def chart_from_formation(army: dict, name: str, size: int = 250, ss: int = 4):
    """从军队数据里取编制（底色/色带/符号）画一张卡。"""
    form = (army.get("formations") or {}).get(name) or {}
    band = form.get("bar_color") or form.get("band") or "#A5121C"
    return render_chart(name=name,
                        symbol=form.get("symbol", "inf"),
                        bg=form.get("bg", "#BFBDB6"),
                        band=band, size=size, ss=ss)


def export_charts(army: dict, outdir: str, size: int = 250, ss: int = 4) -> dict:
    """给每个编制各出一张卡，另出一张总览。返回 {name: path} 与文件清单。"""
    import bcs_army as A

    os.makedirs(outdir, exist_ok=True)
    files, imgs, titles = [], [], []
    for name in (army.get("formations") or {}):
        img = chart_from_formation(army, name, size=size, ss=ss)
        path = os.path.join(outdir, A.slug(name) + "__chart.png")
        img.save(path)
        files.append(path)
        imgs.append(img)
        titles.append(name)
    if imgs:
        files.append(_sheet(imgs, titles, os.path.join(outdir, "_charts_sheet.png")))
    return {"count": len(imgs), "files": files}


def _sheet(imgs, titles, path, cols: int = 4, pad: int = 12, bg: str = "#22211F"):
    """编制卡总览拼版。"""
    from PIL import ImageDraw

    w, h = imgs[0].size
    rows = (len(imgs) + cols - 1) // cols
    top = 22
    sheet = Image.new("RGB", (cols * w + pad * (cols + 1),
                              rows * (h + top) + pad * (rows + 1)), R.hx(bg))
    d = ImageDraw.Draw(sheet)
    for i, (im, title) in enumerate(zip(imgs, titles)):
        cx = i % cols
        cy = i // cols
        x = pad + cx * (w + pad)
        y = pad + cy * (h + top + pad)
        sheet.paste(im, (x, y + top), im)
        d.text((x + w / 2, y + top / 2), title, fill=(225, 222, 215), anchor="mm",
               font=R.font("italic", 15))
    sheet.save(path)
    return path


# ---------------------------------------------------------------- 命令行
def main(argv=None) -> int:
    import bcs_army as A

    argv = list(sys.argv[1:] if argv is None else argv)

    def _arg(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    spec = _arg("--spec", A.SPEC if os.path.exists(A.SPEC) else None)
    out = _arg("--out", os.path.join(A.OUTDIR, "charts"))
    size = int(_arg("--size", 250))

    army = A.load_army(spec) if spec else A.empty_army()
    res = export_charts(army, out, size=size)
    print(f"已生成 {res['count']} 张编制卡 / {len(res['files'])} 个文件 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
