let appData = null;
let selectedNodeId = "";
let tableFilter = "all";

const byId = (id) => document.getElementById(id);

const els = {
  refreshButton: byId("refreshButton"),
  nodeSearch: byId("nodeSearch"),
  stats: byId("stats"),
  candidateState: byId("candidateState"),
  nodeList: byId("nodeList"),
  selectedTitle: byId("selectedTitle"),
  selectedMeta: byId("selectedMeta"),
  contextPanel: byId("contextPanel"),
  candidateButton: byId("candidateButton"),
  annotationForm: byId("annotationForm"),
  startNode: byId("startNode"),
  endNode: byId("endNode"),
  relationType: byId("relationType"),
  status: byId("status"),
  confidence: byId("confidence"),
  annotator: byId("annotator"),
  humanLabel: byId("humanLabel"),
  errorType: byId("errorType"),
  note: byId("note"),
  humanNote: byId("humanNote"),
  annotationTable: byId("annotationTable"),
  exportButton: byId("exportButton"),
  importCandidatesButton: byId("importCandidatesButton"),
  exportGoldButton: byId("exportGoldButton"),
  addNodeButton: byId("addNodeButton"),
  editNodeButton: byId("editNodeButton"),
  deleteNodeButton: byId("deleteNodeButton"),
  undoButton: byId("undoButton"),
  redoButton: byId("redoButton"),
  saveButton: byId("saveButton"),
  nodeDialog: byId("nodeDialog"),
  nodeForm: byId("nodeForm"),
  nodeId: byId("nodeId"),
  nodeName: byId("nodeName"),
  nodeLevel: byId("nodeLevel"),
  nodeParent: byId("nodeParent"),
  nodeCourse: byId("nodeCourse"),
  saveNodeButton: byId("saveNodeButton"),
  relationTypeDialog: byId("relationTypeDialog"),
  addRelationTypeButton: byId("addRelationTypeButton"),
  relationTypeForm: byId("relationTypeForm"),
  customRelationType: byId("customRelationType"),
  saveRelationTypeButton: byId("saveRelationTypeButton"),
  toast: byId("toast"),
};

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.setTimeout(() => els.toast.classList.remove("show"), 2200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function nodeById(id) {
  return appData.nodes.find((node) => node.id === id);
}

function nodeName(id) {
  return nodeById(id)?.name || id;
}

function filteredNodes() {
  const keyword = els.nodeSearch.value.trim().toLowerCase();
  if (!keyword) return appData.nodes;
  return appData.nodes.filter((node) => {
    return [node.id, node.name, node.course_name, node.parent_name]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword));
  });
}

function renderStats() {
  const stats = appData.stats;
  els.stats.innerHTML = [
    ["原始节点", stats.original_nodes],
    ["自定义节点", stats.custom_nodes],
    ["原始关系", stats.original_relationships],
    ["已接受", stats.accepted_annotations],
  ]
    .map(([label, value]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`)
    .join("");
  els.candidateState.innerHTML = `
    <strong>候选文件</strong>
    <span>${stats.candidate_file_exists ? "已检测到" : "未检测到"} · ${escapeHtml(stats.candidate_file)}</span>
    <span>已导入 AI 候选：${stats.ai_candidates_loaded}</span>
  `;
}

function renderNodeList() {
  els.nodeList.innerHTML = filteredNodes()
    .map((node) => {
      const active = node.id === selectedNodeId ? "active" : "";
      return `<button class="node-item ${active}" data-node-id="${node.id}">
        <strong>${escapeHtml(node.name)}</strong>
        <span>L${escapeHtml(node.level || "?")} · ${escapeHtml(node.parent_name || "根节点")} · 子节点 ${node.child_count}</span>
      </button>`;
    })
    .join("");
}

function relatedOriginals(nodeId) {
  return appData.original_relationships.filter((rel) => rel.start_id === nodeId || rel.end_id === nodeId);
}

function renderContext() {
  const node = nodeById(selectedNodeId);
  if (!node) {
    els.selectedTitle.textContent = "选择一个知识点";
    els.selectedMeta.textContent = "查看原始层级关系，审核或新增数学语义关系。";
    els.contextPanel.innerHTML = "";
    return;
  }

  els.selectedTitle.textContent = node.name;
  els.selectedMeta.textContent = `ID ${node.id} · Level ${node.level || "?"} · ${node.course_name || "未填写课程名"}`;

  const originals = relatedOriginals(node.id);
  const parents = originals.filter((rel) => rel.end_id === node.id && rel.type === "CONTAINS");
  const children = originals.filter((rel) => rel.start_id === node.id && rel.type === "CONTAINS");
  const annotations = appData.annotations.filter((rel) => rel.start_id === node.id || rel.end_id === node.id);

  els.contextPanel.innerHTML = [
    contextGroup("父节点", parents.map((rel) => rel.start_name)),
    contextGroup("子节点", children.map((rel) => rel.end_name)),
    contextGroup("相关人工关系", annotations.map((rel) => `${rel.start_name} ${rel.type} ${rel.end_name}`)),
  ].join("");

  els.startNode.value = node.id;
  els.editNodeButton.disabled = node.source !== "custom";
  els.deleteNodeButton.disabled = node.source !== "custom";
}

function contextGroup(title, values) {
  const chips = values.length
    ? values.map((value) => `<span class="chip">${escapeHtml(value)}</span>`).join("")
    : `<span class="chip">暂无</span>`;
  return `<div class="context-group"><h4>${title}</h4><div class="chips">${chips}</div></div>`;
}

function renderSelects() {
  const options = appData.nodes
    .map((node) => `<option value="${node.id}">${escapeHtml(node.name)} · L${escapeHtml(node.level || "?")}</option>`)
    .join("");
  const parentOptions = `<option value="">无父节点</option>${options}`;
  const typeOptions = appData.relation_types
    .map((type) => `<option value="${type}">${escapeHtml(type)}</option>`)
    .join("");
  const humanLabelOptions = `<option value="">沿用 AI 标签</option>${typeOptions}`;
  const errorTypeOptions = appData.error_types
    .map((type) => `<option value="${type}">${escapeHtml(type || "无")}</option>`)
    .join("");
  els.startNode.innerHTML = options;
  els.endNode.innerHTML = options;
  els.nodeParent.innerHTML = parentOptions;
  els.relationType.innerHTML = typeOptions;
  els.humanLabel.innerHTML = humanLabelOptions;
  els.errorType.innerHTML = errorTypeOptions;
  if (selectedNodeId) {
    els.startNode.value = selectedNodeId;
  }
}

function renderTable() {
  const rows = appData.annotations
    .filter((item) => tableFilter === "all" || item.status === tableFilter)
    .map((item) => `<tr>
      <td>${escapeHtml(item.start_name || nodeName(item.start_id))}</td>
      <td>${escapeHtml(item.type)}</td>
      <td>${escapeHtml(item.end_name || nodeName(item.end_id))}</td>
      <td><span class="status ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
      <td>${escapeHtml(item.confidence || "")}</td>
      <td>${escapeHtml(item.source || "")}</td>
      <td>${escapeHtml(item.human_label || "")}</td>
      <td>${escapeHtml(item.error_type || "")}</td>
      <td>${escapeHtml(item.note || "")}</td>
      <td>
        <div class="row-actions">
          <button data-action="accepted" data-id="${item.id}">接受</button>
          <button data-action="pending" data-id="${item.id}">待审</button>
          <button data-action="rejected" data-id="${item.id}">拒绝</button>
          <button data-action="edit" data-id="${item.id}">编辑</button>
        </div>
      </td>
    </tr>`)
    .join("");
  els.annotationTable.innerHTML = rows || `<tr><td colspan="10">暂无标注。先选择节点生成候选，或手动新增关系。</td></tr>`;
}

function render() {
  renderStats();
  renderNodeList();
  renderSelects();
  renderContext();
  renderTable();
}

async function loadData() {
  appData = await api("/api/data");
  if (!selectedNodeId && appData.nodes.length) {
    selectedNodeId = appData.nodes[0].id;
  }
  render();
}

async function saveAnnotation(annotation) {
  await api("/api/annotation", {
    method: "POST",
    body: JSON.stringify({ annotation }),
  });
  await loadData();
}

async function saveBulk(annotations) {
  await api("/api/annotations/bulk", {
    method: "POST",
    body: JSON.stringify({ annotations }),
  });
  await loadData();
}

function formAnnotation() {
  return {
    id: `ann-${crypto.randomUUID().slice(0, 12)}`,
    start_id: els.startNode.value,
    end_id: els.endNode.value,
    type: els.relationType.value,
    status: els.status.value,
    confidence: els.confidence.value,
    source: "manual",
    annotator: els.annotator.value.trim(),
    human_label: els.humanLabel.value,
    human_decision: els.status.value === "accepted" ? "accepted" : els.status.value === "rejected" ? "rejected" : "",
    error_type: els.errorType.value,
    note: els.note.value.trim(),
    human_note: els.humanNote.value.trim(),
  };
}

function editAnnotation(item) {
  els.startNode.value = item.start_id;
  els.endNode.value = item.end_id;
  els.relationType.value = item.type;
  els.status.value = item.status;
  els.confidence.value = item.confidence || "";
  els.annotator.value = item.annotator || "";
  els.humanLabel.value = item.human_label || "";
  els.errorType.value = item.error_type || "";
  els.note.value = item.note || "";
  els.humanNote.value = item.human_note || "";
  els.annotationForm.dataset.editId = item.id;
  toast("已载入到表单，修改后点击保存关系");
}

function clearForm() {
  delete els.annotationForm.dataset.editId;
  els.status.value = "accepted";
  els.confidence.value = "";
  els.note.value = "";
  els.humanLabel.value = "";
  els.errorType.value = "";
  els.humanNote.value = "";
  if (selectedNodeId) els.startNode.value = selectedNodeId;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

els.refreshButton.addEventListener("click", () => loadData().then(() => toast("已刷新")));
els.nodeSearch.addEventListener("input", renderNodeList);

els.nodeList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-node-id]");
  if (!button) return;
  selectedNodeId = button.dataset.nodeId;
  render();
});

els.annotationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const annotation = formAnnotation();
  if (els.annotationForm.dataset.editId) {
    annotation.id = els.annotationForm.dataset.editId;
  }
  await saveAnnotation(annotation);
  clearForm();
  toast("关系已保存");
});

els.candidateButton.addEventListener("click", async () => {
  if (!selectedNodeId) return;
  const payload = await api(`/api/candidates?node_id=${encodeURIComponent(selectedNodeId)}`);
  if (!payload.candidates.length) {
    toast("当前节点没有新的规则候选");
    return;
  }
  await saveBulk(payload.candidates);
  toast(`已生成 ${payload.candidates.length} 条候选`);
});

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    tableFilter = button.dataset.filter;
    renderTable();
  });
});

els.annotationTable.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const item = appData.annotations.find((annotation) => annotation.id === button.dataset.id);
  if (!item) return;
  if (button.dataset.action === "edit") {
    editAnnotation(item);
    return;
  }
  await saveAnnotation({ ...item, status: button.dataset.action });
  toast(`已标记为 ${button.dataset.action}`);
});

els.exportButton.addEventListener("click", async () => {
  const result = await api("/api/export", { method: "POST", body: "{}" });
  toast(`已导出：${result.relationships_csv}`);
});

els.importCandidatesButton.addEventListener("click", async () => {
  const result = await api("/api/import-candidates", { method: "POST", body: "{}" });
  if (!result.ok) {
    toast(result.message || "没有找到候选关系 CSV");
    return;
  }
  await loadData();
  toast(`已导入 ${result.count} 条候选`);
});

els.exportGoldButton.addEventListener("click", async () => {
  const result = await api("/api/export-gold", { method: "POST", body: "{}" });
  toast(`Gold Set 已导出：${result.count} 条`);
});

els.saveButton.addEventListener("click", async () => {
  const result = await api("/api/save", { method: "POST", body: "{}" });
  toast(`进度快照已保存：${result.snapshot}`);
});

els.undoButton.addEventListener("click", async () => {
  const result = await api("/api/undo", { method: "POST", body: "{}" });
  if (!result.ok) {
    toast("没有可撤销的操作");
    return;
  }
  await loadData();
  toast("已撤销上一步操作");
});

els.redoButton.addEventListener("click", async () => {
  const result = await api("/api/redo", { method: "POST", body: "{}" });
  if (!result.ok) {
    toast("没有可反撤销的操作");
    return;
  }
  await loadData();
  toast("已恢复撤销的操作");
});

els.addNodeButton.addEventListener("click", () => {
  els.nodeId.value = "";
  els.nodeName.value = "";
  els.nodeLevel.value = "";
  els.nodeParent.value = selectedNodeId || "";
  els.nodeCourse.value = nodeById(selectedNodeId)?.course_name || appData.nodes[0]?.course_name || "";
  els.nodeDialog.showModal();
});

els.editNodeButton.addEventListener("click", () => {
  const node = nodeById(selectedNodeId);
  if (!node || node.source !== "custom") {
    toast("当前版本只允许编辑 UI 创建的自定义节点");
    return;
  }
  els.nodeId.value = node.id;
  els.nodeName.value = node.name;
  els.nodeLevel.value = node.level || "";
  els.nodeParent.value = node.parent_id || "";
  els.nodeCourse.value = node.course_name || "";
  els.nodeDialog.showModal();
});

els.deleteNodeButton.addEventListener("click", async () => {
  const node = nodeById(selectedNodeId);
  if (!node || node.source !== "custom") {
    toast("当前版本只允许删除 UI 创建的自定义节点");
    return;
  }
  const ok = window.confirm(`确认删除自定义节点「${node.name}」？相关人工关系不会自动删除。`);
  if (!ok) return;
  await api("/api/node", {
    method: "POST",
    body: JSON.stringify({
      node: {
        "node_id:ID": node.id,
        _deleted: "true",
      },
    }),
  });
  selectedNodeId = appData.nodes[0]?.id || "";
  await loadData();
  toast("自定义节点已删除");
});

els.nodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const parent = nodeById(els.nodeParent.value);
  const node = {
    "node_id:ID": els.nodeId.value || `custom-${crypto.randomUUID().slice(0, 10)}`,
    name: els.nodeName.value.trim(),
    "level:int": els.nodeLevel.value || (parent?.level ? String(Number(parent.level) + 1) : ""),
    parent_id: els.nodeParent.value,
    course_name: els.nodeCourse.value.trim(),
    ":LABEL": "KnowledgePoint",
  };
  await api("/api/node", { method: "POST", body: JSON.stringify({ node }) });
  els.nodeDialog.close();
  await loadData();
  selectedNodeId = node["node_id:ID"];
  render();
  toast(els.nodeId.value ? "节点已更新" : "节点已创建");
});

els.addRelationTypeButton.addEventListener("click", () => {
  els.customRelationType.value = "";
  els.relationTypeDialog.showModal();
});

els.relationTypeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const type = els.customRelationType.value.trim().toUpperCase();
  if (!type) return;
  await api("/api/relation-type", { method: "POST", body: JSON.stringify({ type }) });
  els.relationTypeDialog.close();
  await loadData();
  els.relationType.value = type;
  toast("关系类型已添加");
});

loadData().catch((error) => {
  console.error(error);
  toast("加载失败，请查看终端输出");
});
