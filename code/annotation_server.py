from __future__ import annotations

import csv
import json
import mimetypes
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "csv_data_ori"
OUTPUT_DIR = ROOT / "csv_data_annotated"
UI_DIR = ROOT / "annotation_ui"

NODES_CSV = SOURCE_DIR / "neo4j_nodes.csv"
RELATIONSHIPS_CSV = SOURCE_DIR / "neo4j_relationships.csv"
STATE_JSON = OUTPUT_DIR / "annotation_state.json"
HISTORY_JSON = OUTPUT_DIR / "annotation_history.json"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"
EXPORT_REL_CSV = OUTPUT_DIR / "annotated_relationships.csv"
EXPORT_NODE_CSV = OUTPUT_DIR / "annotated_nodes.csv"
GOLD_SET_CSV = OUTPUT_DIR / "gold_set.csv"
CANDIDATE_CSV = OUTPUT_DIR / "candidate_relations_v1.csv"

NODE_ID = "node_id:ID"
NODE_NAME = "name"
NODE_LEVEL = "level:int"
NODE_PARENT = "parent_id"
NODE_COURSE = "course_name"
NODE_LABEL = ":LABEL"

REL_START = ":START_ID"
REL_END = ":END_ID"
REL_TYPE = ":TYPE"
REL_ORDER = "order:int"

DEFAULT_RELATION_TYPES = [
    "PREREQUISITE_OF",
    "USED_IN",
    "GENERALIZES",
    "SPECIAL_CASE_OF",
    "SIMILAR_TO",
    "EASILY_CONFUSED_WITH",
    "RELATED_TO",
    "NO_RELATION",
]

ERROR_TYPES = [
    "",
    "direction_error",
    "relation_type_error",
    "no_real_relation",
    "too_weak_relation",
    "math_error",
    "duplicate",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_source() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not NODES_CSV.exists() or not RELATIONSHIPS_CSV.exists():
        raise FileNotFoundError("Expected csv_data_ori/neo4j_nodes.csv and neo4j_relationships.csv")
    return read_csv(NODES_CSV), read_csv(RELATIONSHIPS_CSV)


def default_state() -> dict:
    return {
        "custom_nodes": [],
        "annotations": [],
        "relation_types": DEFAULT_RELATION_TYPES,
        "updated_at": "",
    }


def load_state() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_JSON.exists():
        state = default_state()
        save_state(state)
        return state
    with STATE_JSON.open("r", encoding="utf-8") as file:
        state = json.load(file)
    base = default_state()
    base.update(state)
    base["relation_types"] = sorted(set(base["relation_types"]) | set(DEFAULT_RELATION_TYPES))
    return base


def save_state(state: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with STATE_JSON.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def load_history() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_JSON.exists():
        return {"undo": [], "redo": []}
    with HISTORY_JSON.open("r", encoding="utf-8") as file:
        history = json.load(file)
    history.setdefault("undo", [])
    history.setdefault("redo", [])
    return history


def save_history(history: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history["undo"] = history.get("undo", [])[-60:]
    history["redo"] = history.get("redo", [])[-60:]
    with HISTORY_JSON.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)


def remember_for_undo(current_state: dict) -> None:
    history = load_history()
    history.setdefault("undo", []).append(current_state)
    history["redo"] = []
    save_history(history)


def snapshot_state() -> dict:
    state = load_state()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot_path = SNAPSHOT_DIR / f"annotation_state_{stamp}.json"
    with snapshot_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
    return {
        "snapshot": str(snapshot_path.relative_to(ROOT)),
        "updated_at": state.get("updated_at", ""),
    }


def restore_from_history(direction: str) -> dict:
    history = load_history()
    current = load_state()
    if direction == "undo":
        source_key = "undo"
        target_key = "redo"
    else:
        source_key = "redo"
        target_key = "undo"
    if not history.get(source_key):
        return {"ok": False, "message": f"nothing to {direction}"}
    next_state = history[source_key].pop()
    history.setdefault(target_key, []).append(current)
    save_history(history)
    save_state(next_state)
    return {"ok": True, "state": next_state}


def build_graph(nodes: list[dict[str, str]], relationships: list[dict[str, str]]) -> dict:
    node_by_id = {node[NODE_ID]: node for node in nodes}
    children: dict[str, list[str]] = {}
    parents: dict[str, list[str]] = {}
    relation_views = []

    for rel in relationships:
        start_id = rel.get(REL_START, "")
        end_id = rel.get(REL_END, "")
        rel_type = rel.get(REL_TYPE, "")
        if rel_type == "CONTAINS":
            children.setdefault(start_id, []).append(end_id)
            parents.setdefault(end_id, []).append(start_id)
        relation_views.append(
            {
                "id": f"source-{start_id}-{end_id}-{rel_type}-{rel.get(REL_ORDER, '')}",
                "source": "original",
                "status": "locked",
                "start_id": start_id,
                "start_name": node_by_id.get(start_id, {}).get(NODE_NAME, start_id),
                "end_id": end_id,
                "end_name": node_by_id.get(end_id, {}).get(NODE_NAME, end_id),
                "type": rel_type,
                "order": rel.get(REL_ORDER, ""),
                "note": "",
                "confidence": "",
            }
        )

    for node_id in children:
        children[node_id].sort(key=lambda child_id: int(node_by_id.get(child_id, {}).get(NODE_LEVEL, "0") or 0))
    return {
        "node_by_id": node_by_id,
        "children": children,
        "parents": parents,
        "original_relationships": relation_views,
    }


def annotation_view(annotation: dict, node_by_id: dict[str, dict[str, str]]) -> dict:
    start_id = annotation.get("start_id", "")
    end_id = annotation.get("end_id", "")
    return {
        **annotation,
        "start_name": node_by_id.get(start_id, {}).get(NODE_NAME, annotation.get("start_name", start_id)),
        "end_name": node_by_id.get(end_id, {}).get(NODE_NAME, annotation.get("end_name", end_id)),
    }


def make_candidate(
    start_id: str,
    end_id: str,
    rel_type: str,
    reason: str,
    node_by_id: dict[str, dict[str, str]],
    confidence: str = "0.60",
) -> dict:
    return {
        "id": f"candidate-{start_id}-{end_id}-{rel_type}",
        "source": "rule_candidate",
        "status": "pending",
        "start_id": start_id,
        "start_name": node_by_id.get(start_id, {}).get(NODE_NAME, start_id),
        "end_id": end_id,
        "end_name": node_by_id.get(end_id, {}).get(NODE_NAME, end_id),
        "type": rel_type,
        "confidence": confidence,
        "note": reason,
    }


def generate_rule_candidates(node_id: str, graph: dict, existing_keys: set[tuple[str, str, str]]) -> list[dict]:
    node_by_id = graph["node_by_id"]
    parents = graph["parents"].get(node_id, [])
    children = graph["children"].get(node_id, [])
    candidates = []

    for child_id in children:
        key = (node_id, child_id, "PREREQUISITE_OF")
        if key not in existing_keys:
            candidates.append(
                make_candidate(
                    node_id,
                    child_id,
                    "PREREQUISITE_OF",
                    "父级知识点通常是理解子级知识点的背景或前置内容，请人工确认。",
                    node_by_id,
                )
            )

    for parent_id in parents:
        siblings = [item for item in graph["children"].get(parent_id, []) if item != node_id]
        for sibling_id in siblings[:8]:
            key = (node_id, sibling_id, "RELATED_TO")
            if key not in existing_keys:
                candidates.append(
                    make_candidate(
                        node_id,
                        sibling_id,
                        "RELATED_TO",
                        "同属一个上级知识点，可能存在概念或方法关联，请人工筛选。",
                        node_by_id,
                        confidence="0.45",
                    )
                )

    for parent_id in parents:
        key = (parent_id, node_id, "GENERALIZES")
        if key not in existing_keys:
            candidates.append(
                make_candidate(
                    parent_id,
                    node_id,
                    "GENERALIZES",
                    "上级知识点可能是当前知识点的概括或主题归属，请人工确认是否是数学意义上的推广。",
                    node_by_id,
                    confidence="0.50",
                )
            )
    return candidates


def data_payload() -> dict:
    source_nodes, source_relationships = load_source()
    state = load_state()
    nodes = source_nodes + state.get("custom_nodes", [])
    graph = build_graph(nodes, source_relationships)
    node_by_id = graph["node_by_id"]
    annotation_rows = [annotation_view(item, node_by_id) for item in state.get("annotations", [])]
    annotation_keys = {
        (item.get("start_id", ""), item.get("end_id", ""), item.get("type", ""))
        for item in state.get("annotations", [])
        if item.get("status") != "rejected"
    }
    original_keys = {
        (item.get(REL_START, ""), item.get(REL_END, ""), item.get(REL_TYPE, ""))
        for item in source_relationships
    }
    nodes_view = []
    for node in nodes:
        node_id = node.get(NODE_ID, "")
        parent_id = node.get(NODE_PARENT, "")
        nodes_view.append(
            {
                "id": node_id,
                "name": node.get(NODE_NAME, ""),
                "level": node.get(NODE_LEVEL, ""),
                "parent_id": parent_id,
                "parent_name": node_by_id.get(parent_id, {}).get(NODE_NAME, ""),
                "course_name": node.get(NODE_COURSE, ""),
                "label": node.get(NODE_LABEL, "KnowledgePoint"),
                "source": "custom" if node.get("_custom") == "true" else "original",
                "child_count": len(graph["children"].get(node_id, [])),
            }
        )
    return {
        "nodes": nodes_view,
        "original_relationships": graph["original_relationships"],
        "annotations": annotation_rows,
        "relation_types": state.get("relation_types", DEFAULT_RELATION_TYPES),
        "error_types": ERROR_TYPES,
        "stats": {
            "original_nodes": len(source_nodes),
            "custom_nodes": len(state.get("custom_nodes", [])),
            "original_relationships": len(source_relationships),
            "annotations": len(state.get("annotations", [])),
            "accepted_annotations": sum(1 for item in state.get("annotations", []) if item.get("status") == "accepted"),
            "updated_at": state.get("updated_at", ""),
            "candidate_file": str(CANDIDATE_CSV.relative_to(ROOT)),
            "candidate_file_exists": CANDIDATE_CSV.exists(),
            "ai_candidates_loaded": sum(1 for item in state.get("annotations", []) if str(item.get("source", "")).startswith("ai_")),
        },
        "candidate_keys": list(annotation_keys | original_keys),
    }


def export_state() -> dict:
    source_nodes, source_relationships = load_source()
    state = load_state()
    all_nodes = []
    for node in source_nodes:
        all_nodes.append({field: node.get(field, "") for field in [NODE_ID, NODE_NAME, NODE_LEVEL, NODE_PARENT, NODE_COURSE, NODE_LABEL]})
    for node in state.get("custom_nodes", []):
        all_nodes.append({field: node.get(field, "") for field in [NODE_ID, NODE_NAME, NODE_LEVEL, NODE_PARENT, NODE_COURSE, NODE_LABEL]})

    exported_relationships = []
    for rel in source_relationships:
        exported_relationships.append(
            {
                REL_START: rel.get(REL_START, ""),
                REL_END: rel.get(REL_END, ""),
                REL_TYPE: rel.get(REL_TYPE, ""),
                REL_ORDER: rel.get(REL_ORDER, ""),
                "status": "original",
                "confidence": "",
                "source": "original",
                "annotator": "",
                "note": "",
            }
        )
    for item in state.get("annotations", []):
        if item.get("status") != "accepted":
            continue
        exported_relationships.append(
            {
                REL_START: item.get("start_id", ""),
                REL_END: item.get("end_id", ""),
                REL_TYPE: item.get("type", ""),
                REL_ORDER: "",
                "status": "accepted",
                "confidence": item.get("confidence", ""),
                "source": item.get("source", "manual"),
                "annotator": item.get("annotator", ""),
                "note": item.get("note", ""),
            }
        )

    write_csv(EXPORT_NODE_CSV, [NODE_ID, NODE_NAME, NODE_LEVEL, NODE_PARENT, NODE_COURSE, NODE_LABEL], all_nodes)
    write_csv(
        EXPORT_REL_CSV,
        [REL_START, REL_END, REL_TYPE, REL_ORDER, "status", "confidence", "source", "annotator", "note"],
        exported_relationships,
    )
    return {
        "nodes_csv": str(EXPORT_NODE_CSV.relative_to(ROOT)),
        "relationships_csv": str(EXPORT_REL_CSV.relative_to(ROOT)),
        "node_count": len(all_nodes),
        "relationship_count": len(exported_relationships),
    }


def import_candidates_from_csv(path: Path | None = None) -> dict:
    path = path or CANDIDATE_CSV
    if not path.exists():
        return {"ok": False, "message": f"{path.relative_to(ROOT)} not found"}
    rows = read_csv(path)
    state = load_state()
    remember_for_undo(state)
    by_id = {item.get("id"): item for item in state.get("annotations", [])}
    imported = 0
    for row in rows:
        item_id = row.get("id") or f"imported-{row.get('start_id', '')}-{row.get('end_id', '')}-{row.get('type', '')}"
        by_id[item_id] = {
            "id": item_id,
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
        imported += 1
    state["annotations"] = list(by_id.values())
    state["relation_types"] = sorted(set(state.get("relation_types", [])) | set(DEFAULT_RELATION_TYPES))
    save_state(state)
    return {"ok": True, "count": imported, "path": str(path.relative_to(ROOT))}


def export_gold_set() -> dict:
    source_nodes, _ = load_source()
    state = load_state()
    node_by_id = {node[NODE_ID]: node for node in source_nodes + state.get("custom_nodes", [])}
    rows = []
    for item in state.get("annotations", []):
        status = item.get("status", "")
        if status not in {"accepted", "rejected"} and not item.get("human_decision"):
            continue
        human_label = item.get("human_label") or (item.get("type", "") if status == "accepted" else "NO_RELATION")
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
    write_csv(
        GOLD_SET_CSV,
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
    return {"gold_set_csv": str(GOLD_SET_CSV.relative_to(ROOT)), "count": len(rows)}


class AnnotationHandler(BaseHTTPRequestHandler):
    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/data":
            self.send_json(data_payload())
            return
        if parsed.path == "/api/candidates":
            query = parse_qs(parsed.query)
            node_id = query.get("node_id", [""])[0]
            nodes, relationships = load_source()
            state = load_state()
            graph = build_graph(nodes + state.get("custom_nodes", []), relationships)
            existing_keys = {
                (item.get("start_id", ""), item.get("end_id", ""), item.get("type", ""))
                for item in state.get("annotations", [])
                if item.get("status") != "rejected"
            }
            existing_keys.update((item.get(REL_START, ""), item.get(REL_END, ""), item.get(REL_TYPE, "")) for item in relationships)
            self.send_json({"candidates": generate_rule_candidates(node_id, graph, existing_keys)})
            return

        path = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        file_path = (UI_DIR / path).resolve()
        if not str(file_path).startswith(str(UI_DIR.resolve())) or not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        state = load_state()
        payload = self.read_json()

        if parsed.path == "/api/annotation":
            item = payload.get("annotation", {})
            remember_for_undo(state)
            item.setdefault("id", f"ann-{uuid.uuid4().hex[:12]}")
            item.setdefault("source", "manual")
            item.setdefault("status", "pending")
            item.setdefault("confidence", "")
            item.setdefault("note", "")
            item.setdefault("annotator", "")
            item.setdefault("human_label", "")
            item.setdefault("human_decision", "")
            item.setdefault("error_type", "")
            item.setdefault("human_note", "")
            item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            existing = [ann for ann in state.get("annotations", []) if ann.get("id") != item["id"]]
            existing.append(item)
            state["annotations"] = existing
            if item.get("type"):
                state["relation_types"] = sorted(set(state.get("relation_types", [])) | {item["type"]})
            save_state(state)
            self.send_json({"ok": True, "annotation": item})
            return

        if parsed.path == "/api/annotations/bulk":
            incoming = payload.get("annotations", [])
            remember_for_undo(state)
            by_id = {item.get("id"): item for item in state.get("annotations", [])}
            for item in incoming:
                item.setdefault("id", f"ann-{uuid.uuid4().hex[:12]}")
                item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                by_id[item["id"]] = item
                if item.get("type"):
                    state["relation_types"] = sorted(set(state.get("relation_types", [])) | {item["type"]})
            state["annotations"] = list(by_id.values())
            save_state(state)
            self.send_json({"ok": True, "count": len(incoming)})
            return

        if parsed.path == "/api/node":
            node = payload.get("node", {})
            remember_for_undo(state)
            node_id = node.get(NODE_ID) or f"custom-{uuid.uuid4().hex[:10]}"
            node[NODE_ID] = node_id
            node.setdefault(NODE_LABEL, "KnowledgePoint")
            node["_custom"] = "true"
            node.setdefault(NODE_LEVEL, "")
            node.setdefault(NODE_PARENT, "")
            node.setdefault(NODE_COURSE, "")
            state["custom_nodes"] = [item for item in state.get("custom_nodes", []) if item.get(NODE_ID) != node_id]
            if node.get("_deleted") != "true":
                state["custom_nodes"].append(node)
            save_state(state)
            self.send_json({"ok": True, "node": node})
            return

        if parsed.path == "/api/relation-type":
            rel_type = payload.get("type", "").strip().upper()
            if rel_type:
                remember_for_undo(state)
                state["relation_types"] = sorted(set(state.get("relation_types", [])) | {rel_type})
                save_state(state)
            self.send_json({"ok": True, "relation_types": state.get("relation_types", [])})
            return

        if parsed.path == "/api/save":
            self.send_json({"ok": True, **snapshot_state()})
            return

        if parsed.path == "/api/undo":
            self.send_json(restore_from_history("undo"))
            return

        if parsed.path == "/api/redo":
            self.send_json(restore_from_history("redo"))
            return

        if parsed.path == "/api/export":
            self.send_json({"ok": True, **export_state()})
            return

        if parsed.path == "/api/import-candidates":
            candidate_path = payload.get("path", "")
            self.send_json(import_candidates_from_csv(Path(candidate_path) if candidate_path else None))
            return

        if parsed.path == "/api/export-gold":
            self.send_json({"ok": True, **export_gold_set()})
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), AnnotationHandler)
    print("Annotation UI: http://127.0.0.1:8765")
    print(f"Reading source CSV from: {SOURCE_DIR}")
    print(f"Writing annotated output to: {OUTPUT_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()
