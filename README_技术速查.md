# BCS 算子生成器（CounterGen）

> 完整使用说明书见 **[使用指南.md](使用指南.md)**；双击 `启动生成器.bat` 打开图形界面，或直接运行 `dist\BCS算子生成器.exe`（无需安装 Python）。

按 `BCSV/Unit Key.png` 的版式做 BCS 系列兵棋自制算子，槽位坐标取自 `BCSV/Example` 里手工框选的实测位置，底部数值区按“关于中轴对称”的规则排布：番号、编制色带、机动色带、装甲值、机动力、素质值、射程、规模代号、进击箭头、底色全部可改，导出 75×75 PNG 直接喂给 Vassal 模块。

纯 Python + Pillow 绘制（无第三方绘图库、不联网），几何按 75×75 “设计单位”排版，内部 4× 超采样后 LANCZOS 降采样，75px 原尺寸也不糊。

---

## 一、版式标定

### 1. 上/中区（来自 Example 框选实测，75×75 原图坐标）

| 槽位 | 实测位置 | 常量 |
|---|---|---|
| 顶部小方框（兵力/行动值） | (24,5)–(31,15) | `L["AR_BOX"]` |
| 规模代号 + 上方小竖条 | x33–40, y12–17（竖条 y9–12） | `L["SIZE"]` / `SIZE_TICK` |
| 兵种符号框 | (22,16)–(50,37) | `L["SYM_BOX"]` |
| 左竖番号（自下而上） | 列心 x=14.8，垂直居中 y=24.4 | `ID_X` / `ID_Y` |
| 右竖编制（自上而下） | 列心 x=58.6，垂直居中 y=24.4 | `FORM_X` / `FORM_Y` |

左右两列**共用同一字号**：上限 `ID_SIZE = 12.4`，并受 `ID_MAXLEN = 32`（竖排长度）与 `ID_MAXH = 11.8`（字面高度）约束——任一侧字符串过长时两列一起等比缩小（例如 `10 Arm` 会一起降到 10.96），所以两列始终同大，既不会顶出兵牌上沿，也不会小到看不清。校验脚本 `bcs_verify_ids.py` 会量出两列的字面高度、上下端与字号。

### 2. 编制规模标志（北约规则）

`size_label` 按北约 unit-size 符号绘制，只做到旅一级（BCS 中绝大多数战斗单位落在 I~X）：`I/II/III` 画 1~3 根竖杠，`X` 画一个交叉的「叉」，其余关键字（KG/TF/Tm/Grp/(+)/(−)）按文字。GUI 的「单位规模」是下拉框，也可手输。

| 符号 | 含义 | 画法 |
|---|---|---|
| `I` | 连 Company | 1 根竖杠 |
| `II` | 营 Battalion | 2 根竖杠 |
| `III` | 团 Regiment | 3 根竖杠 |
| `X` | 旅 Brigade | 一个「叉」：两条对角交叉（不是单斜杠），半对角长 3.0 → 墨迹高与竖杠一致（7.0 格） |
| `XX` | 师 Division | 两个叉并排（多叉时半对角自动收到 2.5） |
| `XXX` | 军 Corps | 三个叉并排 |
| `KG` / `TF` / `Tm` / `Grp` | 战斗群 / 特遣队 / 小队 / 集群 | 文字（BCS 自有，非北约） |
| `(+)` / `(-)` | 加强 / 缺编 | 文字 |

`python bcs_size_sheet.py` 可生成 `samples/size_nato.png` 全套对照。

### 3. 战斗单位的正/反面（战斗面 / 移动面）

`side="front"` 为战斗面，`side="back"` 为移动面，**默认两者版式完全一致**（不再压暗纱）。切面时做四件事：

| 项 | 规则 |
|---|---|
| AR / 素质值 / 机动力 | 移动面优先取 `ar_move` / `quality_move` / `ma_move`，留空则沿用正面值 |
| 反面类型 | `kind_move` 非空、非 `-` 且不等于正面 `kind` 时，**整枚按目标类型重画**（典型：正面 `av` 装甲、反面 `support` 支援，如 M18 坦歼）；此时版式、色带、数值画法全跟着目标 kind 走 |
| AR 画法 | `back_ghost=True`（默认）时，移动面把 AR 画成浅底灰字的「虚化」样式；**`kind_move` 换类型时不虚化**（虚化只表示「同一枚算子的另一面」） |
| 其他元素 | 番号、编制、符号框、编制色带位置一律不变 |

`render_pair()` / `bcs_cli.py --pair` 现在直接输出"战斗面 + 移动面"两个 PNG，面逻辑全部收进 `render()`，GUI 预览、总览拼版、批量导出走的都是同一套。反面换类型后，这一对就是"两种单位"的两面，`kind_move="-"` 则表示不换。

### 4. 指挥部 HQ（正/反两面）

`kind="hq"`，`side="front"` 为正常面、`side="back"` 为已激活面，坐标取自 `BCSV/HQ Eg` 的框选实测：

| 面 | 元素布局 |
|---|---|
| 正面（正常） | 左上 = 指挥范围 `command_radius`；兵牌正上方 = 规模标志 `size_label`；正中 = 兵牌（`symbol`，内填略深于底色；30 × 21.2 格，长宽比 1.414:1 ≈ A4）；兵牌右侧空间水平居中处 = 炮击点数 `arty`（`HQ_ARTY_F` x=63.0）；兵牌下方 = 番号 `formation_id` |
| 背面（已激活） | 左上 = 指挥范围；其右侧 = 激活骰面 `activation`（1–6，按六面骰点阵绘制）；正中 = 番号（**空心黑轮廓**，压在白带上）；番号正下方 = 炮击点数；炮击点数右侧 = 移动力 `ma`（字号约为炮击值的 1.45 倍（实测 1.47），字重改用 Arial Narrow Bold 更细，中心线严格对齐，见 `HQ_MA_SCALE`） |

炮击点数在原作里底下压着爆炸图案，按要求忽略，只画数字。HQ 番号用 Arial Narrow Bold（避免过粗），激活面番号空心；HQ 上的数字统一为**黑色填充 + 白色描边**（移动力除外，保持主文字色），用较宽的字重（Arial Black），两位数按目标墨迹宽高比 ≈1.05 处理（实测「10」= 15.0×13.3 格，接近正方形），单数字保留字形原比例；HQ 内容整体垂直居中（正面上/下留白 7.8 / 8.5 格，背面 7.8 / 7.4 格），HQ 的编制色带自动收成 4.4 格细条，不挤占版面。所有 HQ 数字与番号都用主文字色 + 反色描边、按墨迹高度归一化，和战斗单位同一套渲染路径。

### 5. 补给车（supply）

照 `BCSV/HQ Eg` 的 `补给车-正常 / 补给车-失常` 实测坐标绘制：正面 = 顶部细白行军箭头 + 中央番号（不画定位黑框）（`formation_id`，可用 `\n` 换行，如 `90 Inf\nDiv`）+ 底部补给车标志（白色横杆 + 两个轮圈）；背面（失常面）= 同正面，并在文字底层叠一枚红色禁止标志（粗圆环 + 斜杠）。常量 `SP_ARROW`/`SP_TRUCK_Y`/`SP_WHEELS`/`SP_WHEEL_R`/`SP_TEXT_H`/`SP_SIGN` 都在 `L` 里，补给车与 HQ 一样用 4.4 格细色带。

### 6. 支援单位（support）

版式与战斗单位完全一致（顶部小框 / 规模 / 符号框 / 左右竖排 / 编制色带），但**没有突击箭头、移动力和素质值**；在原本装甲值·素质·射程·移动力那一片的**底层**铺一个大号半透明 `Support` 字样。

| 字段 | 作用 |
|---|---|
| `support_label` | 底层大字内容，默认 `Support`，可改成别的语言/写法 |
| `support_values` | 默认 `False`（只显示 Support 字样）；置 `True` 时把 `av`（左）与 `rng`（中）叠在字样上，用来复刻带数字的支援算子 |

字样用独立图层 + 统一透明度合成（浅底 34%、深底 42% 的墨色），所以是真·底色字，不会盖住上面的数字。GUI 的「③ 数值」里有「支援单位叠加数值」勾选框。

### 8. 编制（师）色带

战斗单位（`av` / `dual` / `inf` / `hq` / `train`）默认在底色底边画一条 **编制色带**：`bar_pos="bottom"`、`bar_thickness=15`（约算子高度的 1/5，足够醒目）、颜色取 `bar_color`。同一师用同一色，跨师一眼可辨；色带上沿压了一道暗线把色带与底色分开；若色带偏深且压到「射程」那一格，射程数字会自动转白字。标记类（`marker`）不画。GUI 的「④ 配色」里有 12 个 `FORMATION_COLORS` 快选色块（红/橙/黄/橄榄/绿/青/蓝/靛/紫/洋红/棕/灰），点一下即可套用；也可用取色器或改 `bar_pos` 到 `top/left/right`。

### 9. 底部数值区（对称规则）

中轴 `CX = 37.5`，左右大数值到中轴距离 `FLANK = 15.6`；两侧都按**墨迹高度归一化**绘制，统一高度 `VAL_H = 19.0`（设计格）。突击箭头区间 `y=44.6~60.6`（高 16.0、宽 4.2），因此两侧数字比箭头高约 19%，即「略高于箭头」。实现方式是先把数字渲染成紧贴墨迹的位图，再等比缩放到 `VAL_H`、以偶数尺寸贴到整数像素中心——因此两侧的**上沿、下沿、中心线完全一致**，横向中心严格落在 `CX±FLANK` 上，不受字形左右边距与圆头数字 overshoot 影响。

| 情形 | 排布 |
|---|---|
| 有装甲值(AV) | AV 落在 `CX-FLANK`，机动力(MA) 落在 `CX+FLANK`，关于中轴对称且墨迹高度完全相同 |
| 有突击箭头、无 AV | 箭头落在 `CX-FLANK`，MA 落在 `CX+FLANK`，两者关于中轴对称 |
| 同时有箭头与 AV | 箭头位于 AV 左侧（`CX-FLANK-13.6`），AV 与 MA 仍关于中轴对称 |
| 素质值 / 射程 | 都压在中轴上：素质值 `Q_Y=45.4` 在上，射程 `R_Y=57.4` 在下；两格同字号（`SM_H=10.4`），合计 22.4 格，略高于左右大数值的 19.0 格 |

`python bcs_verify_values.py` 量左右大数值的像素包围盒（上沿/下沿/高度/中心），`python bcs_verify_center.py` 量中轴列的字高与总高，`python bcs_verify_ids.py` 量左右番号/编制的字号与上下端；三者都会打印判定并输出带标尺的对照图（`samples/value_symmetry.png`、`center_symmetry.png`、`id_symmetry.png`）。

跑 `python bcs_example_compare.py` 生成 `out/refit_compare.png`（本机素材、不入库）：上排是生成器按同样数据复刻的算子，下排是 Example 原图，逐格对齐检查。

## 二、启动

```powershell
python bcs_gui.py                                        # 图形界面（推荐）
python bcs_cli.py --demo                                 # 重新生成 samples/ 全套样张
python bcs_cli.py --spec samples\units.json --out out --size 75 --pair
python bcs_cli.py --spec samples\units.json --out out\sheet.png --sheet --cols 6 --size 150
python bcs_example_compare.py                            # 与 Example 原图并排校验
python bcs_verify_values.py                              # 量 AV/MA 墨迹高度与对称
python bcs_verify_center.py                              # 量素质值/射程字高与总高
python bcs_verify_ids.py                                 # 量左右番号/编制字号与上下端
python bcs_size_sheet.py                                 # 北约编制规模标志（I~X）
python bcs_support_sheet.py                              # 支援单位样张
python bcs_supply_sheet.py                               # 补给车正常/失常面样张
python bcs_hq_sheet.py                                   # HQ 正反两面样张 + 与 HQ Eg 原图对照
python bcs_sides_sheet.py                                  # 战斗单位战斗面/移动面样张
python bcs_symbols_sheet.py                              # 32 个兵种符号对照表
python bcs_cli.py --template                             # 打印 JSON 模板
```

GUI：左侧正面/背面实时预览（上方还有 1:1 实际大小小样），右侧四组参数（①类型与符号 ②番号·编制·规模 ③数值 ④配色·色带），`◀ 上一枚 / 下一枚 ▶` 浏览 `samples/units.json` 示例库。

## 三、当前默认

- **兵种标志用字母代号**：`symbol_mode="letter"`，按 `SYMBOL_LETTERS` 自动取 `INF / ARM / RCN / ENG / ABN / MTN / STG / JS …`，也可在「字母代号」里手填；切 `glyph` 用图形符号库。
- **默认不画机动色带**：`show_band=False`（CS-3 / LB 系算子本来没有底带）；要画就勾「显示机动色带」并选 TAC/LEG/TRUCK。
- **数值是深红 + 白晕**：`value_ink` 留空时浅/中色底自动取 `#A5121C`+白描边；压在深色机动带上才转白字+黑描边。
- **中轴列直接印数字**：`range_style="plain"`（`chip` 可切白底小牌）。
- 背面 = 加暗纱 + 顶部小框虚化（Unprepared / Move 面）。

## 四、字段全表（JSON）

```json
{
  "kind": "inf",                 "unit_id": "2",        "formation_id": "110/28",
  "size_label": "II",            "name": "",
  "ar": "6", "ar_style": "box",
  "quality": "4", "rng": "", "rng2": "", "range_style": "plain",
  "av": "", "ma": "4",
  "assault": true, "hard": false, "breakthrough": false,
  "steps": "", "command_radius": "", "activation": "", "arty": "",
  "symbol": "inf", "symbol_mode": "letter", "symbol_letters": "", "symbol_text": "",
  "bg": "#7E9B3D", "band": "#E8C10C", "show_band": false,
  "bar_color": "#C0392B", "bar_pos": "bottom", "bar_thickness": 15,
  "ink": "", "value_ink": "", "gloss": true,
  "side": "front", "note": ""
}
```

取值约定：
- `kind`：`av` 装甲 / `dual` 双能力 / `inf` 步兵 / `hq` 指挥部 / `train` 辎重 / `support` 支援单位 / `supply` 补给车 / `marker` 标记
- `ar`：顶部小方框里的数字（兵力/行动值，按作不同用法不同）
- `quality`：素质值，画在中轴上方；`rng`/`rng2`：射程，画在中轴下方
- `av` / `ma`：左右两个大数值，自动关于中轴对称
- `assault`：是否画突击箭头（有 `av` 时箭头自动排到 `av` 左侧）
- `ar_style`：`box` 顶框 / `disc` 下方黄圆牌（DF 样式）/ `ghost` 背面 / `none`
- `symbol_mode`：`letter` 字母代号 / `glyph` 图形符号（32 种，见 `samples/symbols.png`）
- `range_style`：`plain` 直接印数字 / `chip` 白底小牌
- `bar_pos`：`top`/`bottom`/`left`/`right`/`none`；`bar_thickness` 0–15（底边超过 42 格起会被安全截断，不会吃掉符号框）

## 五、塞进 Vassal

1. GUI 里调好后「导出正面 PNG」（背面会自动套 ghost 样式）。
2. 丢进目标模块解包目录的 `images/`，如 `BCSV/BCS Last Blitzkrieg-5_18_0/images/`。
3. 新建：Vassal 编辑器里给 Piece 设 BasicPiece 图像；替换：直接覆盖同名 png（如 `CS-3-F_192.png`）最省事。
4. 尺寸：LB/PLS/VoT/BC/BbF 用 75×75，DF 是 70×70，Arr 是 94×94 —— 导出尺寸下拉里都有。

## 六、扩展

- 加兵种字母：`bcs_render.py` 的 `SYMBOL_LETTERS` 加一行。
- 加图形符号：`draw_symbol()` 里加 `elif k == "xxx":`，再往 `SYMBOLS` 登记。
- 改版式：文件顶部 `L = dict(...)` 是全部几何常量（单位=75 网格），改完跑 `bcs_example_compare.py` 校验。
- 批量整套：写好 JSON 列表 → `bcs_cli.py --spec myarmy.json --out out --pair`。

## 七、已知取舍

- 官方各作的“大数值”含义不统一（有的作把行动值画成顶框，有的画成底部黄圆牌），所以字段按槽位命名（`ar` / `quality` / `av` / `ma`），语义由玩家自己定。
- 图形符号是矢量近似，非像素级复刻官方美术；当前默认字母模式。
- Example 里 `CS-3-F_95` 底色上的白色单位副名（“…Sport”）暂无槽位，可用 `marker` 类型代替，或后续加 `sub_name`。
