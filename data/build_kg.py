"""
数学分析知识图谱构建脚本。

运行：
    python3 data/build_kg.py

产物：
    data/kg.json  ——  供 viewer/ 加载的权威数据
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


RELATION_TYPES = [
    {"key": "PREREQUISITE_OF",      "label": "前置",     "color": "#e07b39"},
    {"key": "USED_IN",              "label": "应用于",   "color": "#3a86ff"},
    {"key": "GENERALIZES",          "label": "推广",     "color": "#8338ec"},
    {"key": "SPECIAL_CASE_OF",      "label": "特例",     "color": "#9d4edd"},
    {"key": "SIMILAR_TO",           "label": "类比",     "color": "#06a77d"},
    {"key": "EASILY_CONFUSED_WITH", "label": "易混淆",   "color": "#d62828"},
    {"key": "RELATED_TO",           "label": "弱相关",   "color": "#888888"},
    {"key": "CONTAINS",             "label": "包含",     "color": "#cccccc"},
]


# ---------------- 节点构造工具 ----------------

NODES: list[dict] = []
NODE_INDEX: dict[str, dict] = {}


def add(
    node_id: str,
    name: str,
    level: int,
    parent_id: str | None,
    summary: str = "",
) -> str:
    if node_id in NODE_INDEX:
        raise ValueError(f"重复节点 id: {node_id}")
    if parent_id is not None and parent_id not in NODE_INDEX:
        raise ValueError(f"节点 {node_id} 的 parent_id={parent_id} 还未注册")
    node = {
        "id": node_id,
        "name": name,
        "level": level,
        "parent_id": parent_id,
        "summary": summary,
    }
    NODES.append(node)
    NODE_INDEX[node_id] = node
    return node_id


# ---------------- 关系构造工具 ----------------

EDGES: list[dict] = []
EDGE_SEEN: set[tuple[str, str, str]] = set()


def link(source: str, target: str, type_key: str, note: str = "") -> None:
    if source not in NODE_INDEX or target not in NODE_INDEX:
        raise ValueError(f"关系引用了不存在的节点: {source} -> {target}")
    if source == target:
        raise ValueError(f"自环关系: {source}")
    key = (source, target, type_key)
    if key in EDGE_SEEN:
        return
    EDGE_SEEN.add(key)
    EDGES.append({"source": source, "target": target, "type": type_key, "note": note})


# ===============================================================
# 根 + 册
# ===============================================================

add("ma", "数学分析", 0, None,
    summary="实数系基础上的极限-连续-微分-积分-级数体系，研究函数在连续/光滑/可测意义下的局部与整体性质。")

# 6 大主题领域（替代原 vol1/vol2 划分，按知识体系而非教学顺序）
add("dom_foundation", "实数与极限", 1, "ma",
    summary="集合、映射、实数完备性、数列与函数极限、连续性——整个数学分析的逻辑底座。")
add("dom_diff_uni",   "单变量微分学", 1, "ma",
    summary="一元函数的导数、微分、中值定理、Taylor 公式与导数应用。")
add("dom_int_uni",    "单变量积分学", 1, "ma",
    summary="不定积分、定积分、广义积分及其几何/物理应用。")
add("dom_diff_multi", "多变量微分学", 1, "ma",
    summary="多元极限、偏导、全微分、链式法则、隐函数、方向导数、梯度与多元极值。")
add("dom_int_multi",  "多变量积分学", 1, "ma",
    summary="重积分、曲线积分、曲面积分及三大整合定理（Green / Gauss / Stokes）。")
add("dom_series_ode", "级数与微分方程", 1, "ma",
    summary="数项级数、函数项级数、幂级数、Fourier 级数与常微分方程理论。")


# ===============================================================
# 上册 —— 12 章
# ===============================================================

# ---------- 第 1 章 集合与映射 ----------
add("ch1", "集合与映射", 2, "dom_foundation",
    summary="集合论语言、映射/函数、可数性、确界，是后续所有讨论的逻辑底座。")

add("sec1_1", "集合", 3, "ch1", summary="集合的语言与运算。")
add("kp1_1_1", "集合的定义", 4, "sec1_1", summary="确定的、互异的对象之全体。")
add("kp1_1_2", "集合的运算", 4, "sec1_1", summary="并、交、差、补、对称差及 De Morgan 律。")
add("kp1_1_3", "集合的包含关系", 4, "sec1_1", summary="子集、真子集、相等。")

add("sec1_2", "映射", 3, "ch1", summary="集合之间的对应法则。")
add("kp1_2_1", "映射的定义", 4, "sec1_2", summary="A 中每个元素对应 B 中唯一元素的法则。")
add("kp1_2_2", "映射的分类", 4, "sec1_2", summary="单射、满射、双射。")
add("kp1_2_3", "复合映射", 4, "sec1_2", summary="g∘f 的定义与可结合性。")
add("kp1_2_4", "逆映射", 4, "sec1_2", summary="双射才可逆。")

add("sec1_3", "函数", 3, "ch1", summary="特殊映射：定义域为实数集。")
add("kp1_3_1", "函数的定义", 4, "sec1_3", summary="实变量到实数的映射。")
add("kp1_3_2", "函数的表示方法", 4, "sec1_3", summary="解析式、表格、图像、分段。")
add("kp1_3_3", "函数的四则运算", 4, "sec1_3", summary="加减乘除及定义域交集。")
add("kp1_3_4", "函数的复合", 4, "sec1_3", summary="内外函数定义域匹配。")
add("kp1_3_5", "函数的基本特征", 4, "sec1_3", summary="有界、单调、奇偶、周期。")
add("kp1_3_6", "反函数", 4, "sec1_3", summary="单调函数必有反函数。")
add("kp1_3_7", "初等函数", 4, "sec1_3", summary="幂、指、对、三角、反三角及其有限次复合。")
add("kp1_3_8", "分段函数", 4, "sec1_3", summary="不同子区间用不同表达式。")
add("kp1_3_9", "隐函数与参数方程", 4, "sec1_3", summary="F(x,y)=0 或 (x(t),y(t)) 形式。")

add("sec1_4", "集合的势与可数集", 3, "ch1", summary="基数比较与可数性。")
add("kp1_4_1", "等势", 4, "sec1_4", summary="A 与 B 之间存在双射。")
add("kp1_4_2", "可数集与不可数集", 4, "sec1_4", summary="有理数可数，实数不可数。")
add("kp1_4_3", "势的常识", 4, "sec1_4", summary="可数并、有限积仍可数等。")
add("kp1_4_4", "对角线方法", 4, "sec1_4", summary="Cantor 证明实数不可数的核心技巧。")

add("sec1_5", "确界存在定理", 3, "ch1", summary="实数系的连续性公理。")
add("kp1_5_1", "集合的界", 4, "sec1_5", summary="上界、下界、有界。")
add("kp1_5_2", "确界的定义", 4, "sec1_5", summary="最小上界、最大下界（sup / inf）。")
add("kp1_5_3", "确界存在定理", 4, "sec1_5", summary="非空有上界集必有上确界。")

add("sec1_6", "极坐标与不等式", 3, "ch1", summary="计算与估计的常备工具。")
add("kp1_6_1", "极坐标的概念", 4, "sec1_6", summary="(ρ, θ) 表示点位置。")
add("kp1_6_2", "极坐标与直角坐标的关系", 4, "sec1_6", summary="x=ρcosθ, y=ρsinθ。")
add("kp1_6_3", "常用的不等式", 4, "sec1_6", summary="Cauchy-Schwarz、Bernoulli、均值不等式等。")
add("kp1_6_4", "三角不等式", 4, "sec1_6", summary="|a+b| ≤ |a|+|b|。")


# ---------- 第 2 章 数列极限 ----------
add("ch2", "数列极限", 2, "dom_foundation",
    summary="极限是数学分析的灵魂，本章用 ε-N 语言精确刻画无限趋近。")

add("sec2_1", "数列极限的定义", 3, "ch2", summary="ε-N 语言。")
add("kp2_1_1", "数列的定义", 4, "sec2_1", summary="正整数集到实数的函数。")
add("kp2_1_2", "数列极限的ε-N定义", 4, "sec2_1", summary="∀ε>0, ∃N, n>N 时 |aₙ-A|<ε。")
add("kp2_1_3", "数列极限的几何解释", 4, "sec2_1", summary="ε 邻域内最多有限项在外。")
add("kp2_1_4", "数列发散", 4, "sec2_1", summary="不收敛即发散。")

add("sec2_2", "用定义证明数列极限", 3, "ch2", summary="ε-N 应用范例。")
add("kp2_2_1", "用定义证明数列极限举例", 4, "sec2_2", summary="估计 |aₙ-A| 找 N。")
add("kp2_2_2", "放大法", 4, "sec2_2", summary="把表达式放大到容易控制的形式。")

add("sec2_3", "收敛数列的性质", 3, "ch2", summary="收敛带来的基本结构。")
add("kp2_3_1", "收敛数列的唯一性", 4, "sec2_3", summary="极限若存在必唯一。")
add("kp2_3_2", "收敛数列的有界性", 4, "sec2_3", summary="收敛必有界，反之不然。")
add("kp2_3_3", "数列极限的保序性", 4, "sec2_3", summary="aₙ≤bₙ 极限保持。")
add("kp2_3_4", "数列极限的保号性", 4, "sec2_3", summary="极限正则尾部正。")
add("kp2_3_5", "数列极限与子列极限的一致性", 4, "sec2_3", summary="收敛数列任意子列同极限。")

add("sec2_4", "数列极限的运算", 3, "ch2", summary="代数与不等式技巧。")
add("kp2_4_1", "数列极限的四则运算", 4, "sec2_4", summary="加减乘除极限可分配。")
add("kp2_4_2", "数列极限的夹逼定理", 4, "sec2_4", summary="两边夹则中间收敛同极限。")

add("sec2_5", "数列的无穷小与无穷大", 3, "ch2", summary="趋于 0 与发散到 ∞ 的对偶。")
add("kp2_5_1", "无穷小数列", 4, "sec2_5", summary="极限为 0 的数列。")
add("kp2_5_2", "无穷小的性质", 4, "sec2_5", summary="有限个无穷小之和仍无穷小。")
add("kp2_5_3", "无穷大数列", 4, "sec2_5", summary="|aₙ|→∞。")
add("kp2_5_4", "无穷大的性质", 4, "sec2_5", summary="无穷大的倒数为无穷小。")
add("kp2_5_5", "Stolz定理", 4, "sec2_5", summary="数列形式的洛必达，处理 ∞/∞ 与 0/0。")

add("sec2_6", "单调数列的极限及其应用", 3, "ch2", summary="单调 + 有界 = 收敛。")
add("kp2_6_1", "数列极限的单调有界定理", 4, "sec2_6", summary="单调有界数列必收敛。")
add("kp2_6_2", "自然对数底e", 4, "sec2_6", summary="(1+1/n)ⁿ 的极限。")
add("kp2_6_3", "欧拉常数", 4, "sec2_6", summary="γ = lim(Hₙ - ln n)。")

add("sec2_7", "实数系基本定理", 3, "ch2", summary="五大等价定理。")
add("kp2_7_1", "闭区间套定理", 4, "sec2_7", summary="嵌套闭区间公共点存在唯一。")
add("kp2_7_2", "列紧性定理", 4, "sec2_7", summary="有界数列必有收敛子列（Bolzano-Weierstrass）。")
add("kp2_7_3", "柯西基本定理", 4, "sec2_7", summary="柯西列收敛（实数系完备性）。")
add("kp2_7_4", "有限覆盖定理", 4, "sec2_7", summary="闭区间任一开覆盖有有限子覆盖（Heine-Borel）。")
add("kp2_7_5", "定理等价性的讨论", 4, "sec2_7", summary="五大定理两两等价。")
add("kp2_7_6", "确界原理", 4, "sec2_7", summary="非空有上界集必有上确界，等价于完备性。")

add("sec2_8", "上极限与下极限", 3, "ch2", summary="替代不存在极限时的工具。")
add("kp2_8_1", "上极限与下极限的概念", 4, "sec2_8", summary="所有子列极限的上 / 下确界。")
add("kp2_8_2", "上极限与下极限的性质", 4, "sec2_8", summary="liminf ≤ limsup，相等当且仅当收敛。")


# ---------- 第 3 章 函数极限与连续 ----------
add("ch3", "函数极限与连续", 2, "dom_foundation",
    summary="把数列极限思想移植到函数：ε-δ 与连续性。")

add("sec3_1", "函数极限的定义", 3, "ch3", summary="ε-δ 语言。")
add("kp3_1_1", "邻域的定义", 4, "sec3_1", summary="去心邻域与点的邻域。")
add("kp3_1_2", "x→x₀时函数极限的ε-δ定义", 4, "sec3_1", summary="∀ε>0, ∃δ>0, 0<|x-x₀|<δ ⇒ |f(x)-A|<ε。")
add("kp3_1_3", "函数极限的几何意义", 4, "sec3_1", summary="函数值终落入水平 ε 带。")
add("kp3_1_4", "函数的左右极限", 4, "sec3_1", summary="x→x₀⁻ 与 x→x₀⁺。")

add("sec3_2", "函数极限的性质", 3, "ch3", summary="对偶于数列极限性质。")
add("kp3_2_1", "函数极限的唯一性", 4, "sec3_2", summary="若存在必唯一。")
add("kp3_2_2", "函数极限的局部有界性", 4, "sec3_2", summary="邻域内有界。")
add("kp3_2_3", "函数极限的局部保序性", 4, "sec3_2", summary="不等式可在邻域内保持。")
add("kp3_2_4", "函数极限的局部保号性", 4, "sec3_2", summary="正极限带正邻域。")

add("sec3_3", "其他过程的函数极限", 3, "ch3", summary="x→∞、单侧、∞ 极限。")
add("kp3_3_1", "x→∞时函数极限的定义", 4, "sec3_3", summary="∀ε>0, ∃X, |x|>X 时 |f(x)-A|<ε。")
add("kp3_3_2", "所有形式的极限", 4, "sec3_3", summary="x→x₀±、x→±∞ 共 6 种。")
add("kp3_3_3", "x→∞时函数极限的几何意义", 4, "sec3_3", summary="水平渐近线含义。")
add("kp3_3_4", "海涅定理", 4, "sec3_3", summary="函数极限化归为任意子列的数列极限。")

add("sec3_4", "函数极限的运算", 3, "ch3", summary="代数性质与夹逼。")
add("kp3_4_1", "函数极限的四则运算", 4, "sec3_4", summary="与数列形式平行。")
add("kp3_4_2", "函数极限的夹逼定理", 4, "sec3_4", summary="处理三角函数等。")
add("kp3_4_3", "复合函数的极限", 4, "sec3_4", summary="内函数极限存在且外函数连续可换序。")
add("kp3_4_4", "两个重要极限", 4, "sec3_4", summary="lim sin x / x = 1, lim (1+1/x)^x = e。")

add("sec3_5", "无穷小与无穷大", 3, "ch3", summary="函数版本。")
add("kp3_5_1", "无穷小", 4, "sec3_5", summary="lim f = 0。")
add("kp3_5_2", "无穷小的比较", 4, "sec3_5", summary="同阶、等价、高阶。")
add("kp3_5_3", "等价无穷小代换", 4, "sec3_5", summary="乘除位置可互换。")
add("kp3_5_4", "无穷大", 4, "sec3_5", summary="lim f = ∞。")

add("sec3_6", "函数连续的定义", 3, "ch3", summary="lim f(x) = f(x₀)。")
add("kp3_6_1", "函数在一点处连续的定义", 4, "sec3_6", summary="ε-δ 形式。")
add("kp3_6_2", "左右连续", 4, "sec3_6", summary="单侧连续。")
add("kp3_6_3", "函数在区间上连续", 4, "sec3_6", summary="逐点连续 + 端点单侧。")
add("kp3_6_4", "间断点及其分类", 4, "sec3_6", summary="可去、跳跃、无穷、振荡。")

add("sec3_7", "连续函数的运算与性质", 3, "ch3", summary="保持运算。")
add("kp3_7_1", "连续函数的四则运算", 4, "sec3_7", summary="加减乘除（除外分母非零）连续。")
add("kp3_7_2", "复合函数的连续性", 4, "sec3_7", summary="连续映射的复合仍连续。")
add("kp3_7_3", "反函数的连续性", 4, "sec3_7", summary="区间上严格单调连续函数其反函数连续。")
add("kp3_7_4", "初等函数的连续性", 4, "sec3_7", summary="在定义域内连续。")

add("sec3_8", "闭区间上连续函数的性质", 3, "ch3", summary="紧致带来的整体性质。")
add("kp3_8_1", "最值定理", 4, "sec3_8", summary="闭区间连续函数必取到最大、最小值。")
add("kp3_8_2", "有界性定理", 4, "sec3_8", summary="闭区间连续函数必有界。")
add("kp3_8_3", "零点存在定理", 4, "sec3_8", summary="两端异号则存在零点。")
add("kp3_8_4", "介值定理", 4, "sec3_8", summary="闭区间连续函数取所有中间值。")
add("kp3_8_5", "一致连续性", 4, "sec3_8", summary="δ 与点无关。")
add("kp3_8_6", "Cantor定理", 4, "sec3_8", summary="闭区间连续函数必一致连续。")


# ---------- 第 4 章 函数的导数 ----------
add("ch4", "函数的导数", 2, "dom_diff_uni",
    summary="局部线性化：用切线近似函数。")

add("sec4_1", "导数的概念", 3, "ch4", summary="增量比的极限。")
add("kp4_1_1", "导数的定义", 4, "sec4_1", summary="f'(x₀)=lim (f(x₀+h)-f(x₀))/h。")
add("kp4_1_2", "导数的几何意义", 4, "sec4_1", summary="切线斜率。")
add("kp4_1_3", "导数的物理意义", 4, "sec4_1", summary="瞬时变化率，如速度、加速度。")
add("kp4_1_4", "单侧导数", 4, "sec4_1", summary="左导数 f'₋ 与右导数 f'₊。")
add("kp4_1_5", "可导与连续的关系", 4, "sec4_1", summary="可导必连续，反之不真。")

add("sec4_2", "导数的运算法则", 3, "ch4", summary="加减乘除链式。")
add("kp4_2_1", "四则运算的求导", 4, "sec4_2", summary="(u±v)'=u'±v'，(uv)'=u'v+uv' 等。")
add("kp4_2_2", "复合函数求导（链式法则）", 4, "sec4_2", summary="(g∘f)'=g'(f)·f'。")
add("kp4_2_3", "反函数的导数", 4, "sec4_2", summary="(f⁻¹)'(y)=1/f'(x)。")

add("sec4_3", "由定义求导", 3, "ch4", summary="对非初等函数或边界点。")
add("kp4_3_1", "由定义求导举例", 4, "sec4_3", summary="如绝对值函数在 0 点。")

add("sec4_4", "基本初等函数的导数", 3, "ch4", summary="导数公式表。")
add("kp4_4_1", "幂函数的导数", 4, "sec4_4", summary="(xⁿ)'=nx^{n-1}。")
add("kp4_4_2", "指数函数的导数", 4, "sec4_4", summary="(eˣ)'=eˣ。")
add("kp4_4_3", "对数函数的导数", 4, "sec4_4", summary="(ln x)'=1/x。")
add("kp4_4_4", "三角函数的导数", 4, "sec4_4", summary="(sin x)'=cos x 等。")
add("kp4_4_5", "反三角函数的导数", 4, "sec4_4", summary="(arcsin x)'=1/√(1-x²) 等。")
add("kp4_4_6", "双曲函数的导数", 4, "sec4_4", summary="(sinh x)'=cosh x。")

add("sec4_5", "高阶导数", 3, "ch4", summary="多次求导。")
add("kp4_5_1", "高阶导数的定义", 4, "sec4_5", summary="f^(n) = (f^(n-1))'。")
add("kp4_5_2", "高阶导数的运算", 4, "sec4_5", summary="线性 + Leibniz 公式。")
add("kp4_5_3", "Leibniz公式", 4, "sec4_5", summary="(uv)^(n)=Σ C(n,k) u^(k) v^(n-k)。")

add("sec4_6", "隐函数与参数方程求导", 3, "ch4", summary="非显式表达式的导数。")
add("kp4_6_1", "隐函数求导法", 4, "sec4_6", summary="对方程两边求 d/dx。")
add("kp4_6_2", "对数求导法", 4, "sec4_6", summary="先取对数再求导，处理幂指型。")
add("kp4_6_3", "参数方程求导", 4, "sec4_6", summary="dy/dx = (dy/dt)/(dx/dt)。")

add("sec4_7", "微分", 3, "ch4", summary="一阶近似量。")
add("kp4_7_1", "微分的定义", 4, "sec4_7", summary="Δf ≈ f'(x)Δx, df = f'(x)dx。")
add("kp4_7_2", "微分的几何意义", 4, "sec4_7", summary="切线的纵坐标增量。")
add("kp4_7_3", "微分形式不变性", 4, "sec4_7", summary="df = f'(x)dx 与 x 是自变量还是中间变量无关。")
add("kp4_7_4", "微分的近似应用", 4, "sec4_7", summary="f(x₀+Δx)≈f(x₀)+f'(x₀)Δx。")


# ---------- 第 5 章 微分中值定理 ----------
add("ch5", "微分中值定理", 2, "dom_diff_uni",
    summary="局部信息（导数）⇄ 整体信息（函数值差）的桥梁。")

add("sec5_1", "费马引理", 3, "ch5", summary="极值点的必要条件。")
add("kp5_1_1", "费马引理", 4, "sec5_1", summary="可导极值点处 f'=0。")
add("kp5_1_2", "驻点", 4, "sec5_1", summary="f'(x)=0 的点。")

add("sec5_2", "罗尔定理", 3, "ch5", summary="两端值相等则中间有水平切线。")
add("kp5_2_1", "罗尔定理", 4, "sec5_2", summary="f 在 [a,b] 连续、(a,b) 可导、f(a)=f(b) ⇒ ∃ξ, f'(ξ)=0。")

add("sec5_3", "拉格朗日中值定理", 3, "ch5", summary="一般化的罗尔。")
add("kp5_3_1", "拉格朗日中值定理", 4, "sec5_3", summary="(f(b)-f(a))/(b-a)=f'(ξ)。")
add("kp5_3_2", "拉格朗日定理的推论", 4, "sec5_3", summary="导数恒为零的函数为常数。")
add("kp5_3_3", "函数差与导数的估计", 4, "sec5_3", summary="|f(b)-f(a)|≤M|b-a|。")

add("sec5_4", "柯西中值定理", 3, "ch5", summary="两函数比值形式。")
add("kp5_4_1", "柯西中值定理", 4, "sec5_4", summary="(f(b)-f(a))/(g(b)-g(a))=f'(ξ)/g'(ξ)。")

add("sec5_5", "洛必达法则", 3, "ch5", summary="未定式极限的导数化处理。")
add("kp5_5_1", "0/0型洛必达法则", 4, "sec5_5", summary="同趋 0 时比值=导数之比的极限。")
add("kp5_5_2", "∞/∞型洛必达法则", 4, "sec5_5", summary="同趋无穷时同样。")
add("kp5_5_3", "其他未定式", 4, "sec5_5", summary="0·∞, ∞-∞, 0⁰, 1^∞, ∞⁰ 转 0/0 或 ∞/∞。")


# ---------- 第 6 章 导数的应用 ----------
add("ch6", "导数的应用", 2, "dom_diff_uni",
    summary="单调性、凹凸性、极值、作图。")

add("sec6_1", "函数的单调性", 3, "ch6", summary="一阶导数符号判定。")
add("kp6_1_1", "单调性判定", 4, "sec6_1", summary="f'>0 单增，f'<0 单减。")
add("kp6_1_2", "严格单调", 4, "sec6_1", summary="加强为严格 > 或 <。")

add("sec6_2", "函数的极值", 3, "ch6", summary="局部最值。")
add("kp6_2_1", "极值的定义", 4, "sec6_2", summary="邻域内最大或最小。")
add("kp6_2_2", "极值的必要条件", 4, "sec6_2", summary="可导极值点必为驻点。")
add("kp6_2_3", "极值的第一充分条件", 4, "sec6_2", summary="导数变号判定。")
add("kp6_2_4", "极值的第二充分条件", 4, "sec6_2", summary="二阶导数符号判定。")

add("sec6_3", "最值与最优化", 3, "ch6", summary="闭区间最值。")
add("kp6_3_1", "闭区间最值求法", 4, "sec6_3", summary="比较驻点、不可导点、端点。")
add("kp6_3_2", "实际优化问题", 4, "sec6_3", summary="建模 + 求导。")

add("sec6_4", "凹凸性与拐点", 3, "ch6", summary="二阶导数符号。")
add("kp6_4_1", "凹凸的定义", 4, "sec6_4", summary="弦在曲线上 / 下方。")
add("kp6_4_2", "凹凸性判定", 4, "sec6_4", summary="f''>0 凹 (向上凸)，f''<0 凸。")
add("kp6_4_3", "拐点", 4, "sec6_4", summary="凹凸性变化点，需 f''变号。")

add("sec6_5", "渐近线", 3, "ch6", summary="函数图形的远端走势。")
add("kp6_5_1", "水平渐近线", 4, "sec6_5", summary="lim_{x→∞} f(x)=A。")
add("kp6_5_2", "铅直渐近线", 4, "sec6_5", summary="lim_{x→x₀} f(x)=∞。")
add("kp6_5_3", "斜渐近线", 4, "sec6_5", summary="f(x)=kx+b+o(1)。")

add("sec6_6", "函数作图", 3, "ch6", summary="综合分析画图。")
add("kp6_6_1", "函数作图步骤", 4, "sec6_6", summary="定义域→对称性→渐近线→单调极值→凹凸拐点。")

add("sec6_7", "曲率", 3, "ch6", summary="曲线弯曲程度。")
add("kp6_7_1", "曲率的定义", 4, "sec6_7", summary="κ=|y''|/(1+y'²)^{3/2}。")
add("kp6_7_2", "曲率圆与曲率半径", 4, "sec6_7", summary="R=1/κ。")


# ---------- 第 7 章 泰勒公式 ----------
add("ch7", "泰勒公式", 2, "dom_diff_uni",
    summary="用多项式 + 余项精确逼近函数。")

add("sec7_1", "泰勒中值定理", 3, "ch7", summary="带余项的高阶展开。")
add("kp7_1_1", "Peano余项的泰勒公式", 4, "sec7_1", summary="局部近似，余项 o((x-x₀)ⁿ)。")
add("kp7_1_2", "Lagrange余项的泰勒公式", 4, "sec7_1", summary="整体形式，余项含 f^(n+1)(ξ)。")
add("kp7_1_3", "Cauchy余项的泰勒公式", 4, "sec7_1", summary="便于积分估计。")
add("kp7_1_4", "积分余项", 4, "sec7_1", summary="∫ 形式，便于显式估计。")

add("sec7_2", "麦克劳林公式", 3, "ch7", summary="泰勒公式在 0 处展开。")
add("kp7_2_1", "麦克劳林公式", 4, "sec7_2", summary="x₀=0 的特例。")
add("kp7_2_2", "常用函数的麦克劳林展开", 4, "sec7_2", summary="eˣ、sin x、cos x、ln(1+x)、(1+x)^α。")

add("sec7_3", "泰勒公式的应用", 3, "ch7", summary="求极限、估计误差、判定极值。")
add("kp7_3_1", "用泰勒公式求极限", 4, "sec7_3", summary="替代等价无穷小处理高阶项。")
add("kp7_3_2", "近似计算与误差估计", 4, "sec7_3", summary="按 Lagrange 余项给出误差界。")
add("kp7_3_3", "用泰勒判定极值", 4, "sec7_3", summary="多阶导数符号判定。")


# ---------- 第 8 章 不定积分 ----------
add("ch8", "不定积分", 2, "dom_int_uni",
    summary="求导的逆运算：寻找原函数。")

add("sec8_1", "原函数与不定积分", 3, "ch8", summary="基本概念。")
add("kp8_1_1", "原函数的定义", 4, "sec8_1", summary="F'=f 的 F 叫 f 的原函数。")
add("kp8_1_2", "不定积分的定义", 4, "sec8_1", summary="原函数族 F(x)+C。")
add("kp8_1_3", "不定积分的几何意义", 4, "sec8_1", summary="同一族平行曲线。")
add("kp8_1_4", "基本积分公式", 4, "sec8_1", summary="导数公式倒过来。")
add("kp8_1_5", "不定积分线性性质", 4, "sec8_1", summary="∫(αf+βg) = α∫f+β∫g。")

add("sec8_2", "换元积分法", 3, "ch8", summary="变量替换。")
add("kp8_2_1", "第一类换元法", 4, "sec8_2", summary="凑微分。")
add("kp8_2_2", "第二类换元法", 4, "sec8_2", summary="令 x=φ(t) 反向代换。")
add("kp8_2_3", "三角代换", 4, "sec8_2", summary="x=a sinθ 等去根号。")
add("kp8_2_4", "倒代换", 4, "sec8_2", summary="x=1/t。")

add("sec8_3", "分部积分法", 3, "ch8", summary="∫udv = uv - ∫vdu。")
add("kp8_3_1", "分部积分公式", 4, "sec8_3", summary="由乘积求导反推。")
add("kp8_3_2", "分部积分技巧", 4, "sec8_3", summary="选 u 的优先级 (反对幂指三)。")

add("sec8_4", "有理函数积分", 3, "ch8", summary="多项式商。")
add("kp8_4_1", "有理函数的部分分式分解", 4, "sec8_4", summary="拆为简单分式之和。")
add("kp8_4_2", "三角有理函数积分", 4, "sec8_4", summary="万能代换 t=tan(x/2)。")
add("kp8_4_3", "无理函数积分", 4, "sec8_4", summary="去根号化为有理。")


# ---------- 第 9 章 定积分 ----------
add("ch9", "定积分", 2, "dom_int_uni",
    summary="区间上的累积量：Riemann 和的极限。")

add("sec9_1", "定积分的概念", 3, "ch9", summary="Riemann 和与可积性。")
add("kp9_1_1", "定积分的定义", 4, "sec9_1", summary="分割→取点→求和→取极限。")
add("kp9_1_2", "定积分的几何意义", 4, "sec9_1", summary="带符号面积。")
add("kp9_1_3", "可积的必要条件", 4, "sec9_1", summary="有界是必要不充分。")
add("kp9_1_4", "可积的充分条件", 4, "sec9_1", summary="连续 / 单调 / 有有限间断点。")
add("kp9_1_5", "Darboux和", 4, "sec9_1", summary="上、下和。")

add("sec9_2", "定积分的性质", 3, "ch9", summary="线性、单调、可加。")
add("kp9_2_1", "线性性质", 4, "sec9_2", summary="∫(αf+βg)。")
add("kp9_2_2", "区间可加性", 4, "sec9_2", summary="∫_a^b = ∫_a^c + ∫_c^b。")
add("kp9_2_3", "保号保序性", 4, "sec9_2", summary="积分继承不等式。")
add("kp9_2_4", "估值不等式", 4, "sec9_2", summary="m(b-a)≤∫f≤M(b-a)。")
add("kp9_2_5", "积分中值定理", 4, "sec9_2", summary="存在 ξ 使 ∫f=f(ξ)(b-a)。")
add("kp9_2_6", "推广积分中值定理", 4, "sec9_2", summary="带权 g≥0 形式。")

add("sec9_3", "牛顿-莱布尼茨公式", 3, "ch9", summary="微积分基本定理。")
add("kp9_3_1", "变上限积分", 4, "sec9_3", summary="Φ(x)=∫_a^x f。")
add("kp9_3_2", "变上限积分求导", 4, "sec9_3", summary="Φ'(x)=f(x)。")
add("kp9_3_3", "原函数存在定理", 4, "sec9_3", summary="连续函数必有原函数。")
add("kp9_3_4", "牛顿-莱布尼茨公式", 4, "sec9_3", summary="∫_a^b f = F(b)-F(a)。")

add("sec9_4", "定积分的计算", 3, "ch9", summary="换元 + 分部。")
add("kp9_4_1", "定积分换元法", 4, "sec9_4", summary="同时换上下限。")
add("kp9_4_2", "定积分分部积分法", 4, "sec9_4", summary="保留边界项。")
add("kp9_4_3", "对称性应用", 4, "sec9_4", summary="奇偶 / 周期函数对称区间简化。")


# ---------- 第 10 章 定积分的应用 ----------
add("ch10", "定积分的应用", 2, "dom_int_uni",
    summary="几何量与物理量的计算。")

add("sec10_1", "微元法", 3, "ch10", summary="切片 / 微元思想。")
add("kp10_1_1", "微元法思想", 4, "sec10_1", summary="dA→∫dA。")

add("sec10_2", "几何应用", 3, "ch10", summary="面积、体积、弧长、旋转面。")
add("kp10_2_1", "平面图形的面积", 4, "sec10_2", summary="直角坐标 / 极坐标。")
add("kp10_2_2", "极坐标下的面积", 4, "sec10_2", summary="∫½ρ²dθ。")
add("kp10_2_3", "旋转体体积", 4, "sec10_2", summary="圆盘法 / 壳法。")
add("kp10_2_4", "已知截面积体积", 4, "sec10_2", summary="∫A(x)dx。")
add("kp10_2_5", "平面曲线弧长", 4, "sec10_2", summary="∫√(1+y'²)dx。")
add("kp10_2_6", "旋转面侧面积", 4, "sec10_2", summary="2π∫y√(1+y'²)dx。")

add("sec10_3", "物理应用", 3, "ch10", summary="功、压力、引力、质心。")
add("kp10_3_1", "变力做功", 4, "sec10_3", summary="W=∫F(x)dx。")
add("kp10_3_2", "液体压力", 4, "sec10_3", summary="P=∫ρgh·dA。")
add("kp10_3_3", "万有引力", 4, "sec10_3", summary="F=G∫m₁m₂/r²。")
add("kp10_3_4", "质心与形心", 4, "sec10_3", summary="∫xρdA / ∫ρdA。")


# ---------- 第 11 章 广义积分 ----------
add("ch11", "广义积分", 2, "dom_int_uni",
    summary="无穷区间 / 无界函数的积分。")

add("sec11_1", "无穷区间广义积分", 3, "ch11", summary="∫_a^∞ f。")
add("kp11_1_1", "无穷限广义积分定义", 4, "sec11_1", summary="lim_{b→∞} ∫_a^b。")
add("kp11_1_2", "收敛/发散", 4, "sec11_1", summary="极限存在则收敛。")
add("kp11_1_3", "无穷限的比较判别法", 4, "sec11_1", summary="0≤f≤g 时收敛性传递。")
add("kp11_1_4", "无穷限的极限比较判别法", 4, "sec11_1", summary="lim f/g = c。")
add("kp11_1_5", "p积分判别", 4, "sec11_1", summary="∫₁^∞ 1/xᵖ 收敛 ⇔ p>1。")

add("sec11_2", "瑕积分", 3, "ch11", summary="被积函数在端点无界。")
add("kp11_2_1", "瑕积分定义", 4, "sec11_2", summary="lim_{ε→0⁺} ∫_{a+ε}^b。")
add("kp11_2_2", "瑕积分比较判别", 4, "sec11_2", summary="对端点附近放大。")
add("kp11_2_3", "瑕点p积分判别", 4, "sec11_2", summary="∫₀¹ 1/xᵖ 收敛 ⇔ p<1。")

add("sec11_3", "广义积分的绝对收敛与条件收敛", 3, "ch11", summary="符号变化的情况。")
add("kp11_3_1", "绝对收敛", 4, "sec11_3", summary="∫|f| 收敛。")
add("kp11_3_2", "条件收敛", 4, "sec11_3", summary="∫f 收敛但 ∫|f| 发散。")
add("kp11_3_3", "Abel判别法", 4, "sec11_3", summary="一项单调有界。")
add("kp11_3_4", "Dirichlet判别法", 4, "sec11_3", summary="一项单调趋零 + 另一项部分积分有界。")
add("kp11_3_5", "Γ函数", 4, "sec11_3", summary="∫₀^∞ x^{s-1}e^{-x}dx。")
add("kp11_3_6", "B函数", 4, "sec11_3", summary="∫₀¹ x^{p-1}(1-x)^{q-1}dx。")


# ---------- 第 12 章 微分方程 ----------
add("ch12", "微分方程", 2, "dom_series_ode",
    summary="含未知函数及其导数的方程。")

add("sec12_1", "微分方程的基本概念", 3, "ch12", summary="阶数、解、初值问题。")
add("kp12_1_1", "微分方程的定义", 4, "sec12_1", summary="含未知函数及其导数。")
add("kp12_1_2", "微分方程的阶", 4, "sec12_1", summary="最高阶导数。")
add("kp12_1_3", "解与通解", 4, "sec12_1", summary="满足方程的函数 / 含任意常数族。")
add("kp12_1_4", "特解与初值问题", 4, "sec12_1", summary="确定常数。")

add("sec12_2", "一阶微分方程", 3, "ch12", summary="可分离 / 齐次 / 线性。")
add("kp12_2_1", "可分离变量方程", 4, "sec12_2", summary="dy/dx=f(x)g(y)。")
add("kp12_2_2", "齐次方程", 4, "sec12_2", summary="dy/dx=φ(y/x)，令 u=y/x。")
add("kp12_2_3", "一阶线性方程", 4, "sec12_2", summary="y'+P(x)y=Q(x)，积分因子。")
add("kp12_2_4", "积分因子", 4, "sec12_2", summary="μ=e^{∫P dx}。")
add("kp12_2_5", "伯努利方程", 4, "sec12_2", summary="y'+P(x)y=Q(x)yⁿ，z=y^{1-n} 化线性。")
add("kp12_2_6", "全微分方程", 4, "sec12_2", summary="M dx+N dy = 0 且 ∂M/∂y=∂N/∂x。")

add("sec12_3", "可降阶高阶微分方程", 3, "ch12", summary="降阶技巧。")
add("kp12_3_1", "y^(n)=f(x)型", 4, "sec12_3", summary="逐次积分。")
add("kp12_3_2", "y''=f(x,y')型", 4, "sec12_3", summary="令 p=y'。")
add("kp12_3_3", "y''=f(y,y')型", 4, "sec12_3", summary="令 p=y'，视 p 为 y 的函数。")

add("sec12_4", "二阶线性微分方程", 3, "ch12", summary="结构定理 + 常系数解法。")
add("kp12_4_1", "二阶线性方程的结构", 4, "sec12_4", summary="解空间维数 = 2。")
add("kp12_4_2", "齐次方程通解结构", 4, "sec12_4", summary="两个线性无关解的组合。")
add("kp12_4_3", "Wronski行列式", 4, "sec12_4", summary="判定线性无关。")
add("kp12_4_4", "非齐次方程通解结构", 4, "sec12_4", summary="齐次通解+特解。")
add("kp12_4_5", "常系数齐次方程", 4, "sec12_4", summary="特征方程。")
add("kp12_4_6", "常系数非齐次方程", 4, "sec12_4", summary="待定系数法。")
add("kp12_4_7", "常数变易法", 4, "sec12_4", summary="变常数为函数求特解。")
add("kp12_4_8", "欧拉方程", 4, "sec12_4", summary="x²y''+axy'+by=f(x)，令 x=eᵗ。")


# ===============================================================
# 下册 —— 8 章
# ===============================================================

# ---------- 第 13 章 多元函数极限与连续 ----------
add("ch13", "多元函数极限与连续", 2, "dom_diff_multi",
    summary="把一元的极限-连续推广到 ℝⁿ 上，关键变化在邻域形态和趋近路径的丰富性。")

add("sec13_1", "n维欧氏空间", 3, "ch13", summary="多元分析的舞台。")
add("kp13_1_1", "ℝⁿ的定义", 4, "sec13_1", summary="n 维有序数组的全体。")
add("kp13_1_2", "n维向量与运算", 4, "sec13_1", summary="加法、数乘、内积。")
add("kp13_1_3", "n维距离与范数", 4, "sec13_1", summary="欧氏距离 ‖x-y‖。")
add("kp13_1_4", "邻域", 4, "sec13_1", summary="球形 / 矩形邻域。")
add("kp13_1_5", "开集与闭集", 4, "sec13_1", summary="内点 / 边界点 / 聚点。")
add("kp13_1_6", "聚点与孤立点", 4, "sec13_1", summary="去心邻域含集合点。")
add("kp13_1_7", "有界集与紧集", 4, "sec13_1", summary="ℝⁿ 中紧 ⇔ 有界闭。")
add("kp13_1_8", "区域", 4, "sec13_1", summary="连通的开集。")

add("sec13_2", "多元函数概念", 3, "ch13", summary="z=f(x,y)、u=f(x₁,...,xₙ)。")
add("kp13_2_1", "多元函数的定义", 4, "sec13_2", summary="ℝⁿ⊃D 到 ℝ 的映射。")
add("kp13_2_2", "二元函数的图形", 4, "sec13_2", summary="ℝ³ 中曲面。")
add("kp13_2_3", "等值线/等值面", 4, "sec13_2", summary="f=c 形成的曲线/曲面。")

add("sec13_3", "多元函数的极限", 3, "ch13", summary="点列趋近 P₀ 时函数值的极限。")
add("kp13_3_1", "二重极限定义", 4, "sec13_3", summary="ε-δ：‖x-x₀‖<δ ⇒ |f-A|<ε。")
add("kp13_3_2", "二重极限的几何意义", 4, "sec13_3", summary="去心邻域内函数值终落入水平带。")
add("kp13_3_3", "极限不存在的判别", 4, "sec13_3", summary="找两条不同路径极限不同。")
add("kp13_3_4", "累次极限", 4, "sec13_3", summary="先固定 y 求 x 极限再求 y。")
add("kp13_3_5", "二重极限与累次极限的关系", 4, "sec13_3", summary="二重存在加额外条件 ⇒ 累次相等。")

add("sec13_4", "多元函数的连续性", 3, "ch13", summary="lim_{P→P₀} f(P)=f(P₀)。")
add("kp13_4_1", "多元连续的定义", 4, "sec13_4", summary="极限值等于函数值。")
add("kp13_4_2", "多元连续的运算", 4, "sec13_4", summary="四则、复合连续。")
add("kp13_4_3", "有界闭区域上连续函数性质", 4, "sec13_4", summary="最值定理、介值定理、一致连续。")


# ---------- 第 14 章 多元函数微分学 ----------
add("ch14", "多元函数微分学", 2, "dom_diff_multi",
    summary="偏导、全微分、链式法则、方向导数、梯度、隐函数定理。")

add("sec14_1", "偏导数", 3, "ch14", summary="把其余变量固定后的导数。")
add("kp14_1_1", "偏导数的定义", 4, "sec14_1", summary="∂f/∂x = lim (f(x+h,y)-f(x,y))/h。")
add("kp14_1_2", "偏导数的几何意义", 4, "sec14_1", summary="切片曲线的斜率。")
add("kp14_1_3", "偏导数的计算", 4, "sec14_1", summary="把其余变量看作常数。")
add("kp14_1_4", "高阶偏导数", 4, "sec14_1", summary="∂²f/∂x∂y 等。")
add("kp14_1_5", "混合偏导数相等条件", 4, "sec14_1", summary="Clairaut/Schwarz 定理：连续即可换序。")

add("sec14_2", "全微分", 3, "ch14", summary="线性近似。")
add("kp14_2_1", "全增量与全微分", 4, "sec14_2", summary="Δf=A Δx+B Δy+o(ρ)。")
add("kp14_2_2", "可微的定义", 4, "sec14_2", summary="存在线性主部使误差为高阶无穷小。")
add("kp14_2_3", "可微的必要条件", 4, "sec14_2", summary="可微 ⇒ 偏导存在且 df=f_x dx+f_y dy。")
add("kp14_2_4", "可微的充分条件", 4, "sec14_2", summary="偏导存在且连续 ⇒ 可微。")
add("kp14_2_5", "可微与连续的关系", 4, "sec14_2", summary="可微 ⇒ 连续。")
add("kp14_2_6", "全微分形式不变性", 4, "sec14_2", summary="df 的形式与中间变量无关。")

add("sec14_3", "多元复合函数求导", 3, "ch14", summary="链式法则的多元版本。")
add("kp14_3_1", "多元复合函数的链式法则", 4, "sec14_3", summary="dz/dt = f_x x'+f_y y'。")
add("kp14_3_2", "全导数", 4, "sec14_3", summary="对单参数复合的总导数。")
add("kp14_3_3", "链式法则的树形图", 4, "sec14_3", summary="按路径加和。")

add("sec14_4", "隐函数微分法", 3, "ch14", summary="由方程组确定的函数及其导数。")
add("kp14_4_1", "一元隐函数定理", 4, "sec14_4", summary="F(x,y)=0 局部确定 y=f(x)。")
add("kp14_4_2", "多元隐函数定理", 4, "sec14_4", summary="F(x,y,z)=0 局部确定 z=f(x,y)。")
add("kp14_4_3", "方程组确定的隐函数", 4, "sec14_4", summary="Jacobi 矩阵非奇异。")
add("kp14_4_4", "Jacobi行列式", 4, "sec14_4", summary="∂(F,G)/∂(u,v)。")

add("sec14_5", "方向导数与梯度", 3, "ch14", summary="函数沿任意方向的变化率。")
add("kp14_5_1", "方向导数的定义", 4, "sec14_5", summary="∂f/∂l = lim (f(P+tl)-f(P))/t。")
add("kp14_5_2", "方向导数的计算公式", 4, "sec14_5", summary="可微时 = ∇f·e_l。")
add("kp14_5_3", "梯度的定义", 4, "sec14_5", summary="∇f = (f_x, f_y, f_z)。")
add("kp14_5_4", "梯度的几何意义", 4, "sec14_5", summary="指向函数增长最快方向，模为最大变化率。")
add("kp14_5_5", "梯度与等值面正交", 4, "sec14_5", summary="梯度垂直于等值面。")

add("sec14_6", "空间曲线与曲面的切与法", 3, "ch14", summary="几何上的可微应用。")
add("kp14_6_1", "空间曲线的切线", 4, "sec14_6", summary="参数方程求导。")
add("kp14_6_2", "空间曲线的法平面", 4, "sec14_6", summary="与切向量正交。")
add("kp14_6_3", "曲面的切平面", 4, "sec14_6", summary="由两条偏导数曲线张成。")
add("kp14_6_4", "曲面的法线", 4, "sec14_6", summary="切平面的法向量。")


# ---------- 第 15 章 多元微分学应用 ----------
add("ch15", "多元微分学应用", 2, "dom_diff_multi",
    summary="极值、条件极值、Taylor 展开。")

add("sec15_1", "多元函数极值", 3, "ch15", summary="必要 / 充分条件。")
add("kp15_1_1", "多元极值的定义", 4, "sec15_1", summary="邻域内最大或最小。")
add("kp15_1_2", "极值的必要条件", 4, "sec15_1", summary="可微极值点 ⇒ ∇f=0。")
add("kp15_1_3", "驻点（多元）", 4, "sec15_1", summary="∇f=0 但未必极值。")
add("kp15_1_4", "Hessian矩阵", 4, "sec15_1", summary="二阶偏导构成的对称矩阵。")
add("kp15_1_5", "极值的二阶充分条件", 4, "sec15_1", summary="Hessian 正/负定 ⇒ 极小/大值。")
add("kp15_1_6", "鞍点", 4, "sec15_1", summary="Hessian 不定。")
add("kp15_1_7", "多元最值问题", 4, "sec15_1", summary="比较内部驻点与边界。")

add("sec15_2", "条件极值与拉格朗日乘数法", 3, "ch15", summary="约束下的极值。")
add("kp15_2_1", "条件极值定义", 4, "sec15_2", summary="在约束 g(x)=0 上的极值。")
add("kp15_2_2", "拉格朗日乘数法", 4, "sec15_2", summary="构造 L=f-λg，∇L=0。")
add("kp15_2_3", "多约束情形", 4, "sec15_2", summary="多个 λᵢ 对应多个约束。")
add("kp15_2_4", "条件极值的几何意义", 4, "sec15_2", summary="∇f 与 ∇g 平行。")

add("sec15_3", "多元函数的Taylor公式", 3, "ch15", summary="高维多项式逼近。")
add("kp15_3_1", "二元函数Taylor公式", 4, "sec15_3", summary="(h∂_x+k∂_y)ⁿ 形式。")
add("kp15_3_2", "Peano余项与Lagrange余项（多元）", 4, "sec15_3", summary="局部 / 整体两种。")
add("kp15_3_3", "多元函数的极值与Hessian", 4, "sec15_3", summary="用 Taylor 二阶项判定。")


# ---------- 第 16 章 重积分 ----------
add("ch16", "重积分", 2, "dom_int_multi",
    summary="把 Riemann 积分推广到平面区域 / 空间区域。")

add("sec16_1", "二重积分", 3, "ch16", summary="平面区域的累积。")
add("kp16_1_1", "二重积分的定义", 4, "sec16_1", summary="区域分割 + 黎曼和。")
add("kp16_1_2", "二重积分的几何意义", 4, "sec16_1", summary="曲顶柱体体积。")
add("kp16_1_3", "二重积分的性质", 4, "sec16_1", summary="线性、可加、保号、中值。")
add("kp16_1_4", "二重积分中值定理", 4, "sec16_1", summary="∬f = f(ξ,η)·σ。")

add("sec16_2", "二重积分计算", 3, "ch16", summary="化为累次积分。")
add("kp16_2_1", "直角坐标累次积分", 4, "sec16_2", summary="按 X 型 / Y 型区域。")
add("kp16_2_2", "二重积分换序", 4, "sec16_2", summary="改变积分顺序的关键是画域。")
add("kp16_2_3", "极坐标下的二重积分", 4, "sec16_2", summary="dx dy = ρ dρ dθ。")
add("kp16_2_4", "二重积分一般变量替换", 4, "sec16_2", summary="dxdy = |J| du dv。")

add("sec16_3", "三重积分", 3, "ch16", summary="空间区域的累积。")
add("kp16_3_1", "三重积分的定义", 4, "sec16_3", summary="空间分割 + 黎曼和。")
add("kp16_3_2", "三重积分的性质", 4, "sec16_3", summary="与二重平行。")
add("kp16_3_3", "直角坐标累次积分（三重）", 4, "sec16_3", summary="先一后二 / 先二后一。")
add("kp16_3_4", "柱面坐标变换", 4, "sec16_3", summary="dV = ρ dρ dθ dz。")
add("kp16_3_5", "球面坐标变换", 4, "sec16_3", summary="dV = r²sinφ dr dφ dθ。")
add("kp16_3_6", "三重积分的变量替换", 4, "sec16_3", summary="dV = |J| du dv dw。")

add("sec16_4", "重积分的应用", 3, "ch16", summary="几何与物理。")
add("kp16_4_1", "曲面面积", 4, "sec16_4", summary="∬√(1+z_x²+z_y²)dxdy。")
add("kp16_4_2", "立体体积", 4, "sec16_4", summary="∭dV。")
add("kp16_4_3", "质量与质心（重积分）", 4, "sec16_4", summary="∬ρ dσ / 加权求平均。")
add("kp16_4_4", "转动惯量", 4, "sec16_4", summary="∬ρ·r² dσ。")
add("kp16_4_5", "引力问题", 4, "sec16_4", summary="∬ G ρ/r² dσ。")


# ---------- 第 17 章 曲线曲面积分 ----------
add("ch17", "曲线积分与曲面积分", 2, "dom_int_multi",
    summary="把积分搬到曲线和曲面上，连接微分形式与向量场。")

add("sec17_1", "第一型曲线积分", 3, "ch17", summary="对弧长积分。")
add("kp17_1_1", "第一型曲线积分的定义", 4, "sec17_1", summary="∫_L f(x,y)ds，与方向无关。")
add("kp17_1_2", "第一型曲线积分的性质", 4, "sec17_1", summary="线性、可加。")
add("kp17_1_3", "第一型曲线积分的计算", 4, "sec17_1", summary="化参数方程 ds=√(x'²+y'²)dt。")
add("kp17_1_4", "第一型曲线积分的应用", 4, "sec17_1", summary="质量、质心、弧长。")

add("sec17_2", "第二型曲线积分", 3, "ch17", summary="对坐标积分（向量场做功）。")
add("kp17_2_1", "第二型曲线积分的定义", 4, "sec17_2", summary="∫_L P dx + Q dy，与方向有关。")
add("kp17_2_2", "第二型曲线积分的性质", 4, "sec17_2", summary="反向变号。")
add("kp17_2_3", "第二型曲线积分的计算", 4, "sec17_2", summary="参数代入。")
add("kp17_2_4", "两类曲线积分的联系", 4, "sec17_2", summary="∫P dx + Q dy = ∫(P cosα + Q cosβ)ds。")

add("sec17_3", "格林公式", 3, "ch17", summary="平面闭曲线 ↔ 区域积分。")
add("kp17_3_1", "格林公式", 4, "sec17_3", summary="∮_L Pdx+Qdy = ∬(∂Q/∂x-∂P/∂y)dσ。")
add("kp17_3_2", "格林公式的条件", 4, "sec17_3", summary="正向、单连通、P/Q 一阶连续。")
add("kp17_3_3", "平面曲线积分与路径无关", 4, "sec17_3", summary="⇔ ∂Q/∂x=∂P/∂y 且单连通。")
add("kp17_3_4", "原函数存在的条件", 4, "sec17_3", summary="路径无关 ⇔ 存在 u(x,y) 使 du=Pdx+Qdy。")
add("kp17_3_5", "全微分方程的求解", 4, "sec17_3", summary="求原函数 u(x,y)=C。")

add("sec17_4", "第一型曲面积分", 3, "ch17", summary="对面积积分。")
add("kp17_4_1", "第一型曲面积分的定义", 4, "sec17_4", summary="∬_Σ f dS，与方向无关。")
add("kp17_4_2", "第一型曲面积分的计算", 4, "sec17_4", summary="dS=√(1+z_x²+z_y²)dxdy。")
add("kp17_4_3", "第一型曲面积分的应用", 4, "sec17_4", summary="质量、质心、表面积。")

add("sec17_5", "第二型曲面积分", 3, "ch17", summary="对坐标积分（流量）。")
add("kp17_5_1", "曲面侧的概念", 4, "sec17_5", summary="可定向 + 选定法向。")
add("kp17_5_2", "第二型曲面积分的定义", 4, "sec17_5", summary="∬ P dy dz+Q dz dx+R dx dy。")
add("kp17_5_3", "第二型曲面积分的计算", 4, "sec17_5", summary="投影到坐标面。")
add("kp17_5_4", "两类曲面积分的联系", 4, "sec17_5", summary="化为第一型 + 方向余弦。")

add("sec17_6", "高斯公式", 3, "ch17", summary="空间闭曲面 ↔ 体积积分。")
add("kp17_6_1", "高斯公式", 4, "sec17_6", summary="∯Pdydz+Qdzdx+Rdxdy = ∭(∂P/∂x+∂Q/∂y+∂R/∂z)dV。")
add("kp17_6_2", "通量与散度", 4, "sec17_6", summary="div F=∂P/∂x+∂Q/∂y+∂R/∂z。")
add("kp17_6_3", "散度的物理意义", 4, "sec17_6", summary="源的密度。")

add("sec17_7", "斯托克斯公式", 3, "ch17", summary="空间曲面边界 ↔ 曲面积分。")
add("kp17_7_1", "斯托克斯公式", 4, "sec17_7", summary="∮Pdx+Qdy+Rdz = ∬(∇×F)·dS。")
add("kp17_7_2", "环流量与旋度", 4, "sec17_7", summary="rot F = ∇×F。")
add("kp17_7_3", "旋度的物理意义", 4, "sec17_7", summary="局部转动趋势。")
add("kp17_7_4", "空间曲线积分与路径无关", 4, "sec17_7", summary="∇×F=0 且单连通。")


# ---------- 第 18 章 无穷级数 ----------
add("ch18", "无穷级数", 2, "dom_series_ode",
    summary="可数无穷项相加的极限：数项级数、函数项级数、幂级数。")

add("sec18_1", "数项级数", 3, "ch18", summary="∑aₙ 的收敛性。")
add("kp18_1_1", "级数收敛与发散的定义", 4, "sec18_1", summary="部分和 Sₙ 收敛。")
add("kp18_1_2", "级数收敛的必要条件", 4, "sec18_1", summary="lim aₙ = 0。")
add("kp18_1_3", "级数的基本性质", 4, "sec18_1", summary="线性、加项分组。")
add("kp18_1_4", "几何级数", 4, "sec18_1", summary="∑aqⁿ，|q|<1 收敛。")
add("kp18_1_5", "调和级数", 4, "sec18_1", summary="∑1/n 发散。")
add("kp18_1_6", "p级数", 4, "sec18_1", summary="∑1/nᵖ，p>1 收敛。")

add("sec18_2", "正项级数判别法", 3, "ch18", summary="aₙ≥0 的判别工具。")
add("kp18_2_1", "正项级数比较判别法", 4, "sec18_2", summary="0≤aₙ≤bₙ，∑bₙ 收敛 ⇒ ∑aₙ 收敛。")
add("kp18_2_2", "极限比较判别", 4, "sec18_2", summary="lim aₙ/bₙ = c>0 同敛散。")
add("kp18_2_3", "比值判别法（D'Alembert）", 4, "sec18_2", summary="lim a_{n+1}/aₙ。")
add("kp18_2_4", "根值判别法（Cauchy）", 4, "sec18_2", summary="lim aₙ^{1/n}。")
add("kp18_2_5", "积分判别法", 4, "sec18_2", summary="∑f(n) 与 ∫f 同敛散（f 正递减）。")
add("kp18_2_6", "Raabe判别法", 4, "sec18_2", summary="比值法 = 1 的细化。")

add("sec18_3", "任意项级数", 3, "ch18", summary="项符号不限。")
add("kp18_3_1", "交错级数的Leibniz判别", 4, "sec18_3", summary="|aₙ| 单减趋零。")
add("kp18_3_2", "绝对收敛", 4, "sec18_3", summary="∑|aₙ| 收敛。")
add("kp18_3_3", "条件收敛", 4, "sec18_3", summary="∑aₙ 收敛但 ∑|aₙ| 发散。")
add("kp18_3_4", "绝对收敛的运算", 4, "sec18_3", summary="可任意重排、按 Cauchy 乘积。")
add("kp18_3_5", "Abel判别法（级数）", 4, "sec18_3", summary="∑aₙbₙ，bₙ 单调有界、∑aₙ 收敛。")
add("kp18_3_6", "Dirichlet判别法（级数）", 4, "sec18_3", summary="aₙ 部分和有界 + bₙ 单调趋零。")

add("sec18_4", "函数项级数", 3, "ch18", summary="项是函数。")
add("kp18_4_1", "函数项级数的收敛域", 4, "sec18_4", summary="x 使 ∑uₙ(x) 收敛的全体。")
add("kp18_4_2", "和函数", 4, "sec18_4", summary="S(x)=∑uₙ(x)。")
add("kp18_4_3", "一致收敛的定义", 4, "sec18_4", summary="ε-N 与 x 无关。")
add("kp18_4_4", "Weierstrass M判别", 4, "sec18_4", summary="|uₙ|≤Mₙ 且 ∑Mₙ 收敛。")
add("kp18_4_5", "Cauchy一致收敛准则", 4, "sec18_4", summary="∀ε ∃N 与 x 无关。")
add("kp18_4_6", "一致收敛与连续性", 4, "sec18_4", summary="一致收敛 + 每项连续 ⇒ 和连续。")
add("kp18_4_7", "一致收敛与逐项积分", 4, "sec18_4", summary="∫∑ = ∑∫。")
add("kp18_4_8", "一致收敛与逐项求导", 4, "sec18_4", summary="∑u'ₙ 一致收敛即可换序。")

add("sec18_5", "幂级数", 3, "ch18", summary="∑aₙ(x-x₀)ⁿ。")
add("kp18_5_1", "幂级数的定义", 4, "sec18_5", summary="特殊的函数项级数。")
add("kp18_5_2", "收敛半径", 4, "sec18_5", summary="R 决定收敛区间。")
add("kp18_5_3", "Cauchy-Hadamard公式", 4, "sec18_5", summary="1/R = lim sup |aₙ|^{1/n}。")
add("kp18_5_4", "Abel定理", 4, "sec18_5", summary="收敛区间内绝对收敛、闭子区间一致收敛。")
add("kp18_5_5", "幂级数的运算", 4, "sec18_5", summary="加减、乘积、求导、积分。")
add("kp18_5_6", "幂级数的逐项可微可积", 4, "sec18_5", summary="在收敛区间内部任意阶可微。")

add("sec18_6", "函数展开为幂级数", 3, "ch18", summary="Taylor 级数。")
add("kp18_6_1", "Taylor级数", 4, "sec18_6", summary="∑f^(n)(x₀)/n! (x-x₀)ⁿ。")
add("kp18_6_2", "Maclaurin级数", 4, "sec18_6", summary="x₀=0 特例。")
add("kp18_6_3", "函数展开的充要条件", 4, "sec18_6", summary="余项 → 0。")
add("kp18_6_4", "常用函数的幂级数展开", 4, "sec18_6", summary="eˣ、sin、cos、ln(1+x)、(1+x)^α。")
add("kp18_6_5", "幂级数的应用", 4, "sec18_6", summary="近似计算、求和、解微分方程。")


# ---------- 第 19 章 Fourier 级数 ----------
add("ch19", "Fourier级数", 2, "dom_series_ode",
    summary="用三角函数系展开周期函数，是无穷级数与正交分解的典范。")

add("sec19_1", "三角函数系与正交性", 3, "ch19", summary="基函数族。")
add("kp19_1_1", "三角函数系", 4, "sec19_1", summary="1, cos x, sin x, cos 2x, ...")
add("kp19_1_2", "正交性", 4, "sec19_1", summary="∫_{-π}^{π} 不同函数乘积 = 0。")
add("kp19_1_3", "Euler-Fourier公式", 4, "sec19_1", summary="系数 aₙ, bₙ 的积分公式。")

add("sec19_2", "Fourier级数的展开", 3, "ch19", summary="基本展开法。")
add("kp19_2_1", "周期2π函数的Fourier级数", 4, "sec19_2", summary="a₀/2+∑(aₙcos nx+bₙsin nx)。")
add("kp19_2_2", "周期2L函数的Fourier级数", 4, "sec19_2", summary="变量代换。")
add("kp19_2_3", "奇/偶函数的Fourier级数", 4, "sec19_2", summary="奇函数纯 sin、偶函数纯 cos。")
add("kp19_2_4", "在[0,L]上的正弦/余弦展开", 4, "sec19_2", summary="奇延拓 / 偶延拓。")

add("sec19_3", "Fourier级数的收敛性", 3, "ch19", summary="Dirichlet 条件。")
add("kp19_3_1", "Dirichlet收敛定理", 4, "sec19_3", summary="分段单调有限间断 ⇒ 处处收敛到 [f(x⁺)+f(x⁻)]/2。")
add("kp19_3_2", "Bessel不等式", 4, "sec19_3", summary="∑(aₙ²+bₙ²) ≤ 系数 ∫f²。")
add("kp19_3_3", "Parseval等式", 4, "sec19_3", summary="完备性，等号成立。")
add("kp19_3_4", "Gibbs现象", 4, "sec19_3", summary="跳跃点附近的超调。")

add("sec19_4", "复数形式与广义Fourier", 3, "ch19", summary="更一般的展开。")
add("kp19_4_1", "复数形式的Fourier级数", 4, "sec19_4", summary="∑cₙe^{inx}。")
add("kp19_4_2", "广义Fourier级数", 4, "sec19_4", summary="按一般正交基展开。")
add("kp19_4_3", "Fourier积分变换初步", 4, "sec19_4", summary="非周期函数的延伸。")


# ---------- 第 20 章 常微分方程进阶 ----------
add("ch20", "常微分方程进阶", 2, "dom_series_ode",
    summary="高阶线性方程理论、解的结构、解的存在唯一性、线性方程组初步。")

add("sec20_1", "高阶线性微分方程理论", 3, "ch20", summary="叠加原理、解空间。")
add("kp20_1_1", "n阶线性方程", 4, "sec20_1", summary="y^(n)+a_{n-1}y^{(n-1)}+...+a₀y=f(x)。")
add("kp20_1_2", "解的存在唯一性（线性）", 4, "sec20_1", summary="初值问题在区间上唯一可解。")
add("kp20_1_3", "齐次方程解空间", 4, "sec20_1", summary="n 维向量空间。")
add("kp20_1_4", "线性无关与Wronski行列式（n阶）", 4, "sec20_1", summary="W≠0 ⇒ 线性无关。")
add("kp20_1_5", "Liouville公式", 4, "sec20_1", summary="W'(x) 与系数关系。")

add("sec20_2", "常系数线性方程", 3, "ch20", summary="代数化的解法。")
add("kp20_2_1", "n阶常系数齐次方程", 4, "sec20_2", summary="特征方程的根决定基础解。")
add("kp20_2_2", "复根与重根处理", 4, "sec20_2", summary="复根给 sin/cos，重根加 x 因子。")
add("kp20_2_3", "n阶常系数非齐次方程", 4, "sec20_2", summary="待定系数 / 常数变易。")
add("kp20_2_4", "算子法", 4, "sec20_2", summary="D 算子简化求解。")

add("sec20_3", "微分方程组", 3, "ch20", summary="联立的常微分方程。")
add("kp20_3_1", "一阶线性微分方程组", 4, "sec20_3", summary="X' = A(x)X+F(x)。")
add("kp20_3_2", "常系数线性方程组", 4, "sec20_3", summary="X'=AX，特征值解法。")
add("kp20_3_3", "矩阵指数解法", 4, "sec20_3", summary="X(t)=e^{At}X(0)。")

add("sec20_4", "存在唯一性与解的延拓", 3, "ch20", summary="一般非线性方程的解性质。")
add("kp20_4_1", "Picard存在唯一性定理", 4, "sec20_4", summary="Lipschitz 条件保证局部唯一解。")
add("kp20_4_2", "Picard迭代", 4, "sec20_4", summary="构造解的逐次逼近。")
add("kp20_4_3", "解的延拓", 4, "sec20_4", summary="向最大存在区间扩展。")
add("kp20_4_4", "解对初值的依赖", 4, "sec20_4", summary="连续性 / 可微性。")

add("sec20_5", "稳定性初步", 3, "ch20", summary="解的长期行为。")
add("kp20_5_1", "平衡点与稳定性", 4, "sec20_5", summary="Liapunov 意义下的稳定。")
add("kp20_5_2", "线性化方法", 4, "sec20_5", summary="特征值符号判定。")


# ===============================================================
# 补充节点（关键经典知识点 + 跨章节高频概念）
# ===============================================================

# 实数与基础（补 ch1）
add("kp1_5_4", "实数公理体系", 4, "sec1_5", summary="域 + 序 + 完备性公理。")
add("kp1_5_5", "Archimedes性质", 4, "sec1_5", summary="实数集中无穷大不存在。")
add("kp1_5_6", "稠密性", 4, "sec1_5", summary="任意两不等实数间有有理数。")

# 数列极限补充
add("kp2_4_3", "极限运算的常用变形", 4, "sec2_4", summary="分子有理化、配方等技巧。")
add("kp2_5_6", "n!与nⁿ的比较", 4, "sec2_5", summary="阶的比较：lnⁿ ≪ nᵏ ≪ aⁿ ≪ n! ≪ nⁿ。")
add("kp2_6_4", "压缩映射不动点", 4, "sec2_6", summary="收敛迭代 xₙ₊₁=φ(xₙ)。")

# 函数极限补充
add("kp3_4_5", "无穷小相乘 vs 无穷大相加", 4, "sec3_4", summary="结构化处理未定式。")
add("kp3_5_5", "常见等价无穷小表", 4, "sec3_5", summary="sin x~x, ln(1+x)~x, 1-cos x~x²/2。")
add("kp3_6_5", "复合连续与极限的换序", 4, "sec3_6", summary="lim f(g(x)) = f(lim g(x)) 的条件。")
add("kp3_8_7", "一致连续的反例", 4, "sec3_8", summary="开区间上 1/x 不一致连续。")

# 导数补充
add("kp4_4_7", "复合函数高阶导数", 4, "sec4_4", summary="Faà di Bruno 公式。")
add("kp4_6_4", "极坐标曲线求导", 4, "sec4_6", summary="ρ=ρ(θ) 的切线。")
add("kp4_7_5", "高阶微分", 4, "sec4_7", summary="d²f = f''(x)dx²，对自变量是常量时成立。")

# 中值定理补充
add("kp5_2_2", "罗尔定理的几何意义", 4, "sec5_2", summary="存在水平切线。")
add("kp5_3_4", "拉格朗日定理证明思路", 4, "sec5_3", summary="构造辅助函数 → 罗尔。")
add("kp5_5_4", "洛必达失效情形", 4, "sec5_5", summary="导数比值不存在不代表原比值不存在。")

# 应用补充
add("kp6_2_5", "极值与最值的区别", 4, "sec6_2", summary="极值是局部，最值是全局。")
add("kp6_4_4", "凸函数的判定", 4, "sec6_4", summary="二阶导数非负 ⇔ 凸。")
add("kp6_4_5", "Jensen不等式", 4, "sec6_4", summary="凸函数的关键不等式。")

# 泰勒补充
add("kp7_3_4", "Taylor公式与L'Hospital的比较", 4, "sec7_3", summary="Taylor 处理含高阶项更稳。")
add("kp7_3_5", "误差估计的两种思路", 4, "sec7_3", summary="Lagrange 余项 vs Cauchy 余项。")

# 不定积分补充
add("kp8_2_5", "Euler代换", 4, "sec8_2", summary="处理 √(ax²+bx+c) 的代换。")
add("kp8_3_3", "递推式分部", 4, "sec8_3", summary="∫sinⁿx dx 等的归约。")
add("kp8_4_4", "实部分式的标准形式", 4, "sec8_4", summary="A/(x-a), Bx+C/(x²+px+q)。")

# 定积分补充
add("kp9_1_6", "Riemann可积的Lebesgue判据", 4, "sec9_1", summary="不连续点测度为零。")
add("kp9_2_7", "积分的Cauchy-Schwarz不等式", 4, "sec9_2", summary="(∫fg)² ≤ ∫f² ∫g²。")
add("kp9_4_4", "数值积分", 4, "sec9_4", summary="Simpson、梯形公式。")

# 应用补充
add("kp10_2_7", "参数方程下的弧长与面积", 4, "sec10_2", summary="x=x(t), y=y(t)。")

# 广义积分补充
add("kp11_3_7", "Abel积分判别详细", 4, "sec11_3", summary="Abel 判别更弱条件示例。")
add("kp11_3_8", "条件收敛的经典例子", 4, "sec11_3", summary="∫₁^∞ sin x / x dx。")

# 微分方程补充
add("kp12_2_7", "Riccati方程", 4, "sec12_2", summary="y'=P+Qy+Ry²，需已知特解。")
add("kp12_4_9", "二阶振动方程", 4, "sec12_4", summary="y''+ω²y=0 的物理意义。")

# 多元微分补充
add("kp14_5_6", "梯度与势函数", 4, "sec14_5", summary="若 F=∇φ 则称 F 为势场。")
add("kp14_6_5", "切空间与法空间", 4, "sec14_6", summary="m 维曲面在点处的切空间。")

# 极值补充
add("kp15_1_8", "实际优化问题（多元）", 4, "sec15_1", summary="带约束的工程优化。")
add("kp15_2_5", "经济学中的Lagrange乘数法", 4, "sec15_2", summary="边际替代率与影子价格。")

# 重积分补充
add("kp16_2_5", "二重积分对称性应用", 4, "sec16_2", summary="奇偶性、轴对称简化计算。")
add("kp16_3_7", "三重积分对称性", 4, "sec16_3", summary="球对称区域用球坐标。")

# 曲线曲面补充
add("kp17_2_5", "环量积分", 4, "sec17_2", summary="沿闭曲线 ∮F·dr。")
add("kp17_3_6", "Green公式的几何应用", 4, "sec17_3", summary="求平面图形面积 ½∮(xdy - ydx)。")
add("kp17_6_4", "高斯公式的物理应用", 4, "sec17_6", summary="电磁学、流体的通量。")
add("kp17_7_5", "Stokes公式与电磁学", 4, "sec17_7", summary="∮E·dl = -dΦ/dt 的数学背景。")

# 级数补充
add("kp18_2_7", "级数收敛速率", 4, "sec18_2", summary="Aitken Δ² 加速等。")
add("kp18_3_7", "Riemann重排定理", 4, "sec18_3", summary="条件收敛级数重排可任意值。")
add("kp18_5_7", "幂级数边界点收敛", 4, "sec18_5", summary="x=±R 处需单独判别。")
add("kp18_6_6", "解析延拓初步", 4, "sec18_6", summary="幂级数定义全纯函数的延拓。")

# Fourier 补充
add("kp19_2_5", "工程信号的Fourier展开", 4, "sec19_2", summary="方波、三角波、锯齿波。")
add("kp19_3_5", "Fourier级数收敛速率", 4, "sec19_3", summary="光滑度决定衰减速率。")

# ODE 进阶补充
add("kp20_4_5", "Gronwall不等式", 4, "sec20_4", summary="估计解的增长。")
add("kp20_5_3", "相平面分析", 4, "sec20_5", summary="二维自治系统的几何法。")
add("kp20_5_4", "极限环", 4, "sec20_5", summary="孤立闭轨。")


# ===============================================================
# 关系（语义边）
# ===============================================================
# 不再单独写 CONTAINS：parent_id 已经表达层级。
# 下面只写 PREREQUISITE_OF / USED_IN / GENERALIZES / SPECIAL_CASE_OF /
# SIMILAR_TO / EASILY_CONFUSED_WITH / RELATED_TO 七类语义关系。

# ---------------- 上册关系 ----------------

# 第 1 章 集合与映射
link("kp1_1_1", "kp1_1_2", "PREREQUISITE_OF", "先有集合定义才能谈集合运算。")
link("kp1_1_1", "kp1_1_3", "PREREQUISITE_OF")
link("kp1_2_1", "kp1_2_2", "PREREQUISITE_OF", "映射定义是讨论分类的前提。")
link("kp1_2_2", "kp1_2_4", "PREREQUISITE_OF", "只有双射才可逆。")
link("kp1_2_1", "kp1_2_3", "PREREQUISITE_OF")
link("kp1_2_1", "kp1_3_1", "GENERALIZES", "函数是映射在 ℝ 上的特例。")
link("kp1_3_1", "kp1_2_1", "SPECIAL_CASE_OF")
link("kp1_3_1", "kp1_3_2", "PREREQUISITE_OF")
link("kp1_3_1", "kp1_3_3", "PREREQUISITE_OF")
link("kp1_3_1", "kp1_3_4", "PREREQUISITE_OF")
link("kp1_3_1", "kp1_3_5", "PREREQUISITE_OF")
link("kp1_3_5", "kp1_3_6", "PREREQUISITE_OF", "单调性保证反函数存在。")
link("kp1_3_3", "kp1_3_7", "USED_IN")
link("kp1_3_4", "kp1_3_7", "USED_IN")
link("kp1_2_4", "kp1_3_6", "SPECIAL_CASE_OF")
link("kp1_4_1", "kp1_4_2", "PREREQUISITE_OF")
link("kp1_4_4", "kp1_4_2", "USED_IN", "对角线方法证明实数不可数。")
link("kp1_5_1", "kp1_5_2", "PREREQUISITE_OF", "界是确界的前置概念。")
link("kp1_5_2", "kp1_5_3", "PREREQUISITE_OF")
link("kp1_5_3", "kp2_7_6", "SIMILAR_TO", "两者是同一公理的两种表述。")
link("kp1_6_1", "kp1_6_2", "PREREQUISITE_OF")
link("kp1_6_3", "kp1_6_4", "GENERALIZES")
link("kp1_6_3", "kp2_2_2", "USED_IN", "证明数列极限时常用不等式做放大。")

# 第 2 章 数列极限
link("kp2_1_1", "kp2_1_2", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_1_3", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_1_4", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_2_1", "PREREQUISITE_OF")
link("kp2_2_2", "kp2_2_1", "USED_IN")
link("kp2_1_2", "kp2_3_1", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_3_2", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_3_3", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_3_4", "PREREQUISITE_OF")
link("kp2_1_2", "kp2_3_5", "PREREQUISITE_OF")
link("kp2_3_4", "kp2_3_3", "SPECIAL_CASE_OF")
link("kp2_4_1", "kp2_4_2", "RELATED_TO")
link("kp2_4_2", "kp2_3_3", "USED_IN", "夹逼用到保序性的思想。")
link("kp2_5_1", "kp2_5_2", "PREREQUISITE_OF")
link("kp2_5_3", "kp2_5_4", "PREREQUISITE_OF")
link("kp2_5_1", "kp2_5_3", "EASILY_CONFUSED_WITH", "无穷小与无穷大易被对偶混淆。")
link("kp2_5_5", "kp5_5_1", "SIMILAR_TO", "Stolz 是数列版洛必达。")
link("kp2_3_2", "kp2_6_1", "USED_IN", "单调有界定理用到有界性。")
link("kp2_6_1", "kp2_6_2", "USED_IN", "证明 e 存在用到单调有界。")
link("kp2_6_2", "kp2_6_3", "RELATED_TO")
link("kp2_7_1", "kp2_7_2", "RELATED_TO", "五大基本定理两两等价。")
link("kp2_7_2", "kp2_7_3", "RELATED_TO")
link("kp2_7_3", "kp2_7_4", "RELATED_TO")
link("kp2_7_1", "kp2_7_5", "USED_IN")
link("kp2_7_2", "kp2_7_5", "USED_IN")
link("kp2_7_3", "kp2_7_5", "USED_IN")
link("kp2_7_4", "kp2_7_5", "USED_IN")
link("kp2_7_6", "kp2_7_5", "USED_IN")
link("kp1_5_3", "kp2_7_6", "SIMILAR_TO")
link("kp2_8_1", "kp2_8_2", "PREREQUISITE_OF")
link("kp2_8_1", "kp2_3_1", "RELATED_TO", "上下极限是极限不存在时的替代刻画。")

# 第 3 章 函数极限与连续
link("kp2_1_2", "kp3_1_2", "GENERALIZES", "函数极限是数列极限的连续版本。")
link("kp3_1_2", "kp2_1_2", "SIMILAR_TO", "ε-δ 与 ε-N 形式平行。")
link("kp3_1_1", "kp3_1_2", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_1_3", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_1_4", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_2_1", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_2_2", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_2_3", "PREREQUISITE_OF")
link("kp3_1_2", "kp3_2_4", "PREREQUISITE_OF")
link("kp3_3_4", "kp3_1_2", "USED_IN", "海涅定理把函数极限化归为数列极限。")
link("kp3_3_4", "kp2_1_2", "USED_IN")
link("kp3_3_1", "kp3_3_2", "PREREQUISITE_OF")
link("kp3_3_1", "kp3_3_3", "PREREQUISITE_OF")
link("kp3_4_1", "kp3_4_2", "RELATED_TO")
link("kp2_4_1", "kp3_4_1", "GENERALIZES")
link("kp2_4_2", "kp3_4_2", "GENERALIZES", "数列夹逼推广到函数版本。")
link("kp3_4_2", "kp2_4_2", "SIMILAR_TO")
link("kp3_4_4", "kp2_6_2", "RELATED_TO", "重要极限 (1+1/x)^x → e 与数列 e 一致。")
link("kp3_5_1", "kp3_5_2", "PREREQUISITE_OF")
link("kp3_5_2", "kp3_5_3", "PREREQUISITE_OF")
link("kp3_5_3", "kp3_4_4", "USED_IN", "等价无穷小代换常配合重要极限。")
link("kp3_5_1", "kp3_5_4", "EASILY_CONFUSED_WITH", "无穷小 vs 无穷大对偶易混淆。")
link("kp3_1_2", "kp3_6_1", "PREREQUISITE_OF", "极限是连续性的前提。")
link("kp3_6_1", "kp3_6_2", "PREREQUISITE_OF")
link("kp3_6_2", "kp3_6_3", "PREREQUISITE_OF")
link("kp3_6_1", "kp3_6_4", "PREREQUISITE_OF")
link("kp3_7_1", "kp3_7_2", "PREREQUISITE_OF")
link("kp3_7_2", "kp3_7_3", "RELATED_TO")
link("kp3_7_1", "kp3_7_4", "USED_IN")
link("kp3_7_2", "kp3_7_4", "USED_IN")
link("kp3_6_3", "kp3_8_1", "PREREQUISITE_OF")
link("kp3_6_3", "kp3_8_2", "PREREQUISITE_OF")
link("kp3_6_3", "kp3_8_3", "PREREQUISITE_OF")
link("kp3_8_3", "kp3_8_4", "GENERALIZES", "介值定理是零点定理的推广。")
link("kp3_8_4", "kp3_8_3", "SPECIAL_CASE_OF")
link("kp3_6_3", "kp3_8_5", "PREREQUISITE_OF")
link("kp3_8_5", "kp3_8_6", "PREREQUISITE_OF")
link("kp3_8_5", "kp3_6_1", "EASILY_CONFUSED_WITH", "一致连续 vs 逐点连续是经典易混点。")
link("kp3_8_4", "kp9_2_5", "USED_IN")

# 第 4 章 函数的导数
link("kp3_1_2", "kp4_1_1", "PREREQUISITE_OF", "导数定义本质是极限。")
link("kp4_1_1", "kp4_1_2", "PREREQUISITE_OF")
link("kp4_1_1", "kp4_1_3", "PREREQUISITE_OF")
link("kp4_1_1", "kp4_1_4", "PREREQUISITE_OF")
link("kp3_6_1", "kp4_1_5", "RELATED_TO", "可导比连续强。")
link("kp4_1_5", "kp3_6_1", "USED_IN", "可导推连续证明用到极限性质。")
link("kp4_1_1", "kp4_2_1", "PREREQUISITE_OF")
link("kp4_2_1", "kp4_2_2", "RELATED_TO")
link("kp1_3_4", "kp4_2_2", "USED_IN", "复合是链式法则的对象。")
link("kp1_3_6", "kp4_2_3", "USED_IN")
link("kp4_1_1", "kp4_3_1", "PREREQUISITE_OF")
link("kp4_2_1", "kp4_4_1", "USED_IN")
link("kp4_2_1", "kp4_4_2", "USED_IN")
link("kp4_2_2", "kp4_4_3", "USED_IN")
link("kp4_2_1", "kp4_4_4", "USED_IN")
link("kp4_2_3", "kp4_4_5", "USED_IN")
link("kp4_4_4", "kp4_4_6", "SIMILAR_TO", "三角与双曲函数公式平行。")
link("kp4_1_1", "kp4_5_1", "PREREQUISITE_OF")
link("kp4_5_1", "kp4_5_2", "PREREQUISITE_OF")
link("kp4_5_2", "kp4_5_3", "SPECIAL_CASE_OF")
link("kp4_2_2", "kp4_6_1", "USED_IN", "隐函数求导需要链式法则。")
link("kp4_6_1", "kp4_6_2", "RELATED_TO")
link("kp4_6_1", "kp4_6_3", "RELATED_TO")
link("kp4_1_1", "kp4_7_1", "PREREQUISITE_OF")
link("kp4_7_1", "kp4_7_2", "PREREQUISITE_OF")
link("kp4_7_1", "kp4_7_3", "PREREQUISITE_OF")
link("kp4_7_1", "kp4_7_4", "USED_IN")
link("kp4_1_1", "kp4_7_1", "EASILY_CONFUSED_WITH", "可导 vs 可微在一元情形等价但概念有别。")

# 第 5 章 微分中值定理
link("kp4_1_5", "kp5_1_1", "PREREQUISITE_OF")
link("kp5_1_1", "kp5_1_2", "PREREQUISITE_OF")
link("kp5_1_1", "kp5_2_1", "USED_IN", "罗尔的关键步骤是费马引理。")
link("kp5_2_1", "kp5_3_1", "GENERALIZES", "拉格朗日去掉两端等值条件。")
link("kp5_3_1", "kp5_2_1", "SPECIAL_CASE_OF")
link("kp5_3_1", "kp5_3_2", "USED_IN")
link("kp5_3_1", "kp5_3_3", "USED_IN")
link("kp5_3_1", "kp5_4_1", "GENERALIZES", "柯西涉及两个函数。")
link("kp5_4_1", "kp5_3_1", "SPECIAL_CASE_OF")
link("kp5_4_1", "kp5_5_1", "USED_IN", "洛必达由柯西中值定理推出。")
link("kp5_5_1", "kp5_5_2", "SIMILAR_TO")
link("kp5_5_1", "kp5_5_3", "USED_IN")
link("kp5_5_2", "kp5_5_3", "USED_IN")
link("kp5_5_1", "kp2_5_5", "SIMILAR_TO", "Stolz 是数列版洛必达。")

# 第 6 章 导数的应用
link("kp5_3_1", "kp6_1_1", "USED_IN", "单调性判定用拉格朗日。")
link("kp6_1_1", "kp6_1_2", "RELATED_TO")
link("kp4_1_1", "kp6_2_1", "PREREQUISITE_OF")
link("kp6_2_1", "kp6_2_2", "PREREQUISITE_OF")
link("kp5_1_1", "kp6_2_2", "USED_IN")
link("kp6_1_1", "kp6_2_3", "USED_IN", "第一充分条件就是导数变号。")
link("kp4_5_1", "kp6_2_4", "USED_IN")
link("kp6_2_3", "kp6_2_4", "RELATED_TO")
link("kp3_8_1", "kp6_3_1", "USED_IN", "闭区间最值用到最值定理。")
link("kp6_2_1", "kp6_3_1", "PREREQUISITE_OF")
link("kp6_3_1", "kp6_3_2", "USED_IN")
link("kp6_4_1", "kp6_4_2", "PREREQUISITE_OF")
link("kp6_4_2", "kp6_4_3", "PREREQUISITE_OF")
link("kp4_5_1", "kp6_4_2", "USED_IN")
link("kp6_5_1", "kp6_5_2", "RELATED_TO")
link("kp6_5_1", "kp6_5_3", "RELATED_TO")
link("kp6_1_1", "kp6_6_1", "USED_IN")
link("kp6_2_3", "kp6_6_1", "USED_IN")
link("kp6_4_2", "kp6_6_1", "USED_IN")
link("kp6_5_1", "kp6_6_1", "USED_IN")
link("kp4_5_1", "kp6_7_1", "USED_IN")
link("kp6_7_1", "kp6_7_2", "PREREQUISITE_OF")

# 第 7 章 泰勒公式
link("kp4_5_1", "kp7_1_1", "PREREQUISITE_OF", "泰勒公式建立在高阶导数上。")
link("kp4_5_1", "kp7_1_2", "PREREQUISITE_OF")
link("kp7_1_1", "kp7_1_2", "RELATED_TO")
link("kp7_1_2", "kp7_1_3", "SIMILAR_TO")
link("kp7_1_2", "kp7_1_4", "SIMILAR_TO")
link("kp5_3_1", "kp7_1_2", "GENERALIZES", "Lagrange 余项公式来自反复使用拉格朗日。")
link("kp7_1_1", "kp7_2_1", "SPECIAL_CASE_OF")
link("kp7_2_1", "kp7_2_2", "USED_IN")
link("kp3_5_3", "kp7_3_1", "EASILY_CONFUSED_WITH", "等价无穷小 vs 泰勒展开易混。")
link("kp7_2_2", "kp7_3_1", "USED_IN")
link("kp7_1_2", "kp7_3_2", "USED_IN")
link("kp7_1_1", "kp7_3_3", "USED_IN")
link("kp6_2_4", "kp7_3_3", "GENERALIZES", "二阶判定的高阶版本。")

# 第 8 章 不定积分
link("kp4_1_1", "kp8_1_1", "PREREQUISITE_OF", "原函数定义涉及导数。")
link("kp8_1_1", "kp8_1_2", "PREREQUISITE_OF")
link("kp8_1_2", "kp8_1_3", "PREREQUISITE_OF")
link("kp4_4_1", "kp8_1_4", "USED_IN", "基本积分公式由导数公式倒推。")
link("kp4_4_2", "kp8_1_4", "USED_IN")
link("kp4_4_3", "kp8_1_4", "USED_IN")
link("kp4_4_4", "kp8_1_4", "USED_IN")
link("kp4_4_5", "kp8_1_4", "USED_IN")
link("kp8_1_2", "kp8_1_5", "PREREQUISITE_OF")
link("kp4_2_2", "kp8_2_1", "USED_IN", "凑微分本质是反向链式。")
link("kp8_2_1", "kp8_2_2", "RELATED_TO")
link("kp8_2_2", "kp8_2_3", "SPECIAL_CASE_OF")
link("kp8_2_2", "kp8_2_4", "SPECIAL_CASE_OF")
link("kp4_2_1", "kp8_3_1", "USED_IN", "分部积分由乘积求导反推。")
link("kp8_3_1", "kp8_3_2", "USED_IN")
link("kp8_4_1", "kp8_4_2", "RELATED_TO")
link("kp8_4_1", "kp8_4_3", "RELATED_TO")

# 第 9 章 定积分
link("kp2_1_2", "kp9_1_1", "USED_IN", "Riemann 和取极限。")
link("kp9_1_1", "kp9_1_2", "PREREQUISITE_OF")
link("kp9_1_1", "kp9_1_3", "PREREQUISITE_OF")
link("kp9_1_3", "kp9_1_4", "RELATED_TO")
link("kp9_1_1", "kp9_1_5", "PREREQUISITE_OF")
link("kp9_1_5", "kp9_1_4", "USED_IN", "Darboux 上下和判定可积。")
link("kp9_1_1", "kp9_2_1", "PREREQUISITE_OF")
link("kp9_2_1", "kp9_2_2", "RELATED_TO")
link("kp9_2_2", "kp9_2_3", "RELATED_TO")
link("kp9_2_3", "kp9_2_4", "USED_IN")
link("kp9_2_4", "kp9_2_5", "USED_IN")
link("kp9_2_5", "kp9_2_6", "GENERALIZES")
link("kp9_2_6", "kp9_2_5", "SPECIAL_CASE_OF")
link("kp3_8_4", "kp9_2_5", "USED_IN", "积分中值定理用介值定理。")
link("kp8_1_1", "kp9_3_1", "PREREQUISITE_OF")
link("kp9_3_1", "kp9_3_2", "PREREQUISITE_OF")
link("kp9_3_2", "kp9_3_3", "USED_IN")
link("kp9_3_3", "kp9_3_4", "PREREQUISITE_OF")
link("kp9_3_4", "kp9_4_1", "USED_IN")
link("kp9_3_4", "kp9_4_2", "USED_IN")
link("kp8_2_1", "kp9_4_1", "GENERALIZES")
link("kp8_3_1", "kp9_4_2", "GENERALIZES")
link("kp1_3_5", "kp9_4_3", "USED_IN")

# 第 10 章 定积分的应用
link("kp9_1_1", "kp10_1_1", "RELATED_TO", "微元法是定积分定义的工程化表述。")
link("kp10_1_1", "kp10_2_1", "USED_IN")
link("kp10_1_1", "kp10_2_2", "USED_IN")
link("kp1_6_2", "kp10_2_2", "PREREQUISITE_OF")
link("kp10_1_1", "kp10_2_3", "USED_IN")
link("kp10_2_3", "kp10_2_4", "GENERALIZES", "已知截面积是更一般的体积公式。")
link("kp10_1_1", "kp10_2_5", "USED_IN")
link("kp4_1_1", "kp10_2_5", "USED_IN", "弧长用导数。")
link("kp10_2_5", "kp10_2_6", "RELATED_TO")
link("kp10_1_1", "kp10_3_1", "USED_IN")
link("kp10_1_1", "kp10_3_2", "USED_IN")
link("kp10_1_1", "kp10_3_3", "USED_IN")
link("kp10_1_1", "kp10_3_4", "USED_IN")

# 第 11 章 广义积分
link("kp9_1_1", "kp11_1_1", "GENERALIZES")
link("kp11_1_1", "kp11_1_2", "PREREQUISITE_OF")
link("kp11_1_2", "kp11_1_3", "USED_IN")
link("kp11_1_3", "kp11_1_4", "GENERALIZES")
link("kp11_1_4", "kp11_1_3", "SPECIAL_CASE_OF")
link("kp11_1_5", "kp18_1_6", "SIMILAR_TO", "p积分与p级数判别完全平行。")
link("kp11_1_5", "kp11_1_3", "USED_IN")
link("kp11_1_1", "kp11_2_1", "SIMILAR_TO", "无穷限与瑕积分都是极限定义。")
link("kp11_2_1", "kp11_2_2", "USED_IN")
link("kp11_2_3", "kp11_2_2", "USED_IN")
link("kp11_2_3", "kp11_1_5", "EASILY_CONFUSED_WITH", "瑕点 p<1 vs 无穷限 p>1，方向相反易混。")
link("kp11_3_1", "kp11_3_2", "EASILY_CONFUSED_WITH", "绝对收敛 vs 条件收敛是经典考点。")
link("kp11_3_3", "kp11_3_4", "SIMILAR_TO")
link("kp11_3_3", "kp18_3_5", "SIMILAR_TO", "Abel 判别有积分版与级数版。")
link("kp11_3_4", "kp18_3_6", "SIMILAR_TO", "Dirichlet 判别有积分版与级数版。")
link("kp11_3_5", "kp11_3_6", "RELATED_TO", "Γ与B函数密切相关。")

# 第 12 章 微分方程
link("kp4_1_1", "kp12_1_1", "PREREQUISITE_OF")
link("kp12_1_1", "kp12_1_2", "PREREQUISITE_OF")
link("kp12_1_1", "kp12_1_3", "PREREQUISITE_OF")
link("kp12_1_3", "kp12_1_4", "PREREQUISITE_OF")
link("kp12_2_1", "kp12_2_2", "RELATED_TO")
link("kp12_2_2", "kp12_2_3", "RELATED_TO")
link("kp12_2_3", "kp12_2_4", "USED_IN")
link("kp12_2_3", "kp12_2_5", "RELATED_TO")
link("kp12_2_5", "kp12_2_3", "SPECIAL_CASE_OF", "z=y^{1-n} 化为线性。")
link("kp12_2_6", "kp12_2_3", "EASILY_CONFUSED_WITH", "全微分 vs 一阶线性形式相似。")
link("kp12_3_1", "kp12_3_2", "RELATED_TO")
link("kp12_3_2", "kp12_3_3", "SIMILAR_TO")
link("kp12_4_1", "kp12_4_2", "PREREQUISITE_OF")
link("kp12_4_2", "kp12_4_3", "USED_IN")
link("kp12_4_2", "kp12_4_4", "PREREQUISITE_OF")
link("kp12_4_4", "kp12_4_5", "RELATED_TO")
link("kp12_4_5", "kp12_4_6", "PREREQUISITE_OF")
link("kp12_4_6", "kp12_4_7", "RELATED_TO")
link("kp12_4_7", "kp12_4_6", "GENERALIZES")
link("kp12_4_5", "kp12_4_8", "RELATED_TO")
link("kp12_4_8", "kp12_4_5", "SPECIAL_CASE_OF", "Euler 方程换元后变常系数。")


# ---------------- 跨章节关系（上册内部强联系）----------------
link("kp1_5_3", "kp9_1_4", "USED_IN", "确界原理用于证明可积性。")
link("kp2_7_4", "kp3_8_6", "USED_IN", "Heine-Borel 是 Cantor 定理的关键。")
link("kp3_8_2", "kp9_1_4", "USED_IN")
link("kp5_3_1", "kp9_3_4", "USED_IN", "证明 N-L 公式用拉格朗日。")
link("kp7_2_2", "kp18_6_4", "GENERALIZES", "Maclaurin 展开发展为幂级数展开。")
link("kp8_3_1", "kp17_3_5", "USED_IN", "找原函数也用分部思想。")
link("kp4_1_1", "kp14_1_1", "GENERALIZES", "偏导是导数在多元的推广。")


# ---------------- 下册关系 ----------------

# 第 13 章 多元函数极限与连续
link("kp13_1_1", "kp13_1_2", "PREREQUISITE_OF")
link("kp13_1_2", "kp13_1_3", "PREREQUISITE_OF")
link("kp13_1_3", "kp13_1_4", "PREREQUISITE_OF")
link("kp13_1_4", "kp13_1_5", "PREREQUISITE_OF")
link("kp13_1_5", "kp13_1_6", "PREREQUISITE_OF")
link("kp13_1_5", "kp13_1_7", "RELATED_TO")
link("kp13_1_5", "kp13_1_8", "PREREQUISITE_OF")
link("kp13_1_1", "kp13_2_1", "PREREQUISITE_OF")
link("kp1_3_1", "kp13_2_1", "GENERALIZES")
link("kp13_2_1", "kp1_3_1", "SPECIAL_CASE_OF")
link("kp13_2_1", "kp13_2_2", "PREREQUISITE_OF")
link("kp13_2_1", "kp13_2_3", "PREREQUISITE_OF")
link("kp3_1_2", "kp13_3_1", "GENERALIZES", "二重极限是函数极限的多变量推广。")
link("kp13_3_1", "kp3_1_2", "SPECIAL_CASE_OF")
link("kp13_3_1", "kp13_3_2", "PREREQUISITE_OF")
link("kp13_3_1", "kp13_3_3", "USED_IN")
link("kp13_3_1", "kp13_3_4", "EASILY_CONFUSED_WITH", "二重极限 vs 累次极限。")
link("kp13_3_4", "kp13_3_5", "PREREQUISITE_OF")
link("kp13_3_1", "kp13_4_1", "PREREQUISITE_OF")
link("kp3_6_1", "kp13_4_1", "GENERALIZES")
link("kp13_4_1", "kp3_6_1", "SPECIAL_CASE_OF")
link("kp3_7_1", "kp13_4_2", "GENERALIZES")
link("kp3_8_1", "kp13_4_3", "GENERALIZES")
link("kp3_8_4", "kp13_4_3", "GENERALIZES")
link("kp3_8_5", "kp13_4_3", "GENERALIZES")

# 第 14 章 多元微分学
link("kp4_1_1", "kp14_1_1", "GENERALIZES")
link("kp14_1_1", "kp4_1_1", "SPECIAL_CASE_OF")
link("kp14_1_1", "kp14_1_2", "PREREQUISITE_OF")
link("kp14_1_1", "kp14_1_3", "PREREQUISITE_OF")
link("kp14_1_1", "kp14_1_4", "PREREQUISITE_OF")
link("kp4_5_1", "kp14_1_4", "GENERALIZES")
link("kp14_1_4", "kp14_1_5", "PREREQUISITE_OF")
link("kp4_7_1", "kp14_2_1", "GENERALIZES")
link("kp14_2_1", "kp14_2_2", "PREREQUISITE_OF")
link("kp14_2_2", "kp14_2_3", "PREREQUISITE_OF")
link("kp14_2_3", "kp14_2_4", "RELATED_TO")
link("kp14_2_2", "kp14_2_5", "PREREQUISITE_OF")
link("kp14_1_1", "kp14_2_2", "EASILY_CONFUSED_WITH", "可偏导 vs 可微在多元下不再等价！经典易混点。")
link("kp14_2_2", "kp14_1_1", "EASILY_CONFUSED_WITH")
link("kp4_7_3", "kp14_2_6", "GENERALIZES")
link("kp4_2_2", "kp14_3_1", "GENERALIZES", "链式法则由一元推广到多元。")
link("kp14_3_1", "kp14_3_2", "RELATED_TO")
link("kp14_3_1", "kp14_3_3", "RELATED_TO")
link("kp14_3_1", "kp14_4_1", "USED_IN")
link("kp4_6_1", "kp14_4_1", "GENERALIZES")
link("kp14_4_1", "kp14_4_2", "GENERALIZES")
link("kp14_4_2", "kp14_4_3", "GENERALIZES")
link("kp14_4_3", "kp14_4_4", "USED_IN")
link("kp14_2_2", "kp14_5_1", "PREREQUISITE_OF")
link("kp14_5_1", "kp14_5_2", "PREREQUISITE_OF")
link("kp14_5_2", "kp14_5_3", "PREREQUISITE_OF")
link("kp14_5_3", "kp14_5_4", "PREREQUISITE_OF")
link("kp14_5_3", "kp14_5_5", "RELATED_TO")
link("kp14_3_1", "kp14_6_1", "USED_IN")
link("kp14_6_1", "kp14_6_2", "PREREQUISITE_OF")
link("kp14_2_2", "kp14_6_3", "USED_IN")
link("kp14_6_3", "kp14_6_4", "PREREQUISITE_OF")
link("kp14_5_5", "kp14_6_4", "RELATED_TO", "梯度方向就是法向。")

# 第 15 章 多元微分应用
link("kp14_1_1", "kp15_1_1", "PREREQUISITE_OF")
link("kp6_2_1", "kp15_1_1", "GENERALIZES")
link("kp15_1_1", "kp15_1_2", "PREREQUISITE_OF")
link("kp5_1_1", "kp15_1_2", "GENERALIZES")
link("kp15_1_2", "kp15_1_3", "PREREQUISITE_OF")
link("kp15_1_3", "kp15_1_4", "RELATED_TO")
link("kp14_1_5", "kp15_1_4", "USED_IN")
link("kp15_1_4", "kp15_1_5", "USED_IN")
link("kp6_2_4", "kp15_1_5", "GENERALIZES")
link("kp15_1_5", "kp15_1_6", "RELATED_TO")
link("kp15_1_5", "kp15_1_7", "USED_IN")
link("kp15_1_1", "kp15_2_1", "GENERALIZES")
link("kp15_2_1", "kp15_2_2", "PREREQUISITE_OF")
link("kp14_5_3", "kp15_2_2", "USED_IN")
link("kp15_2_2", "kp15_2_3", "GENERALIZES")
link("kp15_2_2", "kp15_2_4", "RELATED_TO")
link("kp7_1_1", "kp15_3_1", "GENERALIZES")
link("kp15_3_1", "kp7_1_1", "SPECIAL_CASE_OF")
link("kp15_3_1", "kp15_3_2", "PREREQUISITE_OF")
link("kp15_3_1", "kp15_3_3", "USED_IN")
link("kp15_1_5", "kp15_3_3", "RELATED_TO")

# 第 16 章 重积分
link("kp9_1_1", "kp16_1_1", "GENERALIZES", "二重积分是定积分到平面区域的推广。")
link("kp16_1_1", "kp9_1_1", "SPECIAL_CASE_OF")
link("kp16_1_1", "kp16_1_2", "PREREQUISITE_OF")
link("kp9_2_1", "kp16_1_3", "GENERALIZES")
link("kp9_2_5", "kp16_1_4", "GENERALIZES")
link("kp16_1_1", "kp16_2_1", "USED_IN")
link("kp16_2_1", "kp16_2_2", "RELATED_TO")
link("kp16_2_1", "kp16_2_3", "RELATED_TO")
link("kp1_6_2", "kp16_2_3", "USED_IN")
link("kp16_2_3", "kp16_2_4", "SPECIAL_CASE_OF")
link("kp16_1_1", "kp16_3_1", "GENERALIZES")
link("kp16_3_1", "kp16_1_1", "SPECIAL_CASE_OF")
link("kp16_1_3", "kp16_3_2", "SIMILAR_TO")
link("kp16_3_1", "kp16_3_3", "USED_IN")
link("kp16_3_3", "kp16_3_4", "RELATED_TO")
link("kp16_3_3", "kp16_3_5", "RELATED_TO")
link("kp16_3_4", "kp16_3_5", "SIMILAR_TO")
link("kp16_2_4", "kp16_3_6", "GENERALIZES")
link("kp16_3_4", "kp16_3_6", "SPECIAL_CASE_OF")
link("kp16_3_5", "kp16_3_6", "SPECIAL_CASE_OF")
link("kp16_1_1", "kp16_4_1", "USED_IN")
link("kp10_2_6", "kp16_4_1", "GENERALIZES")
link("kp16_3_1", "kp16_4_2", "USED_IN")
link("kp10_2_4", "kp16_4_2", "GENERALIZES")
link("kp16_1_1", "kp16_4_3", "USED_IN")
link("kp10_3_4", "kp16_4_3", "GENERALIZES")
link("kp16_1_1", "kp16_4_4", "USED_IN")
link("kp16_3_1", "kp16_4_5", "USED_IN")
link("kp10_3_3", "kp16_4_5", "GENERALIZES")

# 第 17 章 曲线曲面积分
link("kp9_1_1", "kp17_1_1", "GENERALIZES", "把积分搬到曲线上。")
link("kp10_2_5", "kp17_1_1", "RELATED_TO", "弧长就是 ∫ds。")
link("kp17_1_1", "kp17_1_2", "PREREQUISITE_OF")
link("kp17_1_1", "kp17_1_3", "USED_IN")
link("kp17_1_3", "kp17_1_4", "USED_IN")
link("kp17_1_1", "kp17_2_1", "EASILY_CONFUSED_WITH", "第一型 vs 第二型曲线积分是核心易混点。")
link("kp17_2_1", "kp17_1_1", "EASILY_CONFUSED_WITH")
link("kp17_2_1", "kp17_2_2", "PREREQUISITE_OF")
link("kp17_2_1", "kp17_2_3", "USED_IN")
link("kp17_2_1", "kp17_2_4", "RELATED_TO")
link("kp17_1_1", "kp17_2_4", "RELATED_TO")
link("kp17_2_1", "kp17_3_1", "PREREQUISITE_OF")
link("kp14_1_5", "kp17_3_1", "RELATED_TO")
link("kp17_3_1", "kp17_3_2", "PREREQUISITE_OF")
link("kp17_3_1", "kp17_3_3", "USED_IN")
link("kp17_3_3", "kp17_3_4", "PREREQUISITE_OF")
link("kp17_3_4", "kp17_3_5", "USED_IN")
link("kp12_2_6", "kp17_3_5", "SIMILAR_TO")
link("kp16_1_1", "kp17_4_1", "GENERALIZES")
link("kp9_1_1", "kp17_4_1", "GENERALIZES")
link("kp17_1_1", "kp17_4_1", "SIMILAR_TO", "第一型曲线积分与第一型曲面积分平行。")
link("kp17_4_1", "kp17_4_2", "USED_IN")
link("kp17_4_1", "kp17_4_3", "USED_IN")
link("kp17_4_1", "kp17_5_2", "EASILY_CONFUSED_WITH")
link("kp17_5_1", "kp17_5_2", "PREREQUISITE_OF")
link("kp17_5_2", "kp17_5_3", "USED_IN")
link("kp17_5_2", "kp17_5_4", "RELATED_TO")
link("kp17_4_1", "kp17_5_4", "RELATED_TO")
link("kp17_2_1", "kp17_5_2", "SIMILAR_TO", "第二型曲线积分与第二型曲面积分平行。")
link("kp17_3_1", "kp17_6_1", "GENERALIZES", "Gauss 是 Green 在三维的推广。")
link("kp17_6_1", "kp17_3_1", "SPECIAL_CASE_OF")
link("kp17_5_2", "kp17_6_1", "PREREQUISITE_OF")
link("kp17_6_1", "kp17_6_2", "PREREQUISITE_OF")
link("kp17_6_2", "kp17_6_3", "PREREQUISITE_OF")
link("kp17_3_1", "kp17_7_1", "GENERALIZES", "Stokes 是 Green 的曲面推广。")
link("kp17_7_1", "kp17_3_1", "SPECIAL_CASE_OF")
link("kp17_6_1", "kp17_7_1", "SIMILAR_TO", "Gauss 与 Stokes 是孪生定理。")
link("kp17_7_1", "kp17_7_2", "PREREQUISITE_OF")
link("kp17_7_2", "kp17_7_3", "PREREQUISITE_OF")
link("kp17_7_1", "kp17_7_4", "USED_IN")

# 第 18 章 无穷级数
link("kp2_1_2", "kp18_1_1", "PREREQUISITE_OF", "级数收敛 = 部分和数列收敛。")
link("kp18_1_1", "kp18_1_2", "PREREQUISITE_OF")
link("kp18_1_1", "kp18_1_3", "PREREQUISITE_OF")
link("kp18_1_1", "kp18_1_4", "USED_IN")
link("kp18_1_1", "kp18_1_5", "USED_IN")
link("kp18_1_1", "kp18_1_6", "USED_IN")
link("kp18_1_5", "kp18_1_6", "SPECIAL_CASE_OF", "调和级数是 p=1 的 p级数。")
link("kp18_1_1", "kp18_2_1", "PREREQUISITE_OF")
link("kp18_2_1", "kp18_2_2", "GENERALIZES")
link("kp18_2_2", "kp18_2_1", "SPECIAL_CASE_OF")
link("kp18_2_1", "kp18_2_3", "RELATED_TO")
link("kp18_2_3", "kp18_2_4", "SIMILAR_TO")
link("kp18_2_4", "kp18_2_3", "RELATED_TO")
link("kp11_1_5", "kp18_2_5", "SIMILAR_TO")
link("kp18_2_3", "kp18_2_6", "GENERALIZES")
link("kp18_1_1", "kp18_3_1", "RELATED_TO")
link("kp18_3_2", "kp18_3_3", "EASILY_CONFUSED_WITH", "绝对收敛 vs 条件收敛是核心区分。")
link("kp18_3_2", "kp18_3_4", "USED_IN")
link("kp11_3_3", "kp18_3_5", "SIMILAR_TO")
link("kp11_3_4", "kp18_3_6", "SIMILAR_TO")
link("kp18_3_5", "kp18_3_6", "SIMILAR_TO")
link("kp18_1_1", "kp18_4_1", "PREREQUISITE_OF")
link("kp18_4_1", "kp18_4_2", "PREREQUISITE_OF")
link("kp18_4_2", "kp18_4_3", "PREREQUISITE_OF")
link("kp18_4_3", "kp18_4_4", "USED_IN")
link("kp18_4_3", "kp18_4_5", "PREREQUISITE_OF")
link("kp18_4_3", "kp18_4_6", "USED_IN")
link("kp18_4_3", "kp18_4_7", "USED_IN")
link("kp18_4_3", "kp18_4_8", "USED_IN")
link("kp18_4_3", "kp3_1_2", "EASILY_CONFUSED_WITH", "一致收敛 vs 逐点收敛对偶于一致连续 vs 连续。")
link("kp18_4_1", "kp18_5_1", "SPECIAL_CASE_OF")
link("kp18_5_1", "kp18_5_2", "PREREQUISITE_OF")
link("kp18_5_2", "kp18_5_3", "USED_IN")
link("kp18_5_2", "kp18_5_4", "PREREQUISITE_OF")
link("kp18_4_4", "kp18_5_4", "USED_IN")
link("kp18_5_3", "kp18_5_5", "USED_IN")
link("kp18_5_5", "kp18_5_6", "PREREQUISITE_OF")
link("kp7_1_1", "kp18_6_1", "GENERALIZES", "Taylor 公式延伸到无穷阶就是 Taylor 级数。")
link("kp18_6_1", "kp7_1_1", "RELATED_TO")
link("kp18_6_1", "kp18_6_2", "SPECIAL_CASE_OF")
link("kp7_2_1", "kp18_6_2", "RELATED_TO")
link("kp18_6_1", "kp18_6_3", "PREREQUISITE_OF")
link("kp18_6_3", "kp18_6_4", "USED_IN")
link("kp7_2_2", "kp18_6_4", "GENERALIZES")
link("kp18_6_4", "kp18_6_5", "USED_IN")
link("kp18_5_3", "kp18_6_5", "USED_IN")

# 第 19 章 Fourier 级数
link("kp4_4_4", "kp19_1_1", "PREREQUISITE_OF")
link("kp9_3_4", "kp19_1_2", "USED_IN")
link("kp19_1_1", "kp19_1_2", "PREREQUISITE_OF")
link("kp19_1_2", "kp19_1_3", "USED_IN")
link("kp19_1_3", "kp19_2_1", "USED_IN")
link("kp19_2_1", "kp19_2_2", "GENERALIZES")
link("kp19_2_2", "kp19_2_1", "SPECIAL_CASE_OF")
link("kp19_2_1", "kp19_2_3", "USED_IN")
link("kp19_2_3", "kp19_2_4", "USED_IN")
link("kp18_4_3", "kp19_3_1", "USED_IN")
link("kp19_2_1", "kp19_3_1", "PREREQUISITE_OF")
link("kp19_3_1", "kp19_3_2", "RELATED_TO")
link("kp19_3_2", "kp19_3_3", "PREREQUISITE_OF")
link("kp19_3_1", "kp19_3_4", "RELATED_TO")
link("kp19_2_1", "kp19_4_1", "SIMILAR_TO", "实形式与复形式是同一展开的两面。")
link("kp19_4_1", "kp19_2_1", "SIMILAR_TO")
link("kp19_2_1", "kp19_4_2", "SPECIAL_CASE_OF")
link("kp19_4_1", "kp19_4_3", "PREREQUISITE_OF")
link("kp18_6_1", "kp19_4_2", "SIMILAR_TO", "Taylor 级数与广义 Fourier 都是按基底展开。")
link("kp19_4_2", "kp18_6_1", "SIMILAR_TO")

# 第 20 章 ODE 进阶
link("kp12_4_1", "kp20_1_1", "GENERALIZES")
link("kp20_1_1", "kp12_4_1", "SPECIAL_CASE_OF")
link("kp20_1_1", "kp20_1_2", "PREREQUISITE_OF")
link("kp20_1_2", "kp20_1_3", "USED_IN")
link("kp12_4_3", "kp20_1_4", "GENERALIZES")
link("kp20_1_4", "kp20_1_5", "RELATED_TO")
link("kp12_4_5", "kp20_2_1", "GENERALIZES")
link("kp20_2_1", "kp20_2_2", "PREREQUISITE_OF")
link("kp12_4_6", "kp20_2_3", "GENERALIZES")
link("kp20_2_3", "kp20_2_4", "RELATED_TO")
link("kp20_1_1", "kp20_3_1", "RELATED_TO")
link("kp20_3_1", "kp20_3_2", "SPECIAL_CASE_OF")
link("kp20_3_2", "kp20_3_3", "USED_IN")
link("kp12_1_4", "kp20_4_1", "GENERALIZES", "局部唯一解是初值问题的精细化。")
link("kp20_4_1", "kp20_4_2", "USED_IN")
link("kp20_4_1", "kp20_4_3", "RELATED_TO")
link("kp20_4_1", "kp20_4_4", "RELATED_TO")
link("kp20_4_3", "kp20_5_1", "PREREQUISITE_OF")
link("kp20_5_1", "kp20_5_2", "PREREQUISITE_OF")
link("kp20_3_3", "kp20_5_2", "USED_IN")


# ---------------- 跨册关系（核心承接）----------------
link("kp4_1_1", "kp14_1_1", "GENERALIZES")
link("kp4_7_1", "kp14_2_2", "GENERALIZES")
link("kp4_2_2", "kp14_3_1", "GENERALIZES")
link("kp4_6_1", "kp14_4_1", "GENERALIZES")
link("kp5_1_1", "kp15_1_2", "GENERALIZES")
link("kp6_2_1", "kp15_1_1", "GENERALIZES")
link("kp7_1_1", "kp15_3_1", "GENERALIZES")
link("kp9_1_1", "kp16_1_1", "GENERALIZES")
link("kp9_1_1", "kp16_3_1", "GENERALIZES")
link("kp9_1_1", "kp17_1_1", "GENERALIZES")
link("kp9_1_1", "kp17_4_1", "GENERALIZES")
link("kp9_3_4", "kp17_3_1", "GENERALIZES", "N-L 是 Green 的一维原型。")
link("kp9_3_4", "kp17_6_1", "RELATED_TO")
link("kp9_3_4", "kp17_7_1", "RELATED_TO")
link("kp10_2_5", "kp17_1_3", "USED_IN")
link("kp10_2_6", "kp16_4_1", "GENERALIZES")
link("kp11_1_5", "kp18_1_6", "SIMILAR_TO")
link("kp7_2_2", "kp18_6_4", "GENERALIZES")
link("kp12_4_1", "kp20_1_1", "GENERALIZES")
link("kp12_2_3", "kp20_1_1", "RELATED_TO")
link("kp4_5_1", "kp14_1_4", "GENERALIZES")
link("kp4_5_3", "kp14_3_3", "RELATED_TO")
link("kp1_5_3", "kp13_1_7", "USED_IN", "ℝⁿ 紧致性来自完备性。")
link("kp2_7_2", "kp13_1_7", "GENERALIZES")
link("kp3_8_4", "kp17_3_3", "USED_IN")
link("kp9_2_5", "kp16_1_4", "GENERALIZES")


# ---------------- 补充关系（提升密度 + 接入新增节点）----------------

# 实数公理体系
link("kp1_5_3", "kp1_5_4", "RELATED_TO")
link("kp1_5_4", "kp1_5_5", "PREREQUISITE_OF")
link("kp1_5_4", "kp1_5_6", "PREREQUISITE_OF")
link("kp1_5_5", "kp1_5_6", "USED_IN")
link("kp1_5_4", "kp2_7_5", "RELATED_TO", "实数公理对应五大基本定理。")
link("kp1_5_6", "kp1_4_2", "RELATED_TO")

# 数列阶比较
link("kp2_4_3", "kp2_4_1", "USED_IN")
link("kp2_5_6", "kp2_5_3", "USED_IN")
link("kp2_5_6", "kp3_5_2", "SIMILAR_TO", "数列阶 vs 函数无穷小阶。")
link("kp2_6_4", "kp2_6_1", "USED_IN")
link("kp2_6_4", "kp20_4_2", "SIMILAR_TO", "压缩映射就是 Picard 迭代的核心。")

# 函数极限补充
link("kp3_4_5", "kp3_4_1", "USED_IN")
link("kp3_5_3", "kp3_5_5", "PREREQUISITE_OF")
link("kp3_5_5", "kp3_4_4", "RELATED_TO")
link("kp3_5_5", "kp7_2_2", "EASILY_CONFUSED_WITH", "等价无穷小 vs Maclaurin 展开易混。")
link("kp3_6_5", "kp3_4_3", "RELATED_TO")
link("kp3_8_7", "kp3_8_5", "RELATED_TO", "反例显示一致连续的必要性。")
link("kp3_8_7", "kp3_8_6", "EASILY_CONFUSED_WITH")

# 导数补充
link("kp4_5_3", "kp4_4_7", "GENERALIZES")
link("kp4_4_7", "kp4_5_3", "SPECIAL_CASE_OF")
link("kp4_6_3", "kp4_6_4", "SIMILAR_TO")
link("kp4_7_1", "kp4_7_5", "GENERALIZES")
link("kp4_7_5", "kp4_7_1", "SPECIAL_CASE_OF")

# 中值定理补充
link("kp5_2_1", "kp5_2_2", "PREREQUISITE_OF")
link("kp5_3_1", "kp5_3_4", "RELATED_TO")
link("kp5_5_1", "kp5_5_4", "RELATED_TO")
link("kp5_5_4", "kp5_5_1", "EASILY_CONFUSED_WITH")

# 应用补充
link("kp6_2_1", "kp6_2_5", "PREREQUISITE_OF")
link("kp6_3_1", "kp6_2_5", "RELATED_TO")
link("kp6_4_2", "kp6_4_4", "RELATED_TO")
link("kp6_4_4", "kp6_4_5", "USED_IN")
link("kp6_4_5", "kp9_2_7", "RELATED_TO", "Jensen 与积分不等式同源。")

# Taylor 补充
link("kp7_3_1", "kp7_3_4", "RELATED_TO")
link("kp7_1_2", "kp7_3_5", "USED_IN")
link("kp7_1_3", "kp7_3_5", "USED_IN")

# 不定积分补充
link("kp8_2_3", "kp8_2_5", "SIMILAR_TO")
link("kp8_3_2", "kp8_3_3", "USED_IN")
link("kp8_4_1", "kp8_4_4", "PREREQUISITE_OF")

# 定积分补充
link("kp9_1_4", "kp9_1_6", "GENERALIZES")
link("kp9_1_6", "kp9_1_4", "SPECIAL_CASE_OF")
link("kp9_2_4", "kp9_2_7", "RELATED_TO")
link("kp9_2_7", "kp6_4_5", "SIMILAR_TO")
link("kp9_3_4", "kp9_4_4", "USED_IN")

# 定积分应用
link("kp10_2_5", "kp10_2_7", "GENERALIZES")
link("kp10_2_7", "kp4_6_3", "USED_IN")

# 广义积分补充
link("kp11_3_3", "kp11_3_7", "RELATED_TO")
link("kp11_3_2", "kp11_3_8", "USED_IN", "经典例子展示条件收敛。")

# 微分方程补充
link("kp12_2_5", "kp12_2_7", "SIMILAR_TO", "都是化非线性为线性。")
link("kp12_4_5", "kp12_4_9", "USED_IN", "二阶振动用特征根 ±ωi。")

# 多元微分补充
link("kp14_5_3", "kp14_5_6", "PREREQUISITE_OF")
link("kp14_5_6", "kp17_3_4", "RELATED_TO", "势函数与路径无关条件等价。")
link("kp14_6_3", "kp14_6_5", "RELATED_TO")
link("kp14_6_5", "kp13_1_8", "RELATED_TO")

# 极值补充
link("kp15_1_7", "kp15_1_8", "RELATED_TO")
link("kp15_2_2", "kp15_2_5", "USED_IN")
link("kp15_1_8", "kp6_3_2", "GENERALIZES")

# 重积分补充
link("kp9_4_3", "kp16_2_5", "GENERALIZES")
link("kp16_2_5", "kp9_4_3", "SPECIAL_CASE_OF")
link("kp16_2_5", "kp16_3_7", "SIMILAR_TO")
link("kp16_3_7", "kp16_3_5", "USED_IN")

# 曲线曲面补充
link("kp17_2_1", "kp17_2_5", "SPECIAL_CASE_OF", "环量是闭曲线上的第二型积分。")
link("kp17_3_1", "kp17_3_6", "USED_IN")
link("kp17_6_1", "kp17_6_4", "USED_IN")
link("kp17_7_1", "kp17_7_5", "USED_IN")

# 级数补充
link("kp18_2_3", "kp18_2_7", "RELATED_TO")
link("kp18_3_4", "kp18_3_7", "RELATED_TO", "Riemann 重排展示条件收敛的脆弱性。")
link("kp18_3_3", "kp18_3_7", "USED_IN")
link("kp18_5_4", "kp18_5_7", "RELATED_TO")
link("kp18_6_4", "kp18_6_6", "RELATED_TO")
link("kp18_6_6", "kp18_5_1", "RELATED_TO")

# Fourier 补充
link("kp19_2_1", "kp19_2_5", "USED_IN")
link("kp19_3_1", "kp19_3_5", "RELATED_TO")
link("kp19_3_4", "kp19_2_5", "USED_IN", "方波的 Gibbs 现象。")

# ODE 进阶补充
link("kp20_4_1", "kp20_4_5", "USED_IN", "Gronwall 是 Picard 唯一性的核心估计。")
link("kp20_5_2", "kp20_5_3", "PREREQUISITE_OF")
link("kp20_5_3", "kp20_5_4", "PREREQUISITE_OF")
link("kp20_3_3", "kp20_5_3", "USED_IN")


# ---------------- 同类对偶关系（补充易混与类比）----------------
# 一致 vs 逐点 系列
link("kp3_8_5", "kp18_4_3", "SIMILAR_TO", "都是「一致」概念。")
link("kp3_8_5", "kp19_3_1", "RELATED_TO")
link("kp18_4_3", "kp19_3_1", "RELATED_TO")

# Cauchy 系列
link("kp2_7_3", "kp18_4_5", "GENERALIZES", "Cauchy 准则贯穿数列与级数。")
link("kp2_7_3", "kp1_5_4", "RELATED_TO")

# 比较判别系列（积分版、级数版）
link("kp11_1_3", "kp18_2_1", "SIMILAR_TO")
link("kp11_1_4", "kp18_2_2", "SIMILAR_TO")
link("kp11_2_2", "kp18_2_1", "SIMILAR_TO")

# 极限求法对比
link("kp5_5_1", "kp7_3_1", "EASILY_CONFUSED_WITH", "洛必达 vs Taylor 求极限选哪个？")
link("kp7_3_1", "kp5_5_1", "EASILY_CONFUSED_WITH")
link("kp3_5_3", "kp5_5_1", "EASILY_CONFUSED_WITH")
link("kp3_5_3", "kp7_3_1", "EASILY_CONFUSED_WITH")
link("kp3_4_2", "kp5_5_1", "RELATED_TO")
link("kp2_5_5", "kp7_3_1", "RELATED_TO")

# 求导手法对比
link("kp4_2_2", "kp4_6_1", "RELATED_TO")
link("kp4_6_1", "kp4_6_2", "EASILY_CONFUSED_WITH")
link("kp4_6_2", "kp4_6_3", "RELATED_TO")
link("kp14_3_1", "kp14_4_1", "RELATED_TO")

# 多元 vs 一元的对偶
link("kp14_5_1", "kp4_1_1", "GENERALIZES")
link("kp15_1_5", "kp6_2_4", "GENERALIZES")
link("kp16_2_3", "kp1_6_2", "RELATED_TO")

# Taylor 系列贯通
link("kp15_3_1", "kp18_6_1", "RELATED_TO")
link("kp18_6_1", "kp19_4_2", "SIMILAR_TO")

# 收敛判别工具的对偶
link("kp18_2_3", "kp18_2_4", "EASILY_CONFUSED_WITH")
link("kp18_3_1", "kp18_3_2", "RELATED_TO")
link("kp11_3_3", "kp11_3_4", "EASILY_CONFUSED_WITH")

# 微分方程系列
link("kp12_2_3", "kp12_4_2", "RELATED_TO")
link("kp12_4_5", "kp20_2_1", "RELATED_TO")
link("kp12_4_8", "kp20_2_2", "RELATED_TO")

# 几何应用群
link("kp10_2_1", "kp16_4_2", "GENERALIZES")
link("kp10_2_3", "kp16_4_2", "GENERALIZES")
link("kp10_2_6", "kp17_4_3", "RELATED_TO")
link("kp10_3_1", "kp17_2_5", "GENERALIZES", "功推广为环量。")

# 物理量统一
link("kp16_4_4", "kp10_3_4", "RELATED_TO")

# 极坐标 / 柱面 / 球面坐标的连贯
link("kp1_6_1", "kp16_2_3", "PREREQUISITE_OF")

# 单调性与不等式
link("kp6_1_1", "kp1_6_3", "USED_IN", "证不等式常用单调性。")
link("kp6_4_4", "kp1_6_3", "USED_IN")

# 收敛域与定义域
link("kp18_4_1", "kp1_3_1", "RELATED_TO", "和函数的定义域 = 收敛域。")
link("kp18_5_2", "kp18_4_1", "SPECIAL_CASE_OF")

# 高维拓扑
link("kp13_1_5", "kp16_1_1", "PREREQUISITE_OF", "积分域需要可测/有界闭。")
link("kp13_1_8", "kp17_3_2", "PREREQUISITE_OF")

# 隐函数与几何应用
link("kp14_4_2", "kp14_6_3", "USED_IN")
link("kp14_4_3", "kp15_2_2", "RELATED_TO")

# 反函数 / 复合 / 链式系列
link("kp1_2_3", "kp4_2_2", "USED_IN")
link("kp1_3_6", "kp1_2_4", "SPECIAL_CASE_OF")

# 极限 - 连续 - 可微 - 可导 - 可积 链
link("kp9_1_4", "kp9_1_3", "PREREQUISITE_OF")
link("kp3_6_3", "kp9_1_4", "USED_IN", "闭区间连续 ⇒ 可积。")
link("kp14_2_5", "kp14_2_2", "PREREQUISITE_OF")
link("kp14_2_4", "kp14_2_2", "USED_IN")

# 微分方程与多元微分
link("kp14_5_6", "kp12_2_6", "RELATED_TO")

# 函数 - 级数桥梁
link("kp18_6_1", "kp4_5_2", "USED_IN", "Taylor 级数需要任意阶导数。")

# Fourier 与正交分解
link("kp19_1_2", "kp19_4_2", "PREREQUISITE_OF")
link("kp19_4_2", "kp18_4_1", "RELATED_TO")


# ===============================================================
# 输出 JSON
# ===============================================================

def write_json() -> None:
    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "kg.json"

    payload = {
        "course_name": "数学分析（含上下册）",
        "version": "2.0",
        "generated_at": date.today().isoformat(),
        "relation_types": RELATION_TYPES,
        "stats": {
            "node_count": len(NODES),
            "edge_count": len(EDGES),
            "level_distribution": {
                str(level): sum(1 for n in NODES if n["level"] == level)
                for level in sorted({n["level"] for n in NODES})
            },
            "edge_type_distribution": {
                rt["key"]: sum(1 for e in EDGES if e["type"] == rt["key"])
                for rt in RELATION_TYPES
            },
        },
        "nodes": NODES,
        "edges": EDGES,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"写入 {out_path}", file=sys.stderr)
    print(f"节点 {len(NODES)} 个 / 边 {len(EDGES)} 条", file=sys.stderr)
    for level, count in payload["stats"]["level_distribution"].items():
        print(f"  L{level}: {count}", file=sys.stderr)
    print("边类型分布：", file=sys.stderr)
    for rt_key, count in payload["stats"]["edge_type_distribution"].items():
        print(f"  {rt_key}: {count}", file=sys.stderr)


if __name__ == "__main__":
    write_json()
