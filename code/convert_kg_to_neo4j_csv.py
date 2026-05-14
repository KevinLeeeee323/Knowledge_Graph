#!/usr/bin/env python3
"""
将知识图谱层级 JSON 转换为 Neo4j 导入 CSV。

默认输入:
  knowledge_structure.json

默认输出:
  neo4j_nodes.csv
  neo4j_relationships.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def stable_fallback_id(path_names: List[str], level: int, index: int) -> str:
    """当原始节点没有 id 时，生成稳定可复现的 id。"""
    seed = f"{' > '.join(path_names)}|L{level}|I{index}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
    return f"auto_{digest}"


def load_json(input_file: Path) -> Dict[str, Any]:
    with input_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_id(raw_id: Any) -> Optional[str]:
    if raw_id is None:
        return None
    text = str(raw_id).strip()
    return text or None


def convert_tree_to_rows(
    root_nodes: List[Dict[str, Any]],
    course_name: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    转换为两个表:
      - nodes: Neo4j 节点
      - relationships: Neo4j 边 (父 -> 子)
    """
    node_rows: List[Dict[str, Any]] = []
    rel_rows: List[Dict[str, Any]] = []

    # 处理重复 ID 场景，避免图导入冲突
    id_owner: Dict[str, Tuple[str, int]] = {}
    existing_ids: set[str] = set()

    def ensure_unique_id(
        node_id: Optional[str],
        node_name: str,
        level: int,
        index: int,
        path_names: List[str],
    ) -> str:
        candidate = node_id or stable_fallback_id(path_names, level, index)
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            id_owner[candidate] = (node_name, level)
            return candidate

        # 若相同 ID 指向同名同层级节点，保留；否则自动避让
        owner_name, owner_level = id_owner[candidate]
        if owner_name == node_name and owner_level == level:
            return candidate

        suffix = 1
        while True:
            dedup = f"{candidate}__dup{suffix}"
            if dedup not in existing_ids:
                existing_ids.add(dedup)
                id_owner[dedup] = (node_name, level)
                return dedup
            suffix += 1

    def walk(
        nodes: List[Dict[str, Any]],
        parent_node_id: Optional[str],
        level: int,
        path_names: List[str],
    ) -> None:
        for idx, node in enumerate(nodes, start=1):
            node_name = str(node.get("name", "未命名节点")).strip() or "未命名节点"
            raw_node_id = normalize_id(node.get("id"))
            current_path = path_names + [node_name]
            final_id = ensure_unique_id(raw_node_id, node_name, level, idx, current_path)

            node_rows.append(
                {
                    "node_id:ID": final_id,
                    "name": node_name,
                    "level:int": level,
                    "parent_id": parent_node_id or "",
                    "course_name": course_name,
                    ":LABEL": "KnowledgePoint",
                }
            )

            if parent_node_id:
                rel_rows.append(
                    {
                        ":START_ID": parent_node_id,
                        ":END_ID": final_id,
                        ":TYPE": "CONTAINS",
                        "order:int": idx,
                    }
                )

            children = node.get("children") or []
            if isinstance(children, list) and children:
                walk(children, final_id, level + 1, current_path)

    walk(root_nodes, parent_node_id=None, level=1, path_names=[course_name])
    return node_rows, rel_rows


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="将知识图谱 JSON 转为 Neo4j CSV")
    parser.add_argument(
        "-i",
        "--input",
        default="knowledge_structure.json",
        help="输入 JSON 文件路径",
    )
    parser.add_argument(
        "--nodes-out",
        default="neo4j_nodes.csv",
        help="输出节点 CSV 路径",
    )
    parser.add_argument(
        "--rels-out",
        default="neo4j_relationships.csv",
        help="输出关系 CSV 路径",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    nodes_out = Path(args.nodes_out)
    rels_out = Path(args.rels_out)

    payload = load_json(input_path)
    course_name = str(payload.get("course_name", "知识图谱")).strip() or "知识图谱"
    root_nodes = payload.get("nodes")

    if not isinstance(root_nodes, list) or not root_nodes:
        raise ValueError("输入 JSON 中缺少有效的 nodes 列表。")

    node_rows, rel_rows = convert_tree_to_rows(root_nodes, course_name)

    write_csv(
        nodes_out,
        ["node_id:ID", "name", "level:int", "parent_id", "course_name", ":LABEL"],
        node_rows,
    )
    write_csv(
        rels_out,
        [":START_ID", ":END_ID", ":TYPE", "order:int"],
        rel_rows,
    )

    print(f"转换完成: {input_path}")
    print(f"节点 CSV: {nodes_out} ({len(node_rows)} 行)")
    print(f"关系 CSV: {rels_out} ({len(rel_rows)} 行)")


if __name__ == "__main__":
    main()
