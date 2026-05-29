# 知识图谱关系标注工作台

这个工具读取 `csv_data_ori/neo4j_nodes.csv` 和 `csv_data_ori/neo4j_relationships.csv`，在浏览器里进行关系审核、人工新增关系、自定义关系类型和自定义节点管理。原始 CSV 只读，导出结果写入 `csv_data_annotated/`。

## 环境依赖

- Python 3.10 或更新版本
- 现代浏览器：Chrome、Edge、Firefox、Safari 均可
- 不需要安装 npm、Node.js 或额外 Python 第三方库

## macOS / Linux 启动

在项目根目录运行：

```bash
python3 code/annotation_server.py
```

也可以运行：

```bash
sh annotation_ui/start_annotation_ui.sh
```

打开：

```text
http://127.0.0.1:8765
```

## Windows 启动

在项目根目录运行：

```powershell
py code\annotation_server.py
```

如果 `py` 不可用，使用：

```powershell
python code\annotation_server.py
```

也可以双击或运行：

```powershell
annotation_ui\start_annotation_ui.bat
```

然后打开：

```text
http://127.0.0.1:8765
```

## 输出文件

点击页面右上角 `导出 CSV` 后会生成：

```text
csv_data_annotated/annotated_nodes.csv
csv_data_annotated/annotated_relationships.csv
csv_data_annotated/annotation_state.json
```

其中 `annotated_relationships.csv` 会包含原始 `CONTAINS` 关系，以及人工审核通过的增强关系，例如 `PREREQUISITE_OF`、`USED_IN`、`GENERALIZES` 等。

## 保存、撤销和导出

- 页面里的新增关系、审核状态、自定义节点会自动写入 `csv_data_annotated/annotation_state.json`。
- `保存进度` 会额外生成一个时间戳快照，保存在 `csv_data_annotated/snapshots/`。
- `撤销` / `反撤销` 会恢复最近的标注状态，历史记录保存在 `csv_data_annotated/annotation_history.json`。
- `导出 CSV` 用于生成最终可导入 Neo4j 的 CSV，不等同于阶段性保存。

## AI 候选与 Gold Set

- `生成候选`：对当前左侧选中的知识点生成少量规则候选，适合临时补充。
- `导入候选`：导入 `csv_data_annotated/candidate_relations_v1.csv`，这是主工作流中由 `code/kg_workflow.py` 批量生成的候选关系。
- `导出 Gold Set`：把已经审核过的 accepted / rejected 候选导出为 `csv_data_annotated/gold_set.csv`，用于 prompt v2 优化和实验评估。
- 数学审核时建议填写：
  - 审核状态：accepted / rejected
  - 人工标签：如果 AI 标签错了，在这里填正确关系
  - 错误类型：如方向错误、关系类型错误、无真实关系
  - 人工审核说明：简短写数学理由

## 当前限制

- 原始节点和原始关系不会被 UI 修改或删除。
- UI 创建的自定义节点可以编辑和删除。
- 当前候选关系是规则生成，后续可以接 Ollama 或服务器大模型，把 AI 生成的候选关系写入同一套审核流程。
