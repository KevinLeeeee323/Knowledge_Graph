# Knowledge_Graph（BUAA 数学分析知识图谱）

个人项目，可直接在主目录改 + commit + push main，不开 worktree、不走 MR。远端仓库 `KevinLeeeee323/Knowledge_Graph`（GitHub）。

## 项目定位

零数据库的本地静态知识图谱浏览器。数据由 Python 脚本生成静态 JSON，前端纯静态页面加载渲染，无后端、无构建步骤。2026-05-31/06-01 从旧的「Neo4j + Ollama + 标注 UI 闭环」彻底重构为当前形态。

## 架构

- 数据单一真相源：`data/build_kg.py`——用 Python 函数注册节点 + 关系，重复 id / 悬挂引用 / 自环会立刻 raise。运行 `python3 data/build_kg.py` 生成 `data/kg.json`，viewer 通过 `fetch('../data/kg.json')` 加载。
- 知识结构：`数学分析` → 6 大主题领域（实数与极限 / 单变量微分学 / 单变量积分学 / 多变量微分学 / 多变量积分学 / 级数与微分方程）→ 章 → 节 → 知识点。不按教材上下册划分（旧设计已否定）。
- 规模：约 583 节点 / 634 关系；7 种语义关系（PREREQUISITE_OF / USED_IN / GENERALIZES / SPECIAL_CASE_OF / SIMILAR_TO / EASILY_CONFUSED_WITH / RELATED_TO）+ 隐式 CONTAINS（由 parent_id 推导）。
- Viewer：`viewer/index.html` + `styles.css` + `app.js`（vanilla JS + Cytoscape.js CDN，零依赖零构建）。节点为圆角矩形 + 自适应宽度，文字始终包在框内。

## 运行

`./serve.sh`（mac/linux）或 `serve.bat`（windows），内部是 `python3 -m http.server 8000`，访问 http://127.0.0.1:8000/viewer/
