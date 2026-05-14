import argparse
import json
from typing import Any, Dict, List


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sort_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        nodes,
        key=lambda n: (
            _to_int(n.get("sorted"), 0),
            str(n.get("nodeName") or n.get("name") or ""),
        ),
    )


def _normalize_node(node: Dict[str, Any]) -> Dict[str, Any]:
    node_uid = node.get("nodeUid") or node.get("id") or ""
    node_name = node.get("nodeName") or node.get("name") or "未命名节点"
    children = node.get("children") or []
    normalized_children = [_normalize_node(c) for c in _sort_nodes(children)]
    return {
        "id": node_uid,
        "name": node_name,
        "children": normalized_children,
    }


def find_root_nodes(content: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = content.get("data", {})

    # 兼容格式1：data.nodeList（当前 kg.txt 使用）
    node_list = data.get("nodeList")
    if isinstance(node_list, list) and node_list:
        return _sort_nodes(node_list)

    # 兼容格式2：data.map.children（部分平台接口格式）
    map_children = data.get("map", {}).get("children", [])
    if isinstance(map_children, list) and map_children:
        return _sort_nodes(map_children)

    # 兼容格式3：根级直接有 nodeList
    top_node_list = content.get("nodeList")
    if isinstance(top_node_list, list) and top_node_list:
        return _sort_nodes(top_node_list)

    return []


def write_text_tree(title: str, nodes: List[Dict[str, Any]], output_file: str) -> None:
    def walk(node: Dict[str, Any], prefix: str, is_last: bool, lines: List[str]) -> None:
        branch = "└── " if is_last else "├── "
        lines.append(f"{prefix}{branch}{node['name']}")
        child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
        children = node.get("children", [])
        for idx, child in enumerate(children):
            walk(child, child_prefix, idx == len(children) - 1, lines)

    lines: List[str] = [f"课程名称: {title}", "=" * 50]
    for i, node in enumerate(nodes):
        walk(node, "", i == len(nodes) - 1, lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def extract_kg_structure(
    input_filename: str = "kg.txt",
    text_output: str = "knowledge_structure.txt",
    json_output: str = "knowledge_structure.json",
) -> None:
    with open(input_filename, "r", encoding="utf-8") as f:
        content = json.load(f)

    roots_raw = find_root_nodes(content)
    if not roots_raw:
        raise ValueError("未找到可解析的知识点节点列表（尝试过 data.nodeList / data.map.children / nodeList）。")

    map_name = content.get("data", {}).get("map", {}).get("mapName", "知识图谱")
    roots = [_normalize_node(n) for n in roots_raw]

    output_json = {
        "course_name": map_name,
        "node_count": len(roots),
        "nodes": roots,
    }

    write_text_tree(map_name, roots, text_output)
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    print(f"提取完成: {input_filename}")
    print(f"课程名称: {map_name}")
    print(f"根节点数量: {len(roots)}")
    print(f"文本结构输出: {text_output}")
    print(f"JSON 结构输出: {json_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从知识图谱 JSON/TXT 中提取结构化知识点")
    parser.add_argument("-i", "--input", default="kg.txt", help="输入文件（默认 kg.txt）")
    parser.add_argument(
        "-t", "--text-output", default="knowledge_structure.txt", help="文本树输出文件"
    )
    parser.add_argument(
        "-j", "--json-output", default="knowledge_structure.json", help="JSON 结构输出文件"
    )
    args = parser.parse_args()

    extract_kg_structure(
        input_filename=args.input,
        text_output=args.text_output,
        json_output=args.json_output,
    )
