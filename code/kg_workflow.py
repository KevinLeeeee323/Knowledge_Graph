from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "csv_data_ori"
OUTPUT_DIR = ROOT / "csv_data_annotated"
EXPERIMENT_DIR = ROOT / "experiments"

NODES_CSV = SOURCE_DIR / "neo4j_nodes.csv"
RELATIONSHIPS_CSV = SOURCE_DIR / "neo4j_relationships.csv"
STATE_JSON = OUTPUT_DIR / "annotation_state.json"

NODE_ID = "node_id:ID"
NODE_NAME = "name"
NODE_LEVEL = "level:int"
NODE_PARENT = "parent_id"
NODE_COURSE = "course_name"

REL_START = ":START_ID"
REL_END = ":END_ID"
REL_TYPE = ":TYPE"

RELATION_TYPES = [
    "PREREQUISITE_OF",
    "USED_IN",
    "GENERALIZES",
    "SPECIAL_CASE_OF",
    "SIMILAR_TO",
    "EASILY_CONFUSED_WITH",
    "RELATED_TO",
    "NO_RELATION",
]

RELATION_DEFINITIONS = {
    "PREREQUISITE_OF": "A 是学习或理解 B 前通常需要先掌握的知识。",
    "USED_IN": "A 是证明、计算或理解 B 时会用到的工具、定理、方法或概念。",
    "GENERALIZES": "A 是 B 的更一般形式、更高层抽象或推广。",
    "SPECIAL_CASE_OF": "A 是 B 的特殊情形。",
    "SIMILAR_TO": "A 和 B 在方法、结构或思想上相似，可以类比学习。",
    "EASILY_CONFUSED_WITH": "A 和 B 容易被学生混淆，需要对比辨析。",
    "RELATED_TO": "A 和 B 有弱相关，但不宜断言为严格前置、应用、推广或易混淆。",
    "NO_RELATION": "没有明确数学语义关系，或者仅仅同属一章。",
}


@dataclass(frozen=True)
class CandidatePair:
    start_id: str
    end_id: str
    start_name: str
    end_name: str
    start_level: str
    end_level: str
    evidence: str
    strategy: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_nodes_and_relationships() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    return read_csv(NODES_CSV), read_csv(RELATIONSHIPS_CSV)


def build_indexes(nodes: list[dict[str, str]], relationships: list[dict[str, str]]) -> dict:
    node_by_id = {node[NODE_ID]: node for node in nodes}
    children: dict[str, list[str]] = {}
    parents: dict[str, list[str]] = {}
    for rel in relationships:
        if rel.get(REL_TYPE) != "CONTAINS":
            continue
        start_id = rel.get(REL_START, "")
        end_id = rel.get(REL_END, "")
        children.setdefault(start_id, []).append(end_id)
        parents.setdefault(end_id, []).append(start_id)
    return {"node_by_id": node_by_id, "children": children, "parents": parents}


def node_label(node: dict[str, str]) -> str:
    parent = node.get(NODE_PARENT, "")
    return f"{node.get(NODE_NAME, '')}(L{node.get(NODE_LEVEL, '?')}, parent={parent or 'ROOT'})"


def candidate_pairs(limit: int, strategies: set[str] | None = None) -> list[CandidatePair]:
    nodes, relationships = load_nodes_and_relationships()
    graph = build_indexes(nodes, relationships)
    node_by_id = graph["node_by_id"]
    parents = graph["parents"]
    children = graph["children"]
    strategies = strategies or {"parent_child", "siblings", "keyword_bridge"}
    seen: set[tuple[str, str]] = set()
    pairs: list[CandidatePair] = []

    def add(start_id: str, end_id: str, evidence: str, strategy: str) -> None:
        if start_id == end_id or (start_id, end_id) in seen:
            return
        start = node_by_id.get(start_id)
        end = node_by_id.get(end_id)
        if not start or not end:
            return
        seen.add((start_id, end_id))
        pairs.append(
            CandidatePair(
                start_id=start_id,
                end_id=end_id,
                start_name=start.get(NODE_NAME, ""),
                end_name=end.get(NODE_NAME, ""),
                start_level=start.get(NODE_LEVEL, ""),
                end_level=end.get(NODE_LEVEL, ""),
                evidence=evidence,
                strategy=strategy,
            )
        )

    if "parent_child" in strategies:
        for parent_id, child_ids in children.items():
            for child_id in child_ids:
                add(parent_id, child_id, "原始图谱中二者存在 CONTAINS 父子关系。", "parent_child")
                add(child_id, parent_id, "原始图谱中二者存在反向父子关系，可判断是否为特例/归属。", "parent_child")
                if len(pairs) >= limit:
                    return pairs[:limit]

    if "siblings" in strategies:
        for parent_id, child_ids in children.items():
            child_ids = child_ids[:10]
            for index, start_id in enumerate(child_ids):
                for end_id in child_ids[index + 1 :]:
                    parent_name = node_by_id.get(parent_id, {}).get(NODE_NAME, "")
                    add(start_id, end_id, f"二者同属上级知识点：{parent_name}。", "siblings")
                    add(end_id, start_id, f"二者同属上级知识点：{parent_name}。", "siblings")
                    if len(pairs) >= limit:
                        return pairs[:limit]

    if "keyword_bridge" in strategies:
        keywords = ["极限", "连续", "导数", "微分", "积分", "级数", "定理", "法则", "函数", "无穷小", "泰勒"]
        keyword_nodes: dict[str, list[str]] = {
            keyword: [node[NODE_ID] for node in nodes if keyword in node.get(NODE_NAME, "")]
            for keyword in keywords
        }
        for keyword, ids in keyword_nodes.items():
            ids = ids[:12]
            for index, start_id in enumerate(ids):
                for end_id in ids[index + 1 :]:
                    add(start_id, end_id, f"二者名称都包含关键词：{keyword}。", "keyword_bridge")
                    add(end_id, start_id, f"二者名称都包含关键词：{keyword}。", "keyword_bridge")
                    if len(pairs) >= limit:
                        return pairs[:limit]

    return pairs[:limit]


def ollama_chat(model: str, prompt: str, host: str = "http://127.0.0.1:11434", timeout: int = 90) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 220},
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


def check_ollama_model(model: str, host: str, timeout: int = 8) -> None:
    request = urllib.request.Request(f"{host.rstrip('/')}/api/tags", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    models = {item.get("name") for item in body.get("models", [])}
    if model not in models:
        available = ", ".join(sorted(name for name in models if name)) or "no models"
        raise RuntimeError(f"Ollama model '{model}' not found. Available models: {available}")


def relation_prompt(pair: CandidatePair, version: str, few_shot: list[dict[str, str]] | None = None) -> str:
    type_lines = "\n".join(f"- {name}: {desc}" for name, desc in RELATION_DEFINITIONS.items())
    base_rules = """
请判断两个高等数学/数学分析知识点 A 与 B 之间最合适的有向关系。
只能从给定关系类型中选择一个。如果没有明确数学语义关系，选择 NO_RELATION。
注意关系方向，不要把“同属一章”直接当成先修关系。
输出必须是 JSON，不要输出 Markdown。
JSON 字段：
{
  "relation": "...",
  "confidence": 0.0到1.0,
  "reason": "一句话理由"
}
""".strip()
    extra = ""
    if version == "v2":
        examples = few_shot or default_few_shot_examples()
        example_text = "\n".join(
            json.dumps(example, ensure_ascii=False)
            for example in examples[:10]
        )
        extra = f"""

下面是人工审核后的示例，请学习其中的关系方向和错误规避方式：
{example_text}

额外规则：
- 前置关系必须表示 A 对理解 B 有明确帮助，不能只因 A 出现在 B 前面。
- 如果 A/B 只是同一章节下的兄弟知识点，通常优先选择 RELATED_TO 或 NO_RELATION。
- 如果无法确信，选择 NO_RELATION，并降低 confidence。
""".rstrip()
    return f"""
{base_rules}

关系类型：
{type_lines}
{extra}

待判断：
A: {pair.start_name}，层级 L{pair.start_level}
B: {pair.end_name}，层级 L{pair.end_level}
候选来源证据：{pair.evidence}

请输出 JSON。
""".strip()


def batch_relation_prompt(pairs: list[CandidatePair], version: str, few_shot: list[dict[str, str]] | None = None) -> str:
    type_lines = "\n".join(f"- {name}: {desc}" for name, desc in RELATION_DEFINITIONS.items())
    items = []
    for index, pair in enumerate(pairs, start=1):
        items.append(
            {
                "id": index,
                "A": pair.start_name,
                "A_level": pair.start_level,
                "B": pair.end_name,
                "B_level": pair.end_level,
                "evidence": pair.evidence,
            }
        )
    extra = ""
    if version == "v2":
        examples = few_shot or default_few_shot_examples()
        extra = "\n人工审核示例：\n" + "\n".join(json.dumps(example, ensure_ascii=False) for example in examples[:10])
    return f"""
请批量判断高等数学/数学分析知识点 A 与 B 之间最合适的有向关系。
只能从给定关系类型中选择一个。如果没有明确数学语义关系，选择 NO_RELATION。
注意关系方向，不要把“同属一章”直接当成先修关系。

关系类型：
{type_lines}
{extra}

待判断列表：
{json.dumps(items, ensure_ascii=False, indent=2)}

输出必须是 JSON 数组，不要输出 Markdown。数组每个元素格式：
{{"id": 1, "relation": "...", "confidence": 0.0到1.0, "reason": "一句话理由"}}
""".strip()


def default_few_shot_examples() -> list[dict[str, str]]:
    return [
        {
            "A": "数列极限的定义",
            "B": "数列极限的夹逼定理",
            "relation": "PREREQUISITE_OF",
            "reason": "理解夹逼定理需要先理解数列极限的定义。",
        },
        {
            "A": "连续性",
            "B": "导数的定义",
            "relation": "NO_RELATION",
            "reason": "连续性不是导数定义的前置条件，不能把可导推出连续反向理解。",
        },
        {
            "A": "洛必达法则",
            "B": "未定式极限计算",
            "relation": "USED_IN",
            "reason": "洛必达法则是处理某些未定式极限的计算工具。",
        },
        {
            "A": "数列极限的夹逼定理",
            "B": "函数极限的夹逼定理",
            "relation": "SIMILAR_TO",
            "reason": "二者证明思想和使用方式相似，但对象不同。",
        },
    ]


def parse_model_json(text: str) -> dict[str, str]:
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"relation": "NO_RELATION", "confidence": "0", "reason": f"模型输出无法解析：{text[:120]}"}
    relation = str(data.get("relation", "NO_RELATION")).strip().upper()
    if relation not in RELATION_TYPES:
        relation = "NO_RELATION"
    return {
        "relation": relation,
        "confidence": str(data.get("confidence", "")),
        "reason": str(data.get("reason", "")),
    }


def parse_model_json_array(text: str) -> list[dict[str, str]]:
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    match = re.search(r"\[.*\]", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    parsed = []
    for item in data:
        if not isinstance(item, dict):
            continue
        relation = str(item.get("relation", "NO_RELATION")).strip().upper()
        if relation not in RELATION_TYPES:
            relation = "NO_RELATION"
        parsed.append(
            {
                "id": str(item.get("id", "")),
                "relation": relation,
                "confidence": str(item.get("confidence", "")),
                "reason": str(item.get("reason", "")),
            }
        )
    return parsed


def load_gold_examples(path: Path | None = None) -> list[dict[str, str]]:
    path = path or (OUTPUT_DIR / "gold_set.csv")
    if not path.exists():
        return default_few_shot_examples()
    rows = read_csv(path)
    examples = []
    for row in rows:
        decision = row.get("human_decision", row.get("status", ""))
        relation = row.get("human_label") or row.get("type", "")
        if decision not in {"accepted", "corrected"} and row.get("status") != "accepted":
            continue
        examples.append(
            {
                "A": row.get("start_name", ""),
                "B": row.get("end_name", ""),
                "relation": relation,
                "reason": row.get("human_note") or row.get("note", ""),
            }
        )
    return examples or default_few_shot_examples()


def generate_candidates(args: argparse.Namespace) -> Path:
    pairs = candidate_pairs(args.limit)
    few_shot = load_gold_examples(Path(args.gold_set)) if args.gold_set else load_gold_examples()
    rows = []
    filtered_no_relation = 0
    output = Path(args.output) if args.output else OUTPUT_DIR / f"candidate_relations_{args.prompt_version}.csv"

    if not args.no_llm:
        try:
            check_ollama_model(args.model, args.ollama_host)
            print(f"Ollama ready: {args.model}", flush=True)
        except Exception as error:
            print(f"Warning: Ollama precheck failed: {error}", flush=True)

    def append_row(index: int, pair: CandidatePair, parsed: dict[str, str]) -> None:
        nonlocal filtered_no_relation
        if parsed["relation"] == "NO_RELATION" and not args.keep_no_relation:
            filtered_no_relation += 1
            return
        rows.append(
            {
                "id": f"ai-{args.prompt_version}-{index:04d}",
                "start_id": pair.start_id,
                "start_name": pair.start_name,
                "end_id": pair.end_id,
                "end_name": pair.end_name,
                "type": parsed["relation"],
                "confidence": parsed["confidence"],
                "source": f"ai_{args.prompt_version}",
                "status": "pending",
                "annotator": "",
                "note": parsed["reason"],
                "strategy": pair.strategy,
                "evidence": pair.evidence,
                "prompt_version": args.prompt_version,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if args.save_every and len(rows) % args.save_every == 0:
            write_candidate_rows(output, rows)

    batch_size = max(1, args.batch_size)
    batches = [pairs[start : start + batch_size] for start in range(0, len(pairs), batch_size)]
    iterator = tqdm(batches, total=len(batches), desc="candidate batches") if tqdm else batches
    for batch_index, batch in enumerate(iterator):
        base_index = batch_index * batch_size
        if args.no_llm:
            for offset, pair in enumerate(batch, start=1):
                append_row(
                    base_index + offset,
                    pair,
                    {
                        "relation": heuristic_relation(pair),
                        "confidence": "0.40",
                        "reason": "未调用大模型，使用规则基线生成。",
                    },
                )
            continue

        names = "；".join(f"{pair.start_name}->{pair.end_name}" for pair in batch)
        print(f"Generating batch {batch_index + 1}/{len(batches)}: {names}", flush=True)
        try:
            if len(batch) == 1:
                raw = ollama_chat(args.model, relation_prompt(batch[0], args.prompt_version, few_shot), args.ollama_host, args.timeout)
                parsed_items = [parse_model_json(raw)]
            else:
                raw = ollama_chat(args.model, batch_relation_prompt(batch, args.prompt_version, few_shot), args.ollama_host, args.timeout)
                parsed_items = parse_model_json_array(raw)
                if len(parsed_items) != len(batch):
                    raise ValueError(f"Expected {len(batch)} JSON results, got {len(parsed_items)}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            parsed_items = [
                {
                    "relation": heuristic_relation(pair),
                    "confidence": "0.25",
                    "reason": f"模型调用/解析失败，回退规则基线：{error}",
                }
                for pair in batch
            ]

        by_result_id = {str(item.get("id", "")): item for item in parsed_items}
        for offset, pair in enumerate(batch, start=1):
            parsed = by_result_id.get(str(offset), parsed_items[offset - 1] if offset - 1 < len(parsed_items) else None)
            if not parsed:
                parsed = {
                    "relation": heuristic_relation(pair),
                    "confidence": "0.25",
                    "reason": "模型未返回该条结果，回退规则基线。",
                }
            append_row(base_index + offset, pair, parsed)

    write_candidate_rows(output, rows)
    print(
        f"Generated {len(rows)} candidate rows from {len(pairs)} pairs. "
        f"Filtered NO_RELATION: {filtered_no_relation}.",
        flush=True,
    )
    return output


def write_candidate_rows(output: Path, rows: list[dict[str, str]]) -> None:
    write_csv(
        output,
        [
            "id",
            "start_id",
            "start_name",
            "end_id",
            "end_name",
            "type",
            "confidence",
            "source",
            "status",
            "annotator",
            "note",
            "strategy",
            "evidence",
            "prompt_version",
            "created_at",
        ],
        rows,
    )


def heuristic_relation(pair: CandidatePair) -> str:
    if pair.strategy == "parent_child":
        if int(pair.start_level or "0") < int(pair.end_level or "0"):
            return "PREREQUISITE_OF"
        return "SPECIAL_CASE_OF"
    if pair.strategy == "keyword_bridge":
        return "SIMILAR_TO"
    return "RELATED_TO"


def import_candidates(args: argparse.Namespace) -> None:
    path = Path(args.path)
    rows = read_csv(path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_JSON.exists():
        with STATE_JSON.open("r", encoding="utf-8") as file:
            state = json.load(file)
    else:
        state = {"custom_nodes": [], "annotations": [], "relation_types": []}
    by_id = {item.get("id"): item for item in state.get("annotations", [])}
    for row in rows:
        if not row.get("id"):
            row["id"] = f"imported-{row.get('start_id')}-{row.get('end_id')}-{row.get('type')}"
        by_id[row["id"]] = {
            "id": row.get("id", ""),
            "source": row.get("source", "ai_imported"),
            "status": row.get("status", "pending"),
            "start_id": row.get("start_id", ""),
            "start_name": row.get("start_name", ""),
            "end_id": row.get("end_id", ""),
            "end_name": row.get("end_name", ""),
            "type": row.get("type", ""),
            "confidence": row.get("confidence", ""),
            "note": row.get("note", ""),
            "annotator": row.get("annotator", ""),
            "strategy": row.get("strategy", ""),
            "evidence": row.get("evidence", ""),
            "prompt_version": row.get("prompt_version", ""),
            "human_label": row.get("human_label", ""),
            "human_decision": row.get("human_decision", ""),
            "error_type": row.get("error_type", ""),
            "human_note": row.get("human_note", ""),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    state["annotations"] = list(by_id.values())
    state["relation_types"] = sorted(set(state.get("relation_types", [])) | set(RELATION_TYPES))
    with STATE_JSON.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def export_gold(args: argparse.Namespace) -> Path:
    if not STATE_JSON.exists():
        raise FileNotFoundError("No annotation_state.json found. Run the UI or import candidates first.")
    with STATE_JSON.open("r", encoding="utf-8") as file:
        state = json.load(file)
    rows = []
    nodes, _ = load_nodes_and_relationships()
    node_by_id = {node[NODE_ID]: node for node in nodes}
    for item in state.get("annotations", []):
        status = item.get("status", "")
        if status not in {"accepted", "rejected"} and not item.get("human_decision"):
            continue
        human_label = item.get("human_label") or (item.get("type") if status == "accepted" else "NO_RELATION")
        human_decision = item.get("human_decision") or ("accepted" if status == "accepted" else "rejected")
        rows.append(
            {
                "id": item.get("id", ""),
                "start_id": item.get("start_id", ""),
                "start_name": node_by_id.get(item.get("start_id", ""), {}).get(NODE_NAME, item.get("start_name", "")),
                "end_id": item.get("end_id", ""),
                "end_name": node_by_id.get(item.get("end_id", ""), {}).get(NODE_NAME, item.get("end_name", "")),
                "ai_label": item.get("type", ""),
                "human_label": human_label,
                "human_decision": human_decision,
                "error_type": item.get("error_type", ""),
                "confidence": item.get("confidence", ""),
                "source": item.get("source", ""),
                "prompt_version": item.get("prompt_version", ""),
                "human_note": item.get("human_note") or item.get("note", ""),
            }
        )
    output = Path(args.output) if args.output else OUTPUT_DIR / "gold_set.csv"
    write_csv(
        output,
        [
            "id",
            "start_id",
            "start_name",
            "end_id",
            "end_name",
            "ai_label",
            "human_label",
            "human_decision",
            "error_type",
            "confidence",
            "source",
            "prompt_version",
            "human_note",
        ],
        rows,
    )
    return output


def evaluate_gold(args: argparse.Namespace) -> Path:
    rows = read_csv(Path(args.gold_set))
    grouped: dict[str, dict[str, int]] = {}
    error_counts: dict[str, int] = {}
    for row in rows:
        version = row.get("prompt_version") or row.get("source") or "unknown"
        grouped.setdefault(version, {"total": 0, "correct": 0})
        grouped[version]["total"] += 1
        ai_label = row.get("ai_label", "")
        human_label = row.get("human_label", "")
        decision = row.get("human_decision", "")
        if decision == "accepted" or ai_label == human_label:
            grouped[version]["correct"] += 1
        error = row.get("error_type", "")
        if error:
            error_counts[error] = error_counts.get(error, 0) + 1
    report = {
        "gold_set": str(Path(args.gold_set)),
        "versions": {
            version: {
                **stats,
                "accuracy": round(stats["correct"] / stats["total"], 4) if stats["total"] else 0,
            }
            for version, stats in grouped.items()
        },
        "error_counts": error_counts,
    }
    output = Path(args.output) if args.output else EXPERIMENT_DIR / "relation_generation_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="KG enhancement workflow for candidate generation and evaluation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate-candidates")
    gen.add_argument("--model", default="qwen2.5:7b")
    gen.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    gen.add_argument("--prompt-version", choices=["v1", "v2"], default="v1")
    gen.add_argument("--gold-set", default="")
    gen.add_argument("--limit", type=int, default=120)
    gen.add_argument("--output", default="")
    gen.add_argument("--batch-size", type=int, default=4)
    gen.add_argument("--save-every", type=int, default=10)
    gen.add_argument("--timeout", type=int, default=180)
    gen.add_argument("--no-llm", action="store_true")
    gen.add_argument("--keep-no-relation", action="store_true")
    gen.set_defaults(func=generate_candidates)

    imp = subparsers.add_parser("import-candidates")
    imp.add_argument("path")
    imp.set_defaults(func=import_candidates)

    gold = subparsers.add_parser("export-gold")
    gold.add_argument("--output", default="")
    gold.set_defaults(func=export_gold)

    eval_parser = subparsers.add_parser("evaluate-gold")
    eval_parser.add_argument("--gold-set", default=str(OUTPUT_DIR / "gold_set.csv"))
    eval_parser.add_argument("--output", default="")
    eval_parser.set_defaults(func=evaluate_gold)

    args = parser.parse_args()
    result = args.func(args)
    if isinstance(result, Path):
        print(result)


if __name__ == "__main__":
    main()
