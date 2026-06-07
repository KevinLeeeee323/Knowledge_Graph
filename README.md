# 数学分析知识图谱（BUAA 工科数学分析 · 上下册）

一个零数据库、零构建的本地静态知识图谱浏览器。所有数据收录在 [data/kg.json](data/kg.json) 里：

- 课程：北京航空航天大学 · 工科数学分析（上 + 下）
- 节点：约 580 个（根 → 册 → 章 → 节 → 知识点）
- 关系：约 630 条，覆盖 7 种语义关系（PREREQUISITE_OF / USED_IN / GENERALIZES / SPECIAL_CASE_OF / SIMILAR_TO / EASILY_CONFUSED_WITH / RELATED_TO）

## 快速开始

```bash
./serve.sh           # macOS / Linux
# 或：
serve.bat            # Windows
```

启动后浏览器打开：<http://127.0.0.1:8000/viewer/>

## 你能在浏览器里做什么

- 左侧树：按「数学分析 → 上册 / 下册 → 章 → 节 → 知识点」逐级展开
- 顶部搜索：输入「泰勒公式」「Stokes」「条件收敛」「可微」等任意片段，回车定位
- 中间图：选中节点后立即展示周围 N 跳邻居（默认 2 跳），不同语义关系不同颜色
- 图中边标签：语义关系会显示为中文标签（前置 / 应用于 / 推广 / 特例 / 类比 / 易混淆 / 相关）
- 顶部图例：勾选 / 取消任意语义类型，即时筛选图
- 「显示父子层级」开关：开启后会把 CONTAINS 父子边也画出来（默认关闭，专注于语义关系）
- 右侧详情：节点简介 + 按关系类型分组列出所有邻居，点击邻居即可跳转
- 右侧学习路径助手：基于增强关系自动生成先修补全、推荐路径、应用方向与易混淆/类比提醒

## 学习路径助手

选中任意知识点后，右侧会出现「学习路径助手」。它完全基于 `data/kg.json` 中的增强关系进行确定性分析，不调用 LLM，也不需要后端服务。

- **先补基础**：优先沿 `PREREQUISITE_OF`、`USED_IN`、`GENERALIZES` 的反向关系寻找当前知识点的可能前置。
- **推荐路径**：将前置知识、当前知识点和后续应用串成一条可点击路径。
- **应用方向**：沿 `USED_IN`、`PREREQUISITE_OF`、`SPECIAL_CASE_OF` 寻找学完当前知识点后的应用或后续主题。
- **易混淆 / 类比**：沿 `EASILY_CONFUSED_WITH`、`SIMILAR_TO`、`RELATED_TO` 给出辨析和类比提醒。

当推荐内容较多时，学习路径助手卡片内部会独立滚动，不会撑爆右侧详情栏。

## 想改 / 加节点和关系？

编辑 [data/build_kg.py](data/build_kg.py)，然后重新生成 JSON：

```bash
python3 data/build_kg.py
```

脚本会打印节点 / 关系数和按类型的分布统计，所有引用错误（不存在的 id、自环、重复边）会立刻报错。`data/kg.json` 直接 overwrite。

## 想微调关系中文显示？

图谱边上的中文标签和说明在 [viewer/app.js](viewer/app.js) 顶部的 `RELATION_UI` 中维护：

```js
PREREQUISITE_OF: { label: "前置", desc: "A 是理解 B 的前置知识。" }
```

如果想把「应用于」改成「用于」，或把「前置」改成「先修」，直接改这个表即可。

## 项目结构

```
Knowledge_Graph/
├── README.md
├── 项目任务.md         旧版方案讨论（已转向，见末尾说明）
├── serve.sh / serve.bat
├── data/
│   ├── build_kg.py    主数据源（人类可读 Python）
│   └── kg.json        生成产物（viewer 加载）
└── viewer/
    ├── index.html
    ├── styles.css
    └── app.js         零依赖 vanilla JS + Cytoscape.js（CDN 引入）
```

## 设计取舍

- **JSON 不手写**：build_kg.py 用函数注册节点 / 关系，重复 id、悬挂引用、自环立即抛错；维护成本远低于直接编辑 JSON。
- **不内置 LLM / 不内置标注流程**：项目专注于「呈现一份高质量手写 KG」，不再做 v1/v2 prompt 闭环。
- **零数据库**：Cytoscape.js 通过 CDN 引入即可在浏览器渲染，无需 Neo4j 与任何后端服务。
- **浅色阅读界面**：保持课程资料浏览的清爽感；颜色编码 7 种关系类型，肉眼易辨。

## 验证

```bash
python3 -c "import json; data = json.load(open('data/kg.json')); print(data['stats'])"
```

启动 server 后，搜索「泰勒公式」/「Stokes 公式」/「条件收敛」三个查询点，应能看到合理的局部子图、中文边标签、按类型分组的邻居，以及右侧学习路径助手。
