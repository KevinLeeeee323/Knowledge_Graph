#!/usr/bin/env python3
"""Local KG-constrained problem analyzer.

Run from the project root:

    python3 code/problem_analyzer_server.py --model qwen2.5:7b

It serves the existing static viewer and adds one API:

    POST /api/analyze-problem
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "data" / "kg.json"

RELATION_LABELS = {
    "PREREQUISITE_OF": "前置",
    "USED_IN": "应用于",
    "GENERALIZES": "推广",
    "SPECIAL_CASE_OF": "特例",
    "SIMILAR_TO": "类比",
    "EASILY_CONFUSED_WITH": "易混淆",
    "RELATED_TO": "相关",
    "CONTAINS": "包含",
}

PROMPT_TEMPLATE = """你是一个受知识图谱约束的数学错题分析助手。

任务：分析学生粘贴的题目，把它映射到候选知识图谱节点中。你只能选择候选列表里已有的 id，不能编造新节点。

学生题目：
{question}

候选知识点 JSON：
{candidates}

请快速给出最终结果。只输出一个合法 JSON 对象，不要输出 Markdown，不要输出代码块，不要输出 <think>，不要输出思考过程，不要解释 JSON 外的内容。所有 key 和字符串都必须使用英文双引号。格式如下：
{{
  "condition_check": "先检查题目条件是否完整，例如函数在特殊点是否定义。",
  "diagnosis": "一句话说明这道题主要考察什么，以及为什么不能只套公式。",
  "nodes": [
    {{"id": "候选节点id", "weight": 45, "role": "主要考点", "reason": "为什么命中该知识点"}}
  ],
  "route": ["候选节点id1", "候选节点id2"],
  "solution_steps": ["第一步", "第二步", "第三步"],
  "mistakes": ["常见错误1", "常见错误2"]
}}

要求：
1. nodes 最多 8 个，weight 为 1 到 100 的整数，所有 weight 之和尽量为 100。
2. route 最多 6 个 id，必须来自 nodes 或候选知识点。
3. 如果题目条件可能不完整，要在 condition_check 中指出。
4. 若候选知识点不足以判断，仍然只能从候选里选最相关的，并在 diagnosis 里说明不确定性。
"""


def load_kg() -> dict[str, Any]:
    with KG_PATH.open("r", encoding="utf-8") as f:
        kg = json.load(f)
    node_by_id = {node["id"]: node for node in kg["nodes"]}
    children_of: dict[str, list[dict[str, Any]]] = {}
    incoming: dict[str, list[dict[str, Any]]] = {}
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for node in kg["nodes"]:
        parent_id = node.get("parent_id")
        if parent_id:
            children_of.setdefault(parent_id, []).append(node)
    for edge in kg["edges"]:
        outgoing.setdefault(edge["source"], []).append(edge)
        incoming.setdefault(edge["target"], []).append(edge)
    kg["_node_by_id"] = node_by_id
    kg["_children_of"] = children_of
    kg["_incoming"] = incoming
    kg["_outgoing"] = outgoing

    # ---- 预计算词法索引：每个节点的 token 集合、辅助文本，以及全图 IDF ----
    doc_tokens: dict[str, set[str]] = {}
    aux_text: dict[str, str] = {}
    crumb_text: dict[str, str] = {}
    for node in kg["nodes"]:
        crumb = " / ".join(breadcrumb(node, node_by_id))
        doc_tokens[node["id"]] = tokens(node_text(node, kg))
        aux_text[node["id"]] = node.get("summary", "") + " " + crumb
        crumb_text[node["id"]] = crumb
    df: dict[str, int] = {}
    for toks in doc_tokens.values():
        for token in toks:
            df[token] = df.get(token, 0) + 1
    total_docs = len(kg["nodes"]) or 1
    kg["_doc_tokens"] = doc_tokens
    kg["_aux_text"] = aux_text
    kg["_crumb_text"] = crumb_text
    kg["_idf"] = {token: math.log(1.0 + total_docs / count) for token, count in df.items()}
    return kg


def breadcrumb(node: dict[str, Any], node_by_id: dict[str, dict[str, Any]]) -> list[str]:
    chain = []
    cursor = node
    while cursor:
        chain.insert(0, cursor["name"])
        parent_id = cursor.get("parent_id")
        if not parent_id:
            break
        cursor = node_by_id.get(parent_id)
    return chain


def chinese_ngrams(text: str) -> set[str]:
    chunks = re.findall(r"[\u4e00-\u9fff]+", text)
    grams: set[str] = set()
    for chunk in chunks:
        for n in (2, 3, 4):
            if len(chunk) < n:
                continue
            for i in range(len(chunk) - n + 1):
                grams.add(chunk[i:i + n])
    return grams


def tokens(text: str) -> set[str]:
    text = text.lower()
    # \u62c9\u4e01\u8bcd / \u6570\u5b57\u4fdd\u7559\uff1b\u4e2d\u6587\u4e0d\u53d6\u5355\u5b57\uff08\u566a\u58f0\u5927\uff09\uff0c\u53ea\u7528 2~4 gram \u53c2\u4e0e\u5339\u914d\u3002
    found = set(re.findall(r"[a-z]+|\d+(?:\.\d+)?", text))
    found.update(chinese_ngrams(text))
    return found


# 结构特征 → 概念关键词。每条规则在题面命中后，会把对应关键词去匹配
# 图谱节点的真实名称 / summary，从而替代过去写死的 node-id 加分。
# 关键词必须是 data/kg.json 中真实存在的节点名片段，否则不产生作用。
CONCEPT_RULES: list[tuple[Any, list[str]]] = [
    # 分段函数 / 在特殊点用定义求导
    (
        lambda q, ql: (
            "\\begin{cases}" in q
            or "分段" in ql
            or "cases" in ql
            or bool(re.search(r"在.{0,10}处.{0,8}导", ql))
            or ("导" in ql and ("x=0" in ql or "x = 0" in ql or "在0" in ql or "在 0" in ql))
        ),
        ["导数的定义", "单侧导数", "左导数", "右导数", "可导与连续", "由定义求导", "分段函数"],
    ),
    # 振荡型极限 sin(1/x)
    (
        lambda q, ql: ("1/x" in ql and "sin" in ql) or "sin(1/x)" in ql or "振荡" in ql,
        ["夹逼", "无穷小", "函数极限", "有界"],
    ),
    # 瑕积分 / 广义（反常）积分 / 奇点
    (
        lambda q, ql: "瑕" in ql or "广义积分" in ql or "反常积分" in ql,
        ["瑕积分", "广义积分", "牛顿-莱布尼茨", "收敛"],
    ),
    # 交错级数 / 绝对收敛 / 条件收敛
    (
        lambda q, ql: (
            "交错" in ql
            or "绝对收敛" in ql
            or "条件收敛" in ql
            or bool(re.search(r"\(-1\)\s*\^?\s*\{?\s*n", ql))
        ),
        ["交错级数", "Leibniz判别", "莱布尼茨判别", "绝对收敛", "条件收敛", "正项级数"],
    ),
    # 泰勒 / 高阶（高次分母）极限
    (
        lambda q, ql: (
            "泰勒" in ql
            or "麦克劳林" in ql
            or "taylor" in ql
            or (
                ("lim" in ql or "极限" in ql)
                and bool(re.search(r"x\s*[\^⁴⁵⁶]|x\^?\{?[4-9]", ql))
            )
        ),
        ["泰勒公式", "麦克劳林", "Peano余项", "等价无穷小", "洛必达法则", "Taylor公式", "Maclaruin余项"],
    ),
    # 二阶 / 高阶导数 与 复合函数求导
    (
        lambda q, ql: (
            "二阶导" in ql
            or "高阶导" in ql
            or "d^2" in ql
            or "d²" in ql
            or "f''" in ql
            or "f′′" in ql
        ),
        ["高阶导数", "复合函数求导", "链式法则", "复合函数高阶导数"],
    ),
    (
        lambda q, ql: (
            "复合" in ql
            or ("导" in ql and bool(re.search(r"(ln|sin|cos|exp|e\^)\s*\(", ql)))
        ),
        ["复合函数求导", "链式法则", "复合函数的极限"],
    ),
    # 洛必达
    (
        lambda q, ql: "洛必达" in ql or "l'hop" in ql or "0/0" in ql or "∞/∞" in ql,
        ["洛必达法则"],
    ),
    # 微分中值定理
    (
        lambda q, ql: "中值" in ql or "罗尔" in ql or "拉格朗日" in ql or "柯西中值" in ql,
        ["拉格朗日中值定理", "柯西中值定理", "罗尔定理", "微分中值定理"],
    ),
]


def concept_signals(question: str) -> set[str]:
    """根据题面结构特征，返回应当加权的概念关键词集合。"""
    q_lower = question.lower()
    keywords: set[str] = set()
    for trigger, words in CONCEPT_RULES:
        try:
            if trigger(question, q_lower):
                keywords.update(words)
        except re.error:
            continue
    return keywords


def domain_scope(question: str) -> set[str]:
    """判断题目宏观领域，用于消解“级数 / 积分”等同名考点的章节歧义。

    例如“绝对收敛 / 条件收敛 / Abel 判别”在广义积分章与级数章同时存在，
    仅凭概念关键词无法区分，需要结合题面是 ∑（级数）还是 ∫（积分）。
    """
    ql = question.lower()
    scope: set[str] = set()
    if "级数" in ql or "∑" in ql or "\\sum" in ql or "数项" in ql:
        scope.add("级数")
    if (
        "积分" in ql or "∫" in ql or "\\int" in ql
        or "瑕" in ql or "广义" in ql or "反常" in ql
    ):
        scope.add("积分")
    return scope


def node_text(node: dict[str, Any], kg: dict[str, Any]) -> str:
    node_by_id = kg["_node_by_id"]
    parts = [
        node.get("name", ""),
        node.get("summary", ""),
        " / ".join(breadcrumb(node, node_by_id)),
    ]
    for edge in (kg["_incoming"].get(node["id"], []) + kg["_outgoing"].get(node["id"], []))[:12]:
        parts.append(edge.get("note", ""))
    return " ".join(parts)


def retrieve_candidates(question: str, kg: dict[str, Any], limit: int = 36) -> list[dict[str, Any]]:
    q_lower = question.lower()
    q_tokens = tokens(question)
    idf = kg["_idf"]
    doc_tokens = kg["_doc_tokens"]
    aux_text = kg["_aux_text"]
    concept_kw = concept_signals(question)
    scope = domain_scope(question)
    crumb_text = kg["_crumb_text"]
    scored: list[tuple[float, dict[str, Any]]] = []

    for node in kg["nodes"]:
        node_id = node["id"]
        name = node["name"]
        name_lower = name.lower()
        n_tokens = doc_tokens.get(node_id, set())
        score = 0.0

        # (1) IDF 加权的词项重合：稀有词（如“条件收敛”）权重高，
        #     高频词（如“函数”“求”）权重自动趋近 0。
        for token in (q_tokens & n_tokens):
            weight = min(idf.get(token, 0.0), 6.5)
            score += weight * (1.7 if len(token) >= 2 else 0.45)

        # (2) 节点名整体出现在题面中（强信号，但短名（≤2 字）降权避免误命中）。
        if name_lower and name_lower in q_lower:
            score += 14.0 if len(name) >= 3 else 4.0

        # (3) 结构特征 → 概念关键词，匹配真实节点文本（取代写死的 node-id 加分）。
        if concept_kw:
            blob = aux_text.get(node_id, "")
            for keyword in concept_kw:
                if keyword in name:
                    score += 9.0
                elif keyword in blob:
                    score += 3.2

        # (4) 领域消歧：题面是级数还是积分，据此对节点所在章节路径加权/降权。
        if score > 0 and scope:
            crumb = crumb_text.get(node_id, "")
            if "级数" in scope and "级数" in crumb:
                score *= 1.25
            if "积分" in scope and "积分" in crumb:
                score *= 1.25
            if "级数" in scope and "积分" not in scope and "积分" in crumb:
                score *= 0.7
            if "积分" in scope and "级数" not in scope and "级数" in crumb:
                score *= 0.7

        # (5) 层级先验：偏向“知识点/节”，弱化“册/根”。
        level = int(node.get("level", 0))
        if level >= 4:
            score *= 1.15
        elif level == 3:
            score *= 1.05
        elif level <= 1:
            score *= 0.5

        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected: dict[str, float] = {}
    for score, node in scored[:limit]:
        selected[node["id"]] = max(selected.get(node["id"], 0), score)

    # 取强命中节点的 1 跳邻居，让 LLM 能选到非字面命中的前置/应用节点。
    for score, node in scored[:8]:
        for edge in kg["_incoming"].get(node["id"], []) + kg["_outgoing"].get(node["id"], []):
            other_id = edge["source"] if edge["target"] == node["id"] else edge["target"]
            selected[other_id] = max(selected.get(other_id, 0), score * 0.4)

    ranked = sorted(selected.items(), key=lambda item: item[1], reverse=True)[:limit]
    top_score = ranked[0][1] if ranked else 1.0
    out = []
    for node_id, score in ranked:
        node = kg["_node_by_id"][node_id]
        out.append({
            "id": node_id,
            "name": node["name"],
            "level": node.get("level"),
            "summary": node.get("summary", ""),
            "breadcrumb": " / ".join(breadcrumb(node, kg["_node_by_id"])),
            "score": round(score / top_score * 100, 1),
        })
    return out


def call_ollama(prompt: str, model: str, ollama_url: str, timeout: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0, "top_p": 0.85},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body.get("response", "")


def list_ollama_models(ollama_url: str, timeout: int = 5) -> list[str]:
    req = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/tags",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read().decode("utf-8"))
    names = []
    for item in body.get("models", []):
        name = item.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return sorted(set(names))


def extract_json(text: str) -> dict[str, Any] | None:
    text = clean_model_json_text(text)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(clean_json_candidate(text[start:end + 1]))
    except json.JSONDecodeError:
        return None


def clean_model_json_text(text: str) -> str:
    text = text.strip().lstrip("\ufeff")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()
    return clean_json_candidate(text)


def clean_json_candidate(text: str) -> str:
    # Tolerate the two most common LLM JSON mistakes.
    text = text.strip()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def normalize_weights(items: list[dict[str, Any]]) -> None:
    weights = []
    for item in items:
        try:
            weight = int(item.get("weight", 1))
        except (TypeError, ValueError):
            weight = 1
        weights.append(max(1, min(weight, 100)))
    total = sum(weights) or 1
    normalized = [max(1, int(round(w / total * 100))) for w in weights]
    drift = 100 - sum(normalized)
    if normalized:
        normalized[0] += drift
    for item, weight in zip(items, normalized):
        item["weight"] = max(1, weight)


def graph_evidence(node_ids: list[str], kg: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    selected = set(node_ids)
    edges = []
    for edge in kg["edges"]:
        if edge["source"] in selected and edge["target"] in selected:
            source = kg["_node_by_id"].get(edge["source"])
            target = kg["_node_by_id"].get(edge["target"])
            if not source or not target:
                continue
            edges.append({
                "source": edge["source"],
                "source_name": source["name"],
                "target": edge["target"],
                "target_name": target["name"],
                "type": edge["type"],
                "label": RELATION_LABELS.get(edge["type"], edge["type"]),
                "note": edge.get("note", ""),
            })
    return edges[:limit]


def fallback_analysis(question: str, candidates: list[dict[str, Any]], kg: dict[str, Any], warning: str) -> dict[str, Any]:
    chosen = candidates[:6]
    total = sum(max(c["score"], 1) for c in chosen) or 1
    nodes = []
    for c in chosen:
        node = kg["_node_by_id"][c["id"]]
        weight = max(1, int(round(max(c["score"], 1) / total * 100)))
        nodes.append({
            "id": c["id"],
            "name": node["name"],
            "level": node.get("level"),
            "breadcrumb": c["breadcrumb"],
            "summary": node.get("summary", ""),
            "weight": weight,
            "role": "候选考点",
            "reason": "由题面关键词、节点简介和图谱邻域的文本特征匹配得到。",
        })
    normalize_weights(nodes)
    route = [item["id"] for item in nodes[:5]]
    return {
        "mode": "fallback",
        "warning": warning,
        "condition_check": "当前未成功调用 Ollama，先按图谱文本匹配结果给出候选考点；请人工检查题目条件是否完整。",
        "diagnosis": "这是基于知识图谱节点文本和邻域关系的本地候选分析，未使用大模型生成解释。",
        "nodes": nodes,
        "route": route,
        "solution_steps": [
            "先确认题目条件是否完整，尤其是特殊点处的函数定义。",
            "从权重最高的知识点开始回顾定义、判定方法和典型题型。",
            "沿图谱中的前置和应用关系补齐相关知识。"
        ],
        "mistakes": ["未启动 Ollama 或模型响应超时会触发该降级结果。"],
        "graph_evidence": graph_evidence(route, kg),
        "candidate_count": len(candidates),
    }


def constrained_analysis(
    question: str,
    kg: dict[str, Any],
    model: str,
    ollama_url: str,
    timeout: int,
    top_k: int,
) -> dict[str, Any]:
    candidates = retrieve_candidates(question, kg, limit=top_k)
    if not candidates:
        return {
            "mode": "empty",
            "warning": "没有从知识图谱中检索到候选知识点。",
            "condition_check": "请检查题目是否属于当前数学分析知识图谱范围。",
            "diagnosis": "未命中可用知识点。",
            "nodes": [],
            "route": [],
            "solution_steps": [],
            "mistakes": [],
            "graph_evidence": [],
            "candidate_count": 0,
        }

    prompt = PROMPT_TEMPLATE.format(
        question=question,
        candidates=json.dumps(candidates, ensure_ascii=False, indent=2),
    )
    try:
        raw = call_ollama(prompt, model, ollama_url, timeout)
        parsed = extract_json(raw)
        if not parsed:
            preview = raw.replace("\n", " ")[:180]
            raise ValueError(f"Ollama 没有返回可解析的 JSON。原始输出开头：{preview}")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return fallback_analysis(question, candidates, kg, f"Ollama 调用失败：{exc}")

    candidate_by_id = {item["id"]: item for item in candidates}
    nodes = []
    for item in parsed.get("nodes", []):
        node_id = str(item.get("id", "")).strip()
        if node_id not in candidate_by_id:
            continue
        node = kg["_node_by_id"][node_id]
        nodes.append({
            "id": node_id,
            "name": node["name"],
            "level": node.get("level"),
            "breadcrumb": candidate_by_id[node_id]["breadcrumb"],
            "summary": node.get("summary", ""),
            "weight": item.get("weight", 1),
            "role": str(item.get("role", "考点"))[:24],
            "reason": str(item.get("reason", ""))[:220],
        })
        if len(nodes) >= 8:
            break
    if not nodes:
        return fallback_analysis(question, candidates, kg, "LLM 返回的节点 ID 均不在候选列表内，已降级为本地匹配。")
    normalize_weights(nodes)

    allowed_ids = set(candidate_by_id) | {item["id"] for item in nodes}
    route = []
    for node_id in parsed.get("route", []):
        node_id = str(node_id).strip()
        if node_id in allowed_ids and node_id not in route:
            route.append(node_id)
        if len(route) >= 6:
            break
    if not route:
        route = [item["id"] for item in nodes[:5]]

    return {
        "mode": "ollama",
        "warning": "",
        "condition_check": str(parsed.get("condition_check", ""))[:320],
        "diagnosis": str(parsed.get("diagnosis", ""))[:520],
        "nodes": nodes,
        "route": route,
        "solution_steps": [str(x)[:220] for x in parsed.get("solution_steps", [])[:8]],
        "mistakes": [str(x)[:220] for x in parsed.get("mistakes", [])[:8]],
        "graph_evidence": graph_evidence([item["id"] for item in nodes] + route, kg),
        "candidate_count": len(candidates),
    }


class AnalyzerHandler(SimpleHTTPRequestHandler):
    kg: dict[str, Any]
    default_model: str
    ollama_url: str
    timeout: int
    top_k: int

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/models":
            try:
                models = list_ollama_models(self.ollama_url)
                self.send_json({"models": models, "default_model": self.default_model})
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self.send_json({
                    "models": [self.default_model],
                    "default_model": self.default_model,
                    "warning": f"无法读取 Ollama 模型列表：{exc}",
                })
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/analyze-problem":
            self.send_error(404, "Unknown API")
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "请求体不是合法 JSON。"}, status=400)
            return
        question = str(payload.get("question", "")).strip()
        if not question:
            self.send_json({"error": "question 不能为空。"}, status=400)
            return
        model = str(payload.get("model") or self.default_model)
        try:
            top_k = int(payload.get("top_k") or self.top_k)
        except (TypeError, ValueError):
            top_k = self.top_k
        top_k = max(12, min(top_k, 60))
        result = constrained_analysis(
            question=question,
            kg=self.kg,
            model=model,
            ollama_url=self.ollama_url,
            timeout=self.timeout,
            top_k=top_k,
        )
        result["question"] = question
        result["model"] = model
        self.send_json(result)

    def send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="KG-constrained local problem analyzer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("OLLAMA_TIMEOUT", "300")))
    parser.add_argument("--top-k", type=int, default=36)
    args = parser.parse_args()

    os.chdir(ROOT)
    handler = AnalyzerHandler
    handler.kg = load_kg()
    handler.default_model = args.model
    handler.ollama_url = args.ollama_url
    handler.timeout = args.timeout
    handler.top_k = args.top_k

    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"知识图谱错题分析助手: http://{args.host}:{args.port}/viewer/")
    print(f"Ollama: {args.ollama_url} · model={args.model}")
    print("按 Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
