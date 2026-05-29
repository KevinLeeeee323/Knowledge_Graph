from __future__ import annotations

import argparse
import csv
import json
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "csv_data_ori"
OUTPUT_DIR = ROOT / "csv_data_annotated"

NODES_CSV = OUTPUT_DIR / "annotated_nodes.csv"
REL_CSV = OUTPUT_DIR / "annotated_relationships.csv"
STATE_JSON = OUTPUT_DIR / "annotation_state.json"
FALLBACK_NODES_CSV = SOURCE_DIR / "neo4j_nodes.csv"
FALLBACK_REL_CSV = SOURCE_DIR / "neo4j_relationships.csv"

NODE_ID = "node_id:ID"
NODE_NAME = "name"
NODE_LEVEL = "level:int"
NODE_PARENT = "parent_id"

REL_START = ":START_ID"
REL_END = ":END_ID"
REL_TYPE = ":TYPE"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_graph(use_annotations: bool = True) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    nodes_path = NODES_CSV if NODES_CSV.exists() else FALLBACK_NODES_CSV
    rel_path = REL_CSV if REL_CSV.exists() else FALLBACK_REL_CSV
    nodes = read_csv(nodes_path)
    relationships = read_csv(rel_path)
    if use_annotations:
        relationships = merge_accepted_annotations(relationships)
    return nodes, relationships


def merge_accepted_annotations(relationships: list[dict[str, str]]) -> list[dict[str, str]]:
    if not STATE_JSON.exists():
        return relationships
    with STATE_JSON.open("r", encoding="utf-8") as file:
        state = json.load(file)
    merged = list(relationships)
    existing = {
        (rel.get(REL_START, ""), rel.get(REL_END, ""), rel.get(REL_TYPE, ""))
        for rel in merged
    }
    for item in state.get("annotations", []):
        if item.get("status") != "accepted":
            continue
        rel_type = item.get("human_label") or item.get("type", "")
        if not rel_type or rel_type == "NO_RELATION":
            continue
        key = (item.get("start_id", ""), item.get("end_id", ""), rel_type)
        if key in existing:
            continue
        existing.add(key)
        merged.append(
            {
                REL_START: item.get("start_id", ""),
                REL_END: item.get("end_id", ""),
                REL_TYPE: rel_type,
                "status": "accepted",
                "source": item.get("source", "annotation_state"),
                "confidence": item.get("confidence", ""),
                "note": item.get("human_note") or item.get("note", ""),
            }
        )
    return merged


def score_node(question: str, node: dict[str, str]) -> int:
    name = node.get(NODE_NAME, "")
    score = 0
    if name and name in question:
        score += 10 + len(name)
    for char in set(name):
        if char in question and char.strip():
            score += 1
    for keyword in ["极限", "连续", "导数", "微分", "积分", "泰勒", "定理", "法则", "函数", "数列"]:
        if keyword in question and keyword in name:
            score += 6
    return score


def retrieve_subgraph(question: str, limit: int = 6, use_annotations: bool = True) -> dict:
    nodes, relationships = load_graph(use_annotations)
    node_by_id = {node[NODE_ID]: node for node in nodes}
    ranked = sorted(nodes, key=lambda node: score_node(question, node), reverse=True)
    seeds = [node for node in ranked if score_node(question, node) > 0][:limit]
    seed_ids = {node[NODE_ID] for node in seeds}
    related_edges = []
    related_node_ids = set(seed_ids)

    useful_types = {
        "CONTAINS",
        "PREREQUISITE_OF",
        "USED_IN",
        "GENERALIZES",
        "SPECIAL_CASE_OF",
        "SIMILAR_TO",
        "EASILY_CONFUSED_WITH",
        "RELATED_TO",
    }
    for rel in relationships:
        start_id = rel.get(REL_START, "")
        end_id = rel.get(REL_END, "")
        rel_type = rel.get(REL_TYPE, "")
        if rel_type not in useful_types:
            continue
        if start_id in seed_ids or end_id in seed_ids:
            related_edges.append(rel)
            related_node_ids.add(start_id)
            related_node_ids.add(end_id)
        if len(related_edges) >= 45:
            break

    return {
        "seeds": seeds,
        "nodes": [node_by_id[node_id] for node_id in related_node_ids if node_id in node_by_id],
        "edges": related_edges,
        "node_by_id": node_by_id,
    }


def graph_context(subgraph: dict) -> str:
    node_by_id = subgraph["node_by_id"]
    seed_lines = seed_context_lines(subgraph)
    edge_lines = edge_context_lines(subgraph, node_by_id)
    return "\n".join(
        [
            "命中的知识点：",
            *(seed_lines or ["- 无明确命中"]),
            "",
            "图谱事实：",
            *(edge_lines or ["- 无增强关系，仅可使用命中节点。"]),
        ]
    )


def seed_context_lines(subgraph: dict) -> list[str]:
    return [f"- {node.get(NODE_NAME, '')} (L{node.get(NODE_LEVEL, '?')})" for node in subgraph["seeds"]]


def edge_context_lines(subgraph: dict, node_by_id: dict[str, dict[str, str]] | None = None) -> list[str]:
    node_by_id = node_by_id or subgraph["node_by_id"]
    lines = []
    for rel in subgraph["edges"]:
        start = node_by_id.get(rel.get(REL_START, ""), {})
        end = node_by_id.get(rel.get(REL_END, ""), {})
        note = rel.get("note", "")
        note_text = f"；说明：{note}" if note else ""
        lines.append(
            f"- {start.get(NODE_NAME, rel.get(REL_START, ''))} "
            f"-[{rel.get(REL_TYPE, '')}]-> "
            f"{end.get(NODE_NAME, rel.get(REL_END, ''))}"
            f"{note_text}"
        )
    return lines


def parse_answer_json(text: str) -> dict:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"learning_path": [text.strip()], "explanation": ""}
    path = data.get("learning_path", [])
    if isinstance(path, str):
        path = [path]
    if not isinstance(path, list):
        path = []
    return {
        "learning_path": [str(item) for item in path],
        "explanation": str(data.get("explanation", "")),
    }


def render_grounded_answer(subgraph: dict, generated: dict) -> str:
    seed_lines = seed_context_lines(subgraph)
    edge_lines = edge_context_lines(subgraph)
    path_lines = [f"   {index}. {item}" for index, item in enumerate(generated.get("learning_path", []), start=1)]
    if not path_lines:
        path_lines = ["   - 图谱事实不足，无法生成明确学习路径。"]
    explanation = generated.get("explanation", "").strip() or "图谱事实不足，建议先补充相关前置关系后再解释。"
    return "\n".join(
        [
            "1. 命中知识点",
            *(f"   {line}" for line in seed_lines),
            "",
            "2. 推荐学习路径",
            *path_lines,
            "",
            "3. 图谱依据",
            *(f"   {line}" for line in edge_lines),
            "",
            "4. 简短解释",
            f"   {explanation}",
        ]
    )


def ollama_chat(model: str, prompt: str, host: str = "http://127.0.0.1:11434", timeout: int = 90) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 700},
    }
    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body.get("message", {}).get("content", "")


def answer_question(args: argparse.Namespace) -> None:
    subgraph = retrieve_subgraph(args.question, args.limit, not args.raw_only)
    context = graph_context(subgraph)
    if args.show_context:
        print(context)
        return
    prompt = f"""
你是一个数学学习助教。你不能把自己作为自由知识源，只能基于下面给定的知识图谱事实回答。
如果图谱事实不足，请明确说明“不足”，但可以给出基于已有事实的学习建议。

用户问题：
{args.question}

知识图谱上下文：
{context}

请按以下结构回答：
只输出 JSON，不要输出 Markdown。
JSON 字段：
{{
  "learning_path": ["步骤1", "步骤2", "..."],
  "explanation": "一段简短解释"
}}

注意：
- 不要输出“命中知识点”和“图谱依据”，这些由程序根据图谱事实确定性生成。
- 推荐学习路径必须基于知识图谱上下文，不要加入图谱中没有出现的知识点。
""".strip()
    try:
        raw_answer = ollama_chat(args.model, prompt, args.ollama_host)
        answer = render_grounded_answer(subgraph, parse_answer_json(raw_answer))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        answer = f"Ollama 调用失败，下面仅展示检索到的图谱上下文。\n\n错误：{error}\n\n{context}"
    print(answer)


def main() -> None:
    parser = argparse.ArgumentParser(description="KG-grounded learning path and QA demo.")
    parser.add_argument("question")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--raw-only", action="store_true", help="只使用原始/导出 CSV，不合并 annotation_state.json 中的 accepted 关系")
    parser.add_argument("--show-context", action="store_true", help="只打印实际提供给大模型的图谱上下文，不调用大模型")
    args = parser.parse_args()
    answer_question(args)


if __name__ == "__main__":
    main()
