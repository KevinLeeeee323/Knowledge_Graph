# KG 增强与 KG-grounded 问答工作流

这部分对应项目任务中的“你：Pipeline & Reasoning”。

## 1. 生成第一批候选关系

先开 Ollama，并确认本地有模型，例如 `qwen2.5:7b` 或你的 Qwen 9B 模型。

```bash
python3 code/kg_workflow.py generate-candidates --model qwen2.5:7b --prompt-version v1 --limit 120
```

如果暂时不想调用大模型，可以先跑规则基线：

```bash
python3 code/kg_workflow.py generate-candidates --prompt-version v1 --limit 120 --no-llm
```

输出：

```text
csv_data_annotated/candidate_relations_v1.csv
```

## 2. 导入候选关系给数学同学审核

启动 UI：

```bash
python3 code/annotation_server.py
```

打开：

```text
http://127.0.0.1:8765
```

点击：

```text
导入候选
```

数学同学在 UI 里做：

- accepted / rejected
- 必要时修改关系类型
- 填写人工标签
- 填写错误类型
- 写人工审核说明

## 3. 导出 gold set

在 UI 点击：

```text
导出 Gold Set
```

或命令行：

```bash
python3 code/kg_workflow.py export-gold
```

输出：

```text
csv_data_annotated/gold_set.csv
```

## 4. 用 gold set 生成第二批关系

```bash
python3 code/kg_workflow.py generate-candidates --model qwen2.5:7b --prompt-version v2 --gold-set csv_data_annotated/gold_set.csv --limit 120 --output csv_data_annotated/candidate_relations_v2.csv
```

然后可以导入 v2 候选给数学同学抽样审核。

```bash
python3 code/kg_workflow.py import-candidates csv_data_annotated/candidate_relations_v2.csv
```

## 5. 评估 v1/v2 准确率

```bash
python3 code/kg_workflow.py evaluate-gold --gold-set csv_data_annotated/gold_set.csv
```

输出：

```text
experiments/relation_generation_report.json
```

## 6. 导出增强图谱 CSV

UI 点击：

```text
导出 CSV
```

输出：

```text
csv_data_annotated/annotated_nodes.csv
csv_data_annotated/annotated_relationships.csv
```

## 7. KG-grounded 学习路径/问答 Demo

```bash
python3 code/kg_grounded_demo.py "我学泰勒公式总是不会用" --model qwen2.5:7b
```

这个 demo 会先从图谱中检索相关节点和关系，再把图谱事实作为上下文交给大模型回答。
