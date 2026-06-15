(function () {
  "use strict";

  const state = {
    kg: null,
    nodeById: new Map(),
    childrenOf: new Map(),
    outgoing: new Map(),
    incoming: new Map(),
    relationColor: new Map(),
    relationLabel: new Map(),
    relationOrder: [],
    selectedId: null,
    expanded: new Set(),
    enabledRelations: new Set(),
    includeContains: true,
    hop: 2,
    cy: null,
    analysisNodeIds: new Set(),
    analysisRouteIds: new Set(),
    queryNodeIds: new Set(),
    queryEdgeKeys: new Set(),
    edgeByKey: new Map(),
    queryPanelOpen: false,
    problemPanelOpen: true,
    problemAnalysisRunning: false,
  };

  const RELATION_UI = {
    PREREQUISITE_OF: { label: "前置", desc: "A 是理解 B 的前置知识。" },
    USED_IN: { label: "应用于", desc: "A 是证明、计算或理解 B 时会用到的工具。" },
    GENERALIZES: { label: "推广", desc: "A 是 B 的推广或更一般形式。" },
    SPECIAL_CASE_OF: { label: "特例", desc: "A 是 B 的特殊情形。" },
    SIMILAR_TO: { label: "类比", desc: "A 与 B 在方法、结构或思想上相似。" },
    EASILY_CONFUSED_WITH: { label: "易混淆", desc: "A 与 B 容易混淆，需要对比辨析。" },
    RELATED_TO: { label: "相关", desc: "A 与 B 有弱相关或辅助联系。" },
    CONTAINS: { label: "包含", desc: "层级父子（章 → 节 → 知识点）。" },
  };

  const dom = {
    tree: document.getElementById("tree"),
    detail: document.getElementById("detail"),
    legend: document.getElementById("relationLegend"),
    searchInput: document.getElementById("searchInput"),
    searchResults: document.getElementById("searchResults"),
    hopSelect: document.getElementById("hopSelect"),
    includeContainsToggle: document.getElementById("includeContainsToggle"),
    kgMeta: document.getElementById("kgMeta"),
    emptyHint: document.getElementById("emptyHint"),
    openQueryPanelBtn: document.getElementById("openQueryPanelBtn"),
    queryPanel: document.getElementById("queryPanel"),
    queryHead: document.querySelector("#queryPanel .query-head"),
    closeQueryPanelBtn: document.getElementById("closeQueryPanelBtn"),
    clearQueryBtn: document.getElementById("clearQueryBtn"),
    queryTabs: document.querySelectorAll("[data-query-tab]"),
    querySections: document.querySelectorAll("[data-query-section]"),
    nodeQueryInput: document.getElementById("nodeQueryInput"),
    runNodeQueryBtn: document.getElementById("runNodeQueryBtn"),
    edgeSourceInput: document.getElementById("edgeSourceInput"),
    edgeTypeSelect: document.getElementById("edgeTypeSelect"),
    edgeTargetInput: document.getElementById("edgeTargetInput"),
    runEdgeQueryBtn: document.getElementById("runEdgeQueryBtn"),
    pathStartInput: document.getElementById("pathStartInput"),
    pathEndInput: document.getElementById("pathEndInput"),
    pathMaxHopSelect: document.getElementById("pathMaxHopSelect"),
    runPathQueryBtn: document.getElementById("runPathQueryBtn"),
    queryStatus: document.getElementById("queryStatus"),
    queryResults: document.getElementById("queryResults"),
    openProblemAnalyzerBtn: document.getElementById("openProblemAnalyzerBtn"),
    problemAnalyzer: document.getElementById("problemAnalyzer"),
    problemHead: document.querySelector("#problemAnalyzer .problem-head"),
    problemInput: document.getElementById("problemInput"),
    problemModelInput: document.getElementById("problemModelInput"),
    refreshModelsBtn: document.getElementById("refreshModelsBtn"),
    analyzeProblemBtn: document.getElementById("analyzeProblemBtn"),
    clearAnalysisBtn: document.getElementById("clearAnalysisBtn"),
    closeProblemAnalyzerBtn: document.getElementById("closeProblemAnalyzerBtn"),
    analysisStatus: document.getElementById("analysisStatus"),
    analysisResult: document.getElementById("analysisResult"),
  };

  // ---------------- Bootstrap ----------------

  fetch("../data/kg.json")
    .then((res) => {
      if (!res.ok) throw new Error("无法加载 data/kg.json：" + res.status);
      return res.json();
    })
    .then(bootstrap)
    .catch((err) => {
      dom.kgMeta.textContent = "加载失败：" + err.message;
      console.error(err);
    });

  function bootstrap(kg) {
    state.kg = kg;
    kg.nodes.forEach((node) => state.nodeById.set(node.id, node));
    kg.nodes.forEach((node) => {
      if (node.parent_id) {
        if (!state.childrenOf.has(node.parent_id)) {
          state.childrenOf.set(node.parent_id, []);
        }
        state.childrenOf.get(node.parent_id).push(node);
      }
    });
    kg.edges.forEach((edge) => {
      if (!state.outgoing.has(edge.source)) state.outgoing.set(edge.source, []);
      if (!state.incoming.has(edge.target)) state.incoming.set(edge.target, []);
      state.outgoing.get(edge.source).push(edge);
      state.incoming.get(edge.target).push(edge);
      state.edgeByKey.set(edgeKey(edge), edge);
    });

    kg.relation_types.forEach((rt) => {
      state.relationColor.set(rt.key, rt.color);
      state.relationLabel.set(rt.key, relationLabel(rt.key, rt.label));
      state.relationOrder.push(rt.key);
      state.enabledRelations.add(rt.key);
    });

    dom.kgMeta.textContent = `${kg.course_name} · v${kg.version} · ${kg.stats.node_count} 节点 / ${kg.stats.edge_count} 关系`;

    initLegend();
    initDomainLegend();
    initTree();
    initCytoscape();
    initSearch();
    initHopControls();
    initQueryPanel();
    initProblemAnalyzer();
  }

  // ---------------- Legend ----------------

  function initLegend() {
    state.kg.relation_types.forEach((rt) => {
      if (rt.key === "CONTAINS") return; // 由顶部「显示层级」开关控制，不再在图例里重复
      const label = document.createElement("label");
      label.title = relationDescription(rt.key);
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;
      checkbox.dataset.relation = rt.key;
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.enabledRelations.add(rt.key);
        else state.enabledRelations.delete(rt.key);
        renderGraph();
      });
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = rt.color;
      const text = document.createElement("span");
      text.textContent = relationLabel(rt.key, rt.label);
      label.append(checkbox, swatch, text);
      dom.legend.append(label);
    });
  }

  function relationDescription(key) {
    return (RELATION_UI[key] && RELATION_UI[key].desc) || key;
  }

  function relationLabel(key, fallback) {
    return (RELATION_UI[key] && RELATION_UI[key].label) || fallback || key;
  }

  function initDomainLegend() {
    const container = document.getElementById("domainLegend");
    if (!container) return;
    state.kg.nodes
      .filter((n) => n.level === 1)
      .forEach((dom) => {
        const palette = DOMAIN_PALETTE[dom.id] || FALLBACK;
        const label = document.createElement("label");
        label.title = `点击在树中定位「${dom.name}」`;
        label.style.cursor = "pointer";
        const swatch = document.createElement("span");
        swatch.className = "swatch";
        swatch.style.background = palette.border;
        const text = document.createElement("span");
        text.textContent = dom.name;
        label.append(swatch, text);
        label.addEventListener("click", () => {
          expandAncestors(dom.id);
          selectNode(dom.id);
        });
        container.append(label);
      });
  }

  // ---------------- Tree ----------------

  function initTree() {
    const roots = state.kg.nodes.filter((node) => node.parent_id === null);
    roots.forEach((root) => state.expanded.add(root.id));
    // 默认展开 6 大主题领域
    state.kg.nodes
      .filter((n) => n.level === 1)
      .forEach((n) => state.expanded.add(n.id));
    renderTree();
  }

  function renderTree() {
    dom.tree.innerHTML = "";
    state.kg.nodes
      .filter((node) => node.parent_id === null)
      .forEach((root) => dom.tree.append(buildTreeNode(root)));
  }

  function buildTreeNode(node) {
    const li = document.createElement("li");
    const row = document.createElement("div");
    row.className = "tree-node";
    if (node.id === state.selectedId) row.classList.add("selected");

    const toggle = document.createElement("span");
    toggle.className = "toggle";
    const children = state.childrenOf.get(node.id) || [];
    if (children.length === 0) {
      toggle.classList.add("leaf");
      toggle.textContent = "·";
    } else {
      toggle.textContent = state.expanded.has(node.id) ? "▾" : "▸";
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        if (state.expanded.has(node.id)) state.expanded.delete(node.id);
        else state.expanded.add(node.id);
        renderTree();
      });
    }

    const name = document.createElement("span");
    name.className = "name";
    name.textContent = node.name;

    const badge = document.createElement("span");
    badge.className = "level-badge";
    badge.textContent = "L" + node.level;

    row.append(toggle, name, badge);
    row.addEventListener("click", () => selectNode(node.id));

    li.append(row);

    if (children.length > 0 && state.expanded.has(node.id)) {
      const ul = document.createElement("ul");
      children
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN"))
        .forEach((child) => ul.append(buildTreeNode(child)));
      li.append(ul);
    }

    return li;
  }

  // ---------------- Search ----------------

  function initSearch() {
    dom.searchInput.addEventListener("input", () => {
      const query = dom.searchInput.value.trim();
      if (!query) {
        dom.searchResults.hidden = true;
        dom.searchResults.innerHTML = "";
        return;
      }
      const lower = query.toLowerCase();
      const matches = state.kg.nodes
        .filter(
          (node) =>
            node.name.toLowerCase().includes(lower) ||
            (node.summary && node.summary.toLowerCase().includes(lower))
        )
        .slice(0, 30);
      dom.searchResults.innerHTML = "";
      if (matches.length === 0) {
        const empty = document.createElement("div");
        empty.className = "search-result-item";
        empty.textContent = "无匹配结果";
        empty.style.color = "var(--muted)";
        empty.style.cursor = "default";
        dom.searchResults.append(empty);
      } else {
        matches.forEach((node) => {
          const item = document.createElement("div");
          item.className = "search-result-item";
          item.textContent = `${node.name}  ·  L${node.level}`;
          item.addEventListener("click", () => {
            dom.searchInput.value = "";
            dom.searchResults.hidden = true;
            dom.searchResults.innerHTML = "";
            expandAncestors(node.id);
            selectNode(node.id);
          });
          dom.searchResults.append(item);
        });
      }
      dom.searchResults.hidden = false;
    });

    dom.searchInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      const first = dom.searchResults.querySelector(".search-result-item");
      if (first) first.click();
    });
  }

  function expandAncestors(nodeId) {
    let cursor = state.nodeById.get(nodeId);
    while (cursor && cursor.parent_id) {
      state.expanded.add(cursor.parent_id);
      cursor = state.nodeById.get(cursor.parent_id);
    }
  }

  // ---------------- Hop controls ----------------

  function initHopControls() {
    dom.hopSelect.addEventListener("change", () => {
      state.hop = Number(dom.hopSelect.value);
      renderGraph();
    });
    dom.includeContainsToggle.addEventListener("change", () => {
      state.includeContains = dom.includeContainsToggle.checked;
      renderGraph();
    });
  }

  // ---------------- Selection ----------------

  function selectNode(id) {
    state.selectedId = id;
    ensureUsefulHopFor(id);
    renderTree();
    renderGraph();
    renderDetail();
  }

  function ensureUsefulHopFor(id) {
    const node = state.nodeById.get(id);
    if (!node) return;
    let minHop = 1;
    if (node.level === 0) minHop = 3;
    else if (node.level === 1) minHop = 2;
    if (state.hop >= minHop) return;
    state.hop = minHop;
    dom.hopSelect.value = String(minHop);
  }

  // ---------------- Domain colors ----------------

  const DOMAIN_PALETTE = {
    ma:              { strong: "#1f2937", soft: "#f3f4f6", border: "#1f2937" },
    dom_foundation:  { strong: "#3b82f6", soft: "#eff6ff", border: "#60a5fa" },
    dom_diff_uni:    { strong: "#ea580c", soft: "#fff7ed", border: "#fb923c" },
    dom_int_uni:     { strong: "#059669", soft: "#ecfdf5", border: "#34d399" },
    dom_diff_multi:  { strong: "#7c3aed", soft: "#f5f3ff", border: "#a78bfa" },
    dom_int_multi:   { strong: "#e11d48", soft: "#fff1f2", border: "#fb7185" },
    dom_series_ode:  { strong: "#ca8a04", soft: "#fefce8", border: "#facc15" },
  };
  const FALLBACK = { strong: "#6b7280", soft: "#f9fafb", border: "#d1d5db" };

  function domainOf(node) {
    let cursor = node;
    while (cursor) {
      if (cursor.id === "ma" || cursor.id.startsWith("dom_")) return cursor.id;
      if (!cursor.parent_id) return "ma";
      cursor = state.nodeById.get(cursor.parent_id);
    }
    return "ma";
  }

  function nodeColors(node) {
    const dom = domainOf(node);
    const p = DOMAIN_PALETTE[dom] || FALLBACK;
    if (node.id === "ma") {
      // 根节点：深底白字
      return { bg: "#1f2937", border: "#1f2937", fg: "#ffffff" };
    }
    if (node.level === 1) {
      // 主题领域：彩底白字
      return { bg: p.border, border: p.border, fg: "#ffffff" };
    }
    if (node.level === 2) {
      // 章：浅底深色字 + 同色边框
      return { bg: "#ffffff", border: p.border, fg: p.strong };
    }
    // 节 + 知识点：极浅底 + 同色边框 + 深色字
    return { bg: p.soft, border: p.border, fg: p.strong };
  }

  // ---------------- Cytoscape ----------------

  function initCytoscape() {
    state.cy = cytoscape({
      container: document.getElementById("cy"),
      elements: [],
      style: cytoscapeStyle(),
      layout: { name: "cose", animate: false },
      wheelSensitivity: 0.25,
    });
    state.cy.on("tap", "node", (event) => {
      const id = event.target.id();
      expandAncestors(id);
      selectNode(id);
    });
  }

  function cytoscapeStyle() {
    return [
      {
        selector: "node",
        style: {
          shape: "round-rectangle",
          "background-color": "data(bg)",
          label: "data(name)",
          color: "data(fg)",
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "wrap",
          "text-max-width": 160,
          "font-size": 12,
          "font-weight": 500,
          "font-family": 'ui-sans-serif, system-ui, "PingFang SC", "Microsoft YaHei", sans-serif',
          width: "label",
          height: "label",
          "padding-left": 12,
          "padding-right": 12,
          "padding-top": 8,
          "padding-bottom": 8,
          "border-width": 1,
          "border-color": "data(border)",
          "border-opacity": 1,
        },
      },
      {
        // 根节点：数学分析
        selector: 'node[level = 0]',
        style: { "font-size": 16, "font-weight": 700, "padding-left": 18, "padding-right": 18, "padding-top": 12, "padding-bottom": 12 },
      },
      {
        // 主题领域 L1
        selector: 'node[level = 1]',
        style: { "font-size": 14, "font-weight": 600, "padding-left": 14, "padding-right": 14, "padding-top": 10, "padding-bottom": 10 },
      },
      {
        // 章 L2
        selector: 'node[level = 2]',
        style: { "font-size": 13, "font-weight": 600 },
      },
      {
        selector: "node.selected",
        style: {
          "background-color": "#fff7ed",
          "border-color": "#f59e0b",
          "border-width": 2.5,
          color: "#92400e",
          "font-weight": 700,
        },
      },
      {
        selector: "node.analysis-hit",
        style: {
          "background-color": "#fef08a",
          "border-color": "#111827",
          "border-width": 5,
          color: "#111827",
          "font-weight": 700,
          "shadow-blur": 18,
          "shadow-color": "#facc15",
          "shadow-opacity": 0.85,
          "shadow-offset-x": 0,
          "shadow-offset-y": 0,
          "underlay-color": "#facc15",
          "underlay-opacity": 0.24,
          "underlay-padding": 10,
        },
      },
      {
        selector: "node.analysis-route",
        style: {
          "background-color": "#ffe4e6",
          "border-color": "#be123c",
          "border-width": 5,
          color: "#881337",
          "font-weight": 700,
          "shadow-blur": 18,
          "shadow-color": "#fb7185",
          "shadow-opacity": 0.78,
          "shadow-offset-x": 0,
          "shadow-offset-y": 0,
          "underlay-color": "#fb7185",
          "underlay-opacity": 0.22,
          "underlay-padding": 10,
        },
      },
      {
        selector: "node.selected.analysis-hit, node.selected.analysis-route",
        style: {
          "border-color": "#f59e0b",
          "border-width": 6,
          color: "#111827",
        },
      },
      {
        selector: "node.query-hit",
        style: {
          "background-color": "#f5f3ff",
          "border-color": "#7c3aed",
          "border-width": 5,
          color: "#4c1d95",
          "font-weight": 700,
          "shadow-blur": 16,
          "shadow-color": "#a78bfa",
          "shadow-opacity": 0.72,
          "shadow-offset-x": 0,
          "shadow-offset-y": 0,
        },
      },
      {
        selector: "edge",
        style: {
          "curve-style": "bezier",
          width: 1.8,
          "line-color": "data(color)",
          "target-arrow-color": "data(color)",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.9,
          opacity: 0.82,
          label: "data(label)",
          "font-size": 10,
          "font-weight": 600,
          color: "#374151",
          "text-rotation": "autorotate",
          "text-background-color": "#faf9f7",
          "text-background-opacity": 1,
          "text-background-padding": 3,
          "text-background-shape": "round-rectangle",
          "text-margin-y": -4,
          "min-zoomed-font-size": 7,
        },
      },
      {
        selector: 'edge[type = "CONTAINS"]',
        style: { "line-style": "dashed", opacity: 0.3, label: "" },
      },
      {
        selector: "edge.analysis-edge",
        style: {
          width: 4.2,
          opacity: 1,
          "line-color": "#111827",
          "target-arrow-color": "#111827",
          "target-arrow-shape": "triangle",
          "z-index": 10,
        },
      },
      {
        selector: "edge.query-edge",
        style: {
          width: 4,
          opacity: 1,
          "line-color": "#7c3aed",
          "target-arrow-color": "#7c3aed",
          "line-style": "solid",
          "z-index": 11,
        },
      },
    ];
  }

  function renderGraph() {
    if (!state.cy) return;
    if (!state.selectedId) {
      state.cy.elements().remove();
      dom.emptyHint.classList.remove("hidden");
      return;
    }
    dom.emptyHint.classList.add("hidden");

    const nodeIds = collectNeighborhood(state.selectedId, state.hop);
    state.analysisNodeIds.forEach((id) => nodeIds.add(id));
    state.analysisRouteIds.forEach((id) => nodeIds.add(id));
    state.queryNodeIds.forEach((id) => nodeIds.add(id));
    state.queryEdgeKeys.forEach((key) => {
      const edge = state.edgeByKey.get(key);
      if (!edge) return;
      nodeIds.add(edge.source);
      nodeIds.add(edge.target);
    });
    const edges = collectEdges(nodeIds);
    state.queryEdgeKeys.forEach((key) => {
      const edge = state.edgeByKey.get(key);
      if (!edge) return;
      if (!edges.some((item) => edgeKey(item) === key)) edges.push(edge);
    });

    const elements = [];
    nodeIds.forEach((id) => {
      const node = state.nodeById.get(id);
      if (!node) return;
      const colors = nodeColors(node);
      const classes = [];
      if (node.id === state.selectedId) classes.push("selected");
      if (state.analysisNodeIds.has(node.id)) classes.push("analysis-hit");
      if (state.analysisRouteIds.has(node.id)) classes.push("analysis-route");
      if (state.queryNodeIds.has(node.id)) classes.push("query-hit");
      elements.push({
        data: {
          id: node.id,
          name: node.name,
          level: node.level,
          bg: colors.bg,
          border: colors.border,
          fg: colors.fg,
        },
        classes: classes.join(" "),
      });
    });
    edges.forEach((edge) => {
      const inAnalysis = state.analysisNodeIds.has(edge.source) && state.analysisNodeIds.has(edge.target);
      const key = edgeKey(edge);
      elements.push({
        data: {
          id: key,
          source: edge.source,
          target: edge.target,
          type: edge.type,
          color: state.relationColor.get(edge.type) || "#888",
          label: state.relationLabel.get(edge.type) || edge.type,
        },
        classes: [
          inAnalysis ? "analysis-edge" : "",
          state.queryEdgeKeys.has(key) ? "query-edge" : "",
        ].filter(Boolean).join(" "),
      });
    });

    state.cy.elements().remove();
    state.cy.resize();
    state.cy.add(elements);
    const layout = state.cy.layout({
      name: "cose",
      animate: false,
      nodeRepulsion: 12000,
      idealEdgeLength: 110,
      gravity: 0.2,
      padding: 40,
      randomize: false,
      fit: true,
    });
    layout.run();
    requestAnimationFrame(() => {
      state.cy.resize();
      state.cy.fit(undefined, 50);
      state.cy.center(state.cy.getElementById(state.selectedId));
    });
  }

  function collectNeighborhood(rootId, hop) {
    const visited = new Set([rootId]);
    let frontier = [rootId];
    for (let i = 0; i < hop; i++) {
      const next = [];
      frontier.forEach((id) => {
        gatherNeighbors(id).forEach((nbr) => {
          if (!visited.has(nbr)) {
            visited.add(nbr);
            next.push(nbr);
          }
        });
      });
      frontier = next;
    }
    return visited;
  }

  function gatherNeighbors(id) {
    const out = [];
    (state.outgoing.get(id) || []).forEach((edge) => {
      if (relationActive(edge.type)) out.push(edge.target);
    });
    (state.incoming.get(id) || []).forEach((edge) => {
      if (relationActive(edge.type)) out.push(edge.source);
    });
    if (state.includeContains) {
      const me = state.nodeById.get(id);
      if (me && me.parent_id && state.nodeById.has(me.parent_id)) out.push(me.parent_id);
      (state.childrenOf.get(id) || []).forEach((child) => out.push(child.id));
    }
    return out;
  }

  function collectEdges(nodeIds) {
    const set = nodeIds;
    const out = [];
    const seenKeys = new Set();
    state.kg.edges.forEach((edge) => {
      if (!set.has(edge.source) || !set.has(edge.target)) return;
      if (!relationActive(edge.type)) return;
      const key = edgeKey(edge);
      if (seenKeys.has(key)) return;
      seenKeys.add(key);
      out.push(edge);
    });
    if (state.includeContains) {
      set.forEach((id) => {
        const node = state.nodeById.get(id);
        if (node && node.parent_id && set.has(node.parent_id)) {
          const key = `${node.parent_id}->${node.id}::CONTAINS`;
          if (!seenKeys.has(key)) {
            seenKeys.add(key);
            out.push({ source: node.parent_id, target: node.id, type: "CONTAINS", note: "" });
          }
        }
      });
    }
    return out;
  }

  function edgeKey(edge) {
    return `${edge.source}->${edge.target}::${edge.type}`;
  }

  function relationActive(type) {
    if (type === "CONTAINS") return state.includeContains;
    return state.enabledRelations.has(type);
  }

  // ---------------- Query panel ----------------

  function initQueryPanel() {
    if (!dom.openQueryPanelBtn) return;
    fillEdgeTypeSelect();
    dom.openQueryPanelBtn.addEventListener("click", () => setQueryPanelOpen(true));
    dom.closeQueryPanelBtn.addEventListener("click", () => setQueryPanelOpen(false));
    dom.clearQueryBtn.addEventListener("click", clearQuery);
    dom.queryTabs.forEach((tab) => {
      tab.addEventListener("click", () => setQueryTab(tab.dataset.queryTab));
    });
    dom.runNodeQueryBtn.addEventListener("click", runNodeQuery);
    dom.runEdgeQueryBtn.addEventListener("click", runEdgeQuery);
    dom.runPathQueryBtn.addEventListener("click", runPathQuery);
    [dom.nodeQueryInput, dom.edgeSourceInput, dom.edgeTargetInput, dom.pathStartInput, dom.pathEndInput].forEach((input) => {
      input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        const active = document.querySelector(".query-section.active");
        if (!active) return;
        if (active.dataset.querySection === "node") runNodeQuery();
        else if (active.dataset.querySection === "edge") runEdgeQuery();
        else runPathQuery();
      });
    });
    initQueryPanelDrag();
  }

  function initQueryPanelDrag() {
    if (!dom.queryPanel || !dom.queryHead) return;
    let dragState = null;

    dom.queryPanel.addEventListener("pointerdown", (event) => {
      if (!isQueryDragSurface(event)) return;
      const rect = dom.queryPanel.getBoundingClientRect();
      dragState = {
        startX: event.clientX,
        startY: event.clientY,
        startLeft: rect.left,
        startTop: rect.top,
      };
      dom.queryPanel.classList.add("dragging");
      window.addEventListener("pointermove", moveQueryPanel);
      window.addEventListener("pointerup", stopQueryPanelDrag);
      window.addEventListener("pointercancel", stopQueryPanelDrag);
      event.preventDefault();
    });

    dom.queryPanel.addEventListener("contextmenu", (event) => {
      if (isQueryDragSurface(event)) event.preventDefault();
    });

    function moveQueryPanel(event) {
      if (!dragState) return;
      if (event.buttons === 0) {
        stopQueryPanelDrag();
        return;
      }
      const rect = dom.queryPanel.getBoundingClientRect();
      const nextLeft = clamp(dragState.startLeft + event.clientX - dragState.startX, 8, window.innerWidth - rect.width - 8);
      const nextTop = clamp(dragState.startTop + event.clientY - dragState.startY, 8, window.innerHeight - rect.height - 8);
      dom.queryPanel.style.left = `${nextLeft}px`;
      dom.queryPanel.style.top = `${nextTop}px`;
      dom.queryPanel.style.right = "auto";
      dom.queryPanel.style.bottom = "auto";
      event.preventDefault();
    }

    function stopQueryPanelDrag() {
      if (!dragState) return;
      dragState = null;
      dom.queryPanel.classList.remove("dragging");
      window.removeEventListener("pointermove", moveQueryPanel);
      window.removeEventListener("pointerup", stopQueryPanelDrag);
      window.removeEventListener("pointercancel", stopQueryPanelDrag);
    }
  }

  function isQueryDragSurface(event) {
    const target = event.target;
    if (target.closest("button, select, textarea, input, .query-results")) return false;
    const rect = dom.queryPanel.getBoundingClientRect();
    const edge = 12;
    const resizeCorner = 28;
    const x = event.clientX;
    const y = event.clientY;
    const inResizeCorner = rect.right - x <= resizeCorner && rect.bottom - y <= resizeCorner;
    if (inResizeCorner) return false;
    const onEdge =
      x - rect.left <= edge ||
      rect.right - x <= edge ||
      y - rect.top <= edge ||
      rect.bottom - y <= edge;
    const inHeader = Boolean(target.closest(".query-head"));
    return inHeader || onEdge;
  }

  function fillEdgeTypeSelect() {
    dom.edgeTypeSelect.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "全部关系";
    dom.edgeTypeSelect.append(all);
    state.kg.relation_types.forEach((rt) => {
      const option = document.createElement("option");
      option.value = rt.key;
      option.textContent = `${state.relationLabel.get(rt.key) || rt.label || rt.key} (${rt.key})`;
      dom.edgeTypeSelect.append(option);
    });
  }

  function setQueryPanelOpen(open) {
    state.queryPanelOpen = open;
    dom.queryPanel.hidden = !open;
    dom.openQueryPanelBtn.classList.toggle("active", open);
  }

  function setQueryTab(tabName) {
    dom.queryTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.queryTab === tabName));
    dom.querySections.forEach((section) => section.classList.toggle("active", section.dataset.querySection === tabName));
  }

  function setQueryStatus(text, kind) {
    dom.queryStatus.textContent = text;
    dom.queryStatus.dataset.kind = kind || "idle";
  }

  function clearQuery() {
    state.queryNodeIds.clear();
    state.queryEdgeKeys.clear();
    dom.queryResults.innerHTML = "";
    setQueryStatus("已清除查询高亮。", "idle");
    renderGraph();
  }

  function runNodeQuery() {
    const query = dom.nodeQueryInput.value.trim();
    dom.queryResults.innerHTML = "";
    state.queryNodeIds.clear();
    state.queryEdgeKeys.clear();
    if (!query) {
      setQueryStatus("请输入节点关键词。", "warn");
      renderGraph();
      return;
    }
    const results = state.kg.nodes
      .map((node) => ({ node, score: nodeMatchScore(node, query) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.node.name.localeCompare(b.node.name, "zh-Hans-CN"))
      .slice(0, 50);
    if (results.length === 0) {
      setQueryStatus("没有匹配节点。", "warn");
      renderGraph();
      return;
    }
    results.forEach(({ node }) => {
      dom.queryResults.append(queryResultButton({
        title: node.name,
        meta: `${node.id} · L${node.level} · ${breadcrumbOf(node).join(" / ")}`,
        note: node.summary || "",
        onClick: () => focusQueryNodes([node.id], node.id),
      }));
    });
    state.queryNodeIds = new Set(results.slice(0, 12).map((item) => item.node.id));
    setQueryStatus(`找到 ${results.length} 个节点，已高亮前 ${Math.min(results.length, 12)} 个。`, "ok");
    focusQueryNodes([...state.queryNodeIds], results[0].node.id);
  }

  function runEdgeQuery() {
    const sourceQuery = dom.edgeSourceInput.value.trim();
    const targetQuery = dom.edgeTargetInput.value.trim();
    const type = dom.edgeTypeSelect.value;
    dom.queryResults.innerHTML = "";
    state.queryNodeIds.clear();
    state.queryEdgeKeys.clear();

    if (!sourceQuery && !targetQuery && !type) {
      setQueryStatus("请输入头节点、尾节点或选择关系类型。", "warn");
      renderGraph();
      return;
    }

    const sourceMatches = sourceQuery ? matchNodes(sourceQuery, 24) : [];
    const targetMatches = targetQuery ? matchNodes(targetQuery, 24) : [];
    if (sourceQuery && sourceMatches.length === 0) {
      setQueryStatus(`头节点「${sourceQuery}」没有匹配到节点。`, "warn");
      renderGraph();
      return;
    }
    if (targetQuery && targetMatches.length === 0) {
      setQueryStatus(`尾节点「${targetQuery}」没有匹配到节点。`, "warn");
      renderGraph();
      return;
    }

    const sourceSet = new Set(sourceMatches.map((item) => item.node.id));
    const targetSet = new Set(targetMatches.map((item) => item.node.id));
    const sourceScore = new Map(sourceMatches.map((item) => [item.node.id, item.score]));
    const targetScore = new Map(targetMatches.map((item) => [item.node.id, item.score]));

    const results = state.kg.edges
      .filter((edge) => !type || edge.type === type)
      .map((edge) => ({ edge, score: edgeQueryScore(edge, sourceSet, targetSet, sourceScore, targetScore, Boolean(sourceQuery), Boolean(targetQuery)) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || edgeKey(a.edge).localeCompare(edgeKey(b.edge)))
      .map((item) => item.edge)
      .slice(0, 100);

    if (results.length === 0) {
      const matchHint = edgeMatchHint(sourceMatches, targetMatches, sourceQuery, targetQuery);
      setQueryStatus(`${matchHint}；没有找到相连关系。`, "warn");
      const focusIds = [...sourceSet, ...targetSet];
      if (focusIds.length > 0) focusQueryNodes(focusIds.slice(0, 12), focusIds[0]);
      else renderGraph();
      return;
    }
    results.forEach((edge) => {
      const source = state.nodeById.get(edge.source);
      const target = state.nodeById.get(edge.target);
      dom.queryResults.append(queryResultButton({
        title: `${source.name} -[${state.relationLabel.get(edge.type) || edge.type}]-> ${target.name}`,
        meta: `${edge.type} · ${edge.source} → ${edge.target}`,
        note: edge.note || "",
        onClick: () => focusQueryEdges([edgeKey(edge)], edge.source),
      }));
    });
    focusQueryEdges(results.slice(0, 20).map(edgeKey), results[0].source);
    setQueryStatus(`${edgeMatchHint(sourceMatches, targetMatches, sourceQuery, targetQuery)}；找到 ${results.length} 条关系，已高亮前 ${Math.min(results.length, 20)} 条。`, "ok");
  }

  function runPathQuery() {
    const startQuery = dom.pathStartInput.value.trim();
    const endQuery = dom.pathEndInput.value.trim();
    dom.queryResults.innerHTML = "";
    state.queryNodeIds.clear();
    state.queryEdgeKeys.clear();
    if (!startQuery || !endQuery) {
      setQueryStatus("请输入起点和终点。", "warn");
      renderGraph();
      return;
    }
    const startMatches = pathNodeMatches(startQuery, 16);
    const endMatches = pathNodeMatches(endQuery, 16);
    const maxDepth = Number(dom.pathMaxHopSelect.value) || 4;
    if (startMatches.length === 0 || endMatches.length === 0) {
      setQueryStatus("起点或终点没有匹配到节点。", "warn");
      renderGraph();
      return;
    }
    const path = findBestPath(startMatches, endMatches, maxDepth, normalizeText(startQuery) === normalizeText(endQuery));
    const start = path ? state.nodeById.get(path.nodes[0]) : startMatches[0].node;
    const end = path ? state.nodeById.get(path.nodes[path.nodes.length - 1]) : endMatches[0].node;
    if (!path) {
      setQueryStatus(`起点候选：${formatMatchedNodes(startMatches)}；终点候选：${formatMatchedNodes(endMatches)}；未在 ${maxDepth} 跳内找到路径。`, "warn");
      focusQueryNodes([...startMatches.slice(0, 6), ...endMatches.slice(0, 6)].map((item) => item.node.id), start.id);
      return;
    }
    if (!state.includeContains && path.steps.some((step) => step.edge.type === "CONTAINS")) {
      state.includeContains = true;
      dom.includeContainsToggle.checked = true;
    }
    const block = document.createElement("div");
    block.className = "query-path-result";
    const title = document.createElement("div");
    title.className = "query-path-title";
    title.textContent = `${start.name} 到 ${end.name} · ${path.steps.length} 跳`;
    block.append(title);
    path.steps.forEach((step) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "query-path-step";
      row.textContent = formatPathStep(step);
      row.addEventListener("click", () => focusPathStep(step));
      block.append(row);
    });
    dom.queryResults.append(block);
    state.queryNodeIds = new Set(path.nodes);
    state.queryEdgeKeys = new Set(path.steps.map((step) => edgeKey(step.edge)));
    focusGraphNode(start.id);
    setQueryStatus(`路径查询完成：起点匹配为「${start.name}」，终点匹配为「${end.name}」；最大跳数 ${maxDepth}，箭头方向表示图谱中真实边方向。`, "ok");
  }

  function nodeMatchScore(node, query) {
    const q = normalizeText(query);
    if (!q) return 0;
    const id = normalizeText(node.id);
    const name = normalizeText(node.name);
    const summary = normalizeText(node.summary || "");
    const bc = normalizeText(breadcrumbOf(node).join("/"));
    let score = 0;
    if (id === q || name === q) score += 120;
    if (name.includes(q)) score += 90;
    if (id.includes(q)) score += 70;
    if (summary.includes(q)) score += 42;
    if (bc.includes(q)) score += 36;
    if (fuzzyIncludes(name, q)) score += 26;
    if (fuzzyIncludes(bc, q)) score += 12;
    if (node.level >= 3) score *= 1.08;
    if (node.level <= 1) score *= 0.65;
    return score;
  }

  function matchNodes(query, limit) {
    const ranked = state.kg.nodes
      .map((node) => ({ node, score: nodeMatchScore(node, query) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.node.name.localeCompare(b.node.name, "zh-Hans-CN"));
    if (ranked.length === 0) return [];
    const best = ranked[0].score;
    return ranked
      .filter((item) => item.score >= Math.max(20, best * 0.45))
      .slice(0, limit || 12);
  }

  function pathNodeMatches(query, limit) {
    const q = normalizeText(query);
    const exact = state.kg.nodes
      .filter((node) => normalizeText(node.id) === q || normalizeText(node.name) === q)
      .map((node) => ({ node, score: nodeMatchScore(node, query) }))
      .sort((a, b) => b.score - a.score || a.node.level - b.node.level);
    return exact.length > 0 ? exact.slice(0, limit || 12) : matchNodes(query, limit);
  }

  function edgeQueryScore(edge, sourceSet, targetSet, sourceScore, targetScore, hasSourceQuery, hasTargetQuery) {
    const hasSource = sourceSet.size > 0;
    const hasTarget = targetSet.size > 0;
    if (hasSource && hasTarget) {
      const direct = sourceSet.has(edge.source) && targetSet.has(edge.target);
      const reverse = sourceSet.has(edge.target) && targetSet.has(edge.source);
      if (!direct && !reverse) return 0;
      const leftScore = direct ? sourceScore.get(edge.source) : sourceScore.get(edge.target);
      const rightScore = direct ? targetScore.get(edge.target) : targetScore.get(edge.source);
      return (leftScore || 1) + (rightScore || 1) + (direct ? 20 : 8);
    }
    if (hasSource) {
      if (!sourceSet.has(edge.source) && !sourceSet.has(edge.target)) return 0;
      return (sourceScore.get(edge.source) || sourceScore.get(edge.target) || 1) + (hasTargetQuery ? 0 : 4);
    }
    if (hasTarget) {
      if (!targetSet.has(edge.source) && !targetSet.has(edge.target)) return 0;
      return (targetScore.get(edge.source) || targetScore.get(edge.target) || 1) + (hasSourceQuery ? 0 : 4);
    }
    return 1;
  }

  function edgeMatchHint(sourceMatches, targetMatches, sourceQuery, targetQuery) {
    const parts = [];
    if (sourceQuery) parts.push(`头节点匹配：${formatMatchedNodes(sourceMatches)}`);
    if (targetQuery) parts.push(`尾节点匹配：${formatMatchedNodes(targetMatches)}`);
    return parts.length > 0 ? parts.join("；") : "按关系类型查询";
  }

  function formatMatchedNodes(matches) {
    return matches.slice(0, 3).map((item) => `「${item.node.name}」`).join("、") || "无";
  }

  function bestNodeMatch(query) {
    return state.kg.nodes
      .map((node) => ({ node, score: nodeMatchScore(node, query) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)[0]?.node || null;
  }

  function normalizeText(text) {
    return String(text || "").toLowerCase().replace(/\s+/g, "");
  }

  function fuzzyIncludes(text, query) {
    if (!query) return false;
    let index = 0;
    for (const ch of text) {
      if (ch === query[index]) index += 1;
      if (index === query.length) return true;
    }
    return false;
  }

  function findBestPath(startMatches, endMatches, maxDepth, allowSameNode) {
    const endIds = new Set(endMatches.map((item) => item.node.id));
    const endScore = new Map(endMatches.map((item) => [item.node.id, item.score]));
    let best = null;
    startMatches.forEach((match, index) => {
      const candidate = findShortestPath(match.node.id, endIds, maxDepth, allowSameNode);
      if (!candidate) return;
      const score = candidate.steps.length * -10000 + match.score + (endScore.get(candidate.id) || 0) - index;
      if (!best || score > best.rankScore) best = { ...candidate, rankScore: score };
    });
    return best;
  }

  function findShortestPath(startId, endIds, maxDepth, allowSameNode) {
    const queue = [{ id: startId, nodes: [startId], steps: [] }];
    const visited = new Set([startId]);
    while (queue.length > 0) {
      const current = queue.shift();
      if (endIds.has(current.id) && (allowSameNode || current.steps.length > 0)) return current;
      if (current.steps.length >= maxDepth) continue;
      pathNeighbors(current.id).forEach((step) => {
        if (visited.has(step.to)) return;
        visited.add(step.to);
        queue.push({
          id: step.to,
          nodes: current.nodes.concat(step.to),
          steps: current.steps.concat(step),
        });
      });
    }
    return null;
  }

  function pathNeighbors(id) {
    const nextSteps = [];
    (state.outgoing.get(id) || []).forEach((edge) => {
      nextSteps.push({ from: id, to: edge.target, edge, direction: "out" });
    });
    (state.incoming.get(id) || []).forEach((edge) => {
      nextSteps.push({ from: id, to: edge.source, edge, direction: "in" });
    });
    const node = state.nodeById.get(id);
    if (node && node.parent_id && state.nodeById.has(node.parent_id)) {
      nextSteps.push({
        from: id,
        to: node.parent_id,
        edge: { source: node.parent_id, target: id, type: "CONTAINS", note: "" },
        direction: "in",
      });
    }
    (state.childrenOf.get(id) || []).forEach((child) => {
      nextSteps.push({
        from: id,
        to: child.id,
        edge: { source: id, target: child.id, type: "CONTAINS", note: "" },
        direction: "out",
      });
    });
    return nextSteps;
  }

  function formatPathStep(step) {
    const from = state.nodeById.get(step.from);
    const to = state.nodeById.get(step.to);
    const label = state.relationLabel.get(step.edge.type) || step.edge.type;
    if (step.direction === "out") return `${from.name} -[${label}]-> ${to.name}`;
    return `${from.name} <-[${label}]- ${to.name}`;
  }

  function focusQueryNodes(ids, focusId) {
    state.queryNodeIds = new Set(ids.filter((id) => state.nodeById.has(id)));
    state.queryEdgeKeys.clear();
    focusGraphNode(focusId || ids[0]);
  }

  function focusQueryEdges(keys, focusId) {
    state.queryEdgeKeys = new Set(keys.filter((key) => state.edgeByKey.has(key)));
    const ids = new Set();
    state.queryEdgeKeys.forEach((key) => {
      const edge = state.edgeByKey.get(key);
      ids.add(edge.source);
      ids.add(edge.target);
    });
    state.queryNodeIds = ids;
    focusGraphNode(focusId || [...ids][0]);
  }

  function focusPathStep(step) {
    const key = edgeKey(step.edge);
    if (state.edgeByKey.has(key)) {
      focusQueryEdges([key], step.from);
      return;
    }
    state.queryEdgeKeys = new Set([key]);
    state.queryNodeIds = new Set([step.edge.source, step.edge.target]);
    focusGraphNode(step.from);
  }

  function focusGraphNode(id) {
    if (!id || !state.nodeById.has(id)) {
      renderGraph();
      return;
    }
    expandAncestors(id);
    if (state.hop < 1) {
      state.hop = 1;
      dom.hopSelect.value = "1";
    }
    selectNode(id);
  }

  function queryResultButton({ title, meta, note, onClick }) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "query-result-item";
    const titleEl = document.createElement("strong");
    titleEl.textContent = title;
    const metaEl = document.createElement("span");
    metaEl.textContent = meta;
    button.append(titleEl, metaEl);
    if (note) {
      const noteEl = document.createElement("p");
      noteEl.textContent = note;
      button.append(noteEl);
    }
    button.addEventListener("click", onClick);
    return button;
  }

  // ---------------- Problem analyzer ----------------

  function initProblemAnalyzer() {
    if (!dom.analyzeProblemBtn) return;
    dom.openProblemAnalyzerBtn.addEventListener("click", () => setProblemPanelOpen(true));
    dom.analyzeProblemBtn.addEventListener("click", analyzeProblem);
    dom.refreshModelsBtn.addEventListener("click", loadOllamaModels);
    dom.clearAnalysisBtn.addEventListener("click", clearAnalysis);
    dom.closeProblemAnalyzerBtn.addEventListener("click", () => setProblemPanelOpen(false));
    dom.problemInput.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        analyzeProblem();
      }
    });
    initProblemPanelDrag();
    loadOllamaModels();
    setProblemPanelOpen(true);
  }

  function setProblemPanelOpen(open) {
    state.problemPanelOpen = open;
    dom.problemAnalyzer.hidden = !open;
    dom.openProblemAnalyzerBtn.classList.toggle("active", open);
    dom.openProblemAnalyzerBtn.textContent = state.problemAnalysisRunning ? "分析中..." : "错题分析";
  }

  function setProblemAnalysisRunning(running) {
    state.problemAnalysisRunning = running;
    dom.openProblemAnalyzerBtn.classList.toggle("running", running);
    dom.openProblemAnalyzerBtn.textContent = running ? "分析中..." : "错题分析";
  }

  async function loadOllamaModels() {
    const current = dom.problemModelInput.value || "qwen2.5:7b";
    dom.refreshModelsBtn.disabled = true;
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "无法读取模型列表");
      const models = Array.isArray(data.models) && data.models.length > 0 ? data.models : [data.default_model || current];
      dom.problemModelInput.innerHTML = "";
      models.forEach((model) => {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        dom.problemModelInput.append(option);
      });
      if (models.includes(current)) {
        dom.problemModelInput.value = current;
      } else if (models.includes(data.default_model)) {
        dom.problemModelInput.value = data.default_model;
      }
      if (data.warning) {
        setAnalysisStatus(data.warning, "warn");
      } else {
        setAnalysisStatus(`已识别 ${models.length} 个本地 Ollama 模型。`, "ok");
      }
    } catch (err) {
      dom.problemModelInput.innerHTML = "";
      const option = document.createElement("option");
      option.value = current;
      option.textContent = current;
      dom.problemModelInput.append(option);
      setAnalysisStatus("未连接到 AI 服务；启动 serve_ai 后可自动读取模型列表。", "warn");
    } finally {
      dom.refreshModelsBtn.disabled = false;
    }
  }

  function initProblemPanelDrag() {
    if (!dom.problemAnalyzer || !dom.problemHead) return;
    let dragState = null;

    dom.problemAnalyzer.addEventListener("pointerdown", (event) => {
      if (!isProblemDragSurface(event)) return;
      const rect = dom.problemAnalyzer.getBoundingClientRect();
      dragState = {
        startX: event.clientX,
        startY: event.clientY,
        startLeft: rect.left,
        startTop: rect.top,
      };
      dom.problemAnalyzer.classList.add("dragging");
      window.addEventListener("pointermove", moveProblemPanel);
      window.addEventListener("pointerup", stopProblemPanelDrag);
      window.addEventListener("pointercancel", stopProblemPanelDrag);
      event.preventDefault();
    });

    dom.problemAnalyzer.addEventListener("contextmenu", (event) => {
      if (isProblemDragSurface(event)) event.preventDefault();
    });

    function moveProblemPanel(event) {
      if (!dragState) return;
      if (event.buttons === 0) {
        stopProblemPanelDrag();
        return;
      }
      const rect = dom.problemAnalyzer.getBoundingClientRect();
      const nextLeft = clamp(dragState.startLeft + event.clientX - dragState.startX, 8, window.innerWidth - rect.width - 8);
      const nextTop = clamp(dragState.startTop + event.clientY - dragState.startY, 8, window.innerHeight - rect.height - 8);
      dom.problemAnalyzer.style.left = `${nextLeft}px`;
      dom.problemAnalyzer.style.top = `${nextTop}px`;
      dom.problemAnalyzer.style.right = "auto";
      dom.problemAnalyzer.style.bottom = "auto";
      event.preventDefault();
    }

    function stopProblemPanelDrag() {
      if (!dragState) return;
      dragState = null;
      dom.problemAnalyzer.classList.remove("dragging");
      window.removeEventListener("pointermove", moveProblemPanel);
      window.removeEventListener("pointerup", stopProblemPanelDrag);
      window.removeEventListener("pointercancel", stopProblemPanelDrag);
    }
  }

  function isProblemDragSurface(event) {
    const target = event.target;
    if (target.closest("button, select, textarea, input, .analysis-result")) return false;
    const rect = dom.problemAnalyzer.getBoundingClientRect();
    const edge = 12;
    const resizeCorner = 28;
    const x = event.clientX;
    const y = event.clientY;
    const inResizeCorner = rect.right - x <= resizeCorner && rect.bottom - y <= resizeCorner;
    if (inResizeCorner) return false;
    const onEdge =
      x - rect.left <= edge ||
      rect.right - x <= edge ||
      y - rect.top <= edge ||
      rect.bottom - y <= edge;
    const inHeader = Boolean(target.closest(".problem-head"));
    return inHeader || onEdge;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(value, Math.max(min, max)));
  }

  function setAnalysisStatus(text, kind) {
    dom.analysisStatus.textContent = text;
    dom.analysisStatus.dataset.kind = kind || "idle";
  }

  async function analyzeProblem() {
    const question = dom.problemInput.value.trim();
    if (!question) {
      setAnalysisStatus("请先粘贴一道题目。", "error");
      return;
    }
    const model = dom.problemModelInput.value.trim() || "qwen2.5:7b";
    dom.analyzeProblemBtn.disabled = true;
    setProblemAnalysisRunning(true);
    setAnalysisStatus("正在检索图谱并调用本地 Ollama...", "loading");
    dom.analysisResult.innerHTML = "";
    try {
      const res = await fetch("/api/analyze-problem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, model, top_k: 36 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "分析失败");
      renderAnalysisResult(data);
      applyAnalysisHighlights(data);
      const modeText = data.mode === "ollama" ? "Ollama 已完成图谱约束分析" : "已使用本地匹配降级结果";
      setAnalysisStatus(`${modeText} · 候选 ${data.candidate_count || 0} 个`, data.mode === "ollama" ? "ok" : "warn");
    } catch (err) {
      setAnalysisStatus(`无法连接 AI 服务：${err.message}。请用 python3 code/problem_analyzer_server.py 启动。`, "error");
    } finally {
      dom.analyzeProblemBtn.disabled = false;
      setProblemAnalysisRunning(false);
    }
  }

  function clearAnalysis() {
    state.analysisNodeIds.clear();
    state.analysisRouteIds.clear();
    dom.analysisResult.innerHTML = "";
    setAnalysisStatus("已清除错题分析高亮。", "idle");
    renderGraph();
  }

  function applyAnalysisHighlights(data) {
    state.analysisNodeIds = new Set((data.nodes || []).map((node) => node.id).filter((id) => state.nodeById.has(id)));
    state.analysisRouteIds = new Set((data.route || []).filter((id) => state.nodeById.has(id)));
    const focusId = (data.nodes && data.nodes[0] && data.nodes[0].id) || (data.route && data.route[0]);
    if (focusId && state.nodeById.has(focusId)) {
      expandAncestors(focusId);
      if (state.hop < 2) {
        state.hop = 2;
        dom.hopSelect.value = "2";
      }
      selectNode(focusId);
    } else {
      renderGraph();
    }
  }

  function renderAnalysisResult(data) {
    dom.analysisResult.innerHTML = "";
    if (data.warning) {
      dom.analysisResult.append(analysisNotice(data.warning, "warn"));
    }
    dom.analysisResult.append(analysisBlock("条件检查", data.condition_check || "未返回条件检查。"));
    dom.analysisResult.append(analysisBlock("诊断结论", data.diagnosis || "未返回诊断结论。"));

    const nodes = document.createElement("div");
    nodes.className = "analysis-block";
    nodes.append(analysisHeading("考点权重"));
    if (!data.nodes || data.nodes.length === 0) {
      nodes.append(analysisEmpty("没有命中知识图谱节点。"));
    } else {
      data.nodes.forEach((item) => nodes.append(analysisNodeRow(item)));
    }
    dom.analysisResult.append(nodes);

    if (data.route && data.route.length > 0) {
      const route = document.createElement("div");
      route.className = "analysis-block";
      route.append(analysisHeading("推荐补救路径"));
      const chips = document.createElement("div");
      chips.className = "analysis-route";
      data.route.forEach((id, index) => {
        const node = state.nodeById.get(id);
        if (!node) return;
        const chip = document.createElement("button");
        chip.type = "button";
        chip.textContent = node.name;
        chip.addEventListener("click", () => {
          expandAncestors(id);
          selectNode(id);
        });
        chips.append(chip);
        if (index < data.route.length - 1) {
          const arrow = document.createElement("span");
          arrow.textContent = "→";
          chips.append(arrow);
        }
      });
      route.append(chips);
      dom.analysisResult.append(route);
    }

    dom.analysisResult.append(analysisList("解题步骤提示", data.solution_steps || []));
    dom.analysisResult.append(analysisList("常见错误", data.mistakes || []));
    dom.analysisResult.append(evidenceBlock(data.graph_evidence || []));
  }

  function analysisHeading(text) {
    const heading = document.createElement("h3");
    heading.textContent = text;
    return heading;
  }

  function analysisBlock(title, text) {
    const block = document.createElement("div");
    block.className = "analysis-block";
    block.append(analysisHeading(title));
    const p = document.createElement("p");
    p.textContent = text;
    block.append(p);
    return block;
  }

  function analysisNotice(text, kind) {
    const div = document.createElement("div");
    div.className = `analysis-notice ${kind || ""}`;
    div.textContent = text;
    return div;
  }

  function analysisEmpty(text) {
    const div = document.createElement("div");
    div.className = "analysis-empty";
    div.textContent = text;
    return div;
  }

  function analysisNodeRow(item) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "analysis-node-row";
    row.addEventListener("click", () => {
      expandAncestors(item.id);
      selectNode(item.id);
    });

    const top = document.createElement("div");
    top.className = "analysis-node-top";
    const name = document.createElement("span");
    name.className = "analysis-node-name";
    name.textContent = item.name;
    const weight = document.createElement("span");
    weight.className = "analysis-node-weight";
    weight.textContent = `${item.weight}%`;
    top.append(name, weight);

    const bar = document.createElement("div");
    bar.className = "analysis-weight-bar";
    const fill = document.createElement("span");
    fill.style.width = `${Math.max(4, Math.min(Number(item.weight) || 0, 100))}%`;
    bar.append(fill);

    const meta = document.createElement("div");
    meta.className = "analysis-node-meta";
    meta.textContent = `${item.role || "考点"} · ${item.breadcrumb || item.id}`;

    const reason = document.createElement("p");
    reason.textContent = item.reason || item.summary || "";

    row.append(top, bar, meta, reason);
    return row;
  }

  function analysisList(title, items) {
    const block = document.createElement("div");
    block.className = "analysis-block";
    block.append(analysisHeading(title));
    if (!items.length) {
      block.append(analysisEmpty("暂无。"));
      return block;
    }
    const ol = document.createElement("ol");
    items.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      ol.append(li);
    });
    block.append(ol);
    return block;
  }

  function evidenceBlock(edges) {
    const block = document.createElement("div");
    block.className = "analysis-block";
    block.append(analysisHeading("图谱依据"));
    if (!edges.length) {
      block.append(analysisEmpty("命中节点之间暂无直接边，已在图中展示候选节点。"));
      return block;
    }
    const ul = document.createElement("ul");
    ul.className = "analysis-evidence";
    edges.forEach((edge) => {
      const li = document.createElement("li");
      li.textContent = `${edge.source_name} -[${edge.label}]-> ${edge.target_name}`;
      if (edge.note) {
        const note = document.createElement("span");
        note.textContent = edge.note;
        li.append(note);
      }
      ul.append(li);
    });
    block.append(ul);
    return block;
  }

  // ---------------- Detail panel ----------------

  function renderDetail() {
    if (!state.selectedId) {
      dom.detail.innerHTML = '<div class="placeholder">点击节点查看详情。</div>';
      return;
    }
    const node = state.nodeById.get(state.selectedId);
    if (!node) {
      dom.detail.innerHTML = '<div class="placeholder">节点未找到。</div>';
      return;
    }
    const breadcrumb = breadcrumbOf(node);
    const summary = node.summary || "（暂无简介）";

    const meta = [];
    meta.push(`L${node.level}`);
    const domainId = domainOf(node);
    const domNode = state.nodeById.get(domainId);
    if (domNode && domainId !== node.id) meta.push(domNode.name);
    meta.push(`id: ${node.id}`);

    dom.detail.innerHTML = "";

    const title = document.createElement("h2");
    title.textContent = node.name;
    dom.detail.append(title);

    const bc = document.createElement("div");
    bc.className = "breadcrumb";
    bc.textContent = breadcrumb.join(" / ");
    dom.detail.append(bc);

    const metaDiv = document.createElement("div");
    metaDiv.className = "meta";
    meta.forEach((m) => {
      const span = document.createElement("span");
      span.textContent = m;
      metaDiv.append(span);
    });
    dom.detail.append(metaDiv);

    const summaryDiv = document.createElement("div");
    summaryDiv.className = "summary";
    summaryDiv.textContent = summary;
    dom.detail.append(summaryDiv);

    dom.detail.append(buildLearningAssistant(node));

    // 父子层级（始终展示，无视 CONTAINS toggle）
    const children = state.childrenOf.get(node.id) || [];
    if (children.length > 0) {
      dom.detail.append(buildRelationGroup(
        "包含",
        "#cccccc",
        children.map((c) => ({
          direction: "out",
          peer: c,
          note: "",
        }))
      ));
    }
    if (node.parent_id) {
      const parent = state.nodeById.get(node.parent_id);
      if (parent) {
        dom.detail.append(buildRelationGroup(
          "属于",
          "#cccccc",
          [{ direction: "in", peer: parent, note: "" }]
        ));
      }
    }

    // 按关系类型分组
    state.relationOrder.forEach((type) => {
      if (type === "CONTAINS") return;
      const outs = (state.outgoing.get(node.id) || [])
        .filter((e) => e.type === type)
        .map((e) => ({
          direction: "out",
          peer: state.nodeById.get(e.target),
          note: e.note,
        }))
        .filter((entry) => entry.peer);
      const ins = (state.incoming.get(node.id) || [])
        .filter((e) => e.type === type)
        .map((e) => ({
          direction: "in",
          peer: state.nodeById.get(e.source),
          note: e.note,
        }))
        .filter((entry) => entry.peer);
      const combined = outs.concat(ins);
      if (combined.length === 0) return;
      dom.detail.append(buildRelationGroup(
        state.relationLabel.get(type) || type,
        state.relationColor.get(type) || "#888",
        combined
      ));
    });
  }

  function buildRelationGroup(title, color, entries) {
    const group = document.createElement("div");
    group.className = "relation-group";

    const header = document.createElement("div");
    header.className = "group-header";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = color;
    const titleSpan = document.createElement("span");
    titleSpan.textContent = title;
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = `${entries.length}`;
    header.append(swatch, titleSpan, count);
    group.append(header);

    const ul = document.createElement("ul");
    entries.forEach((entry) => {
      const li = document.createElement("li");
      const arrow = entry.direction === "out" ? "→" : "←";
      const head = document.createElement("span");
      head.innerHTML = `<span class="arrow">${arrow}</span>${entry.peer.name}`;
      li.append(head);
      if (entry.note) {
        const noteEl = document.createElement("span");
        noteEl.className = "note";
        noteEl.textContent = entry.note;
        li.append(noteEl);
      }
      li.addEventListener("click", () => {
        expandAncestors(entry.peer.id);
        selectNode(entry.peer.id);
      });
      ul.append(li);
    });
    group.append(ul);
    return group;
  }

  // ---------------- Learning assistant ----------------

  function buildLearningAssistant(node) {
    const panel = document.createElement("section");
    panel.className = "assistant-panel";

    const title = document.createElement("div");
    title.className = "assistant-title";
    title.textContent = "学习路径助手";
    panel.append(title);

    const plan = learningPlan(node.id);
    const content = document.createElement("div");
    content.className = "assistant-content";
    content.append(buildAssistantSection("先补基础", plan.prerequisites, "沿「前置」关系反向寻找。"));
    content.append(buildPathSection("推荐路径", plan.path));
    content.append(buildAssistantSection("应用方向", plan.applications, "沿「应用于」关系寻找后续练习场景。"));
    content.append(buildAssistantSection("易混淆 / 类比", plan.watchouts, "适合做概念辨析或复习提醒。"));
    panel.append(content);
    return panel;
  }

  function learningPlan(nodeId) {
    const prerequisites = uniqueById(
      incomingPeers(nodeId, "PREREQUISITE_OF")
        .concat(incomingPeers(nodeId, "USED_IN"))
        .concat(incomingPeers(nodeId, "GENERALIZES"))
    ).slice(0, 6);

    const applications = uniqueById(
      outgoingPeers(nodeId, "USED_IN")
        .concat(outgoingPeers(nodeId, "PREREQUISITE_OF"))
        .concat(outgoingPeers(nodeId, "SPECIAL_CASE_OF"))
    ).slice(0, 6);

    const watchouts = uniqueById(
      bothDirectionPeers(nodeId, "EASILY_CONFUSED_WITH")
        .concat(bothDirectionPeers(nodeId, "SIMILAR_TO"))
        .concat(bothDirectionPeers(nodeId, "RELATED_TO"))
    ).slice(0, 6);

    const path = uniqueById(prerequisites.slice(0, 2).concat([state.nodeById.get(nodeId)]).concat(applications.slice(0, 2)));
    return { prerequisites, applications, watchouts, path };
  }

  function outgoingPeers(nodeId, type) {
    return (state.outgoing.get(nodeId) || [])
      .filter((edge) => edge.type === type)
      .map((edge) => edgeWithPeer(edge, state.nodeById.get(edge.target), "out"))
      .filter((entry) => entry.peer);
  }

  function incomingPeers(nodeId, type) {
    return (state.incoming.get(nodeId) || [])
      .filter((edge) => edge.type === type)
      .map((edge) => edgeWithPeer(edge, state.nodeById.get(edge.source), "in"))
      .filter((entry) => entry.peer);
  }

  function bothDirectionPeers(nodeId, type) {
    return outgoingPeers(nodeId, type).concat(incomingPeers(nodeId, type));
  }

  function edgeWithPeer(edge, peer, direction) {
    return {
      id: peer && peer.id,
      peer,
      type: edge.type,
      direction,
      note: edge.note || "",
      label: state.relationLabel.get(edge.type) || edge.type,
    };
  }

  function uniqueById(entries) {
    const seen = new Set();
    const out = [];
    entries.forEach((entry) => {
      const id = entry.peer ? entry.peer.id : entry.id;
      if (!id || seen.has(id)) return;
      seen.add(id);
      out.push(entry);
    });
    return out;
  }

  function buildAssistantSection(title, entries, hint) {
    const section = document.createElement("div");
    section.className = "assistant-section";
    const header = document.createElement("div");
    header.className = "assistant-section-title";
    header.textContent = title;
    section.append(header);

    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.className = "assistant-empty";
      empty.textContent = hint;
      section.append(empty);
      return section;
    }

    const list = document.createElement("div");
    list.className = "assistant-list";
    entries.forEach((entry) => list.append(buildAssistantItem(entry)));
    section.append(list);
    return section;
  }

  function buildAssistantItem(entry) {
    const item = document.createElement("button");
    item.className = "assistant-item";
    const relation = document.createElement("span");
    relation.className = "assistant-relation";
    relation.textContent = entry.label;
    const name = document.createElement("span");
    name.className = "assistant-name";
    name.textContent = entry.peer.name;
    item.append(relation, name);
    if (entry.note) {
      const note = document.createElement("span");
      note.className = "assistant-note";
      note.textContent = entry.note;
      item.append(note);
    }
    item.addEventListener("click", () => {
      expandAncestors(entry.peer.id);
      selectNode(entry.peer.id);
    });
    return item;
  }

  function buildPathSection(title, entries) {
    const section = document.createElement("div");
    section.className = "assistant-section";
    const header = document.createElement("div");
    header.className = "assistant-section-title";
    header.textContent = title;
    section.append(header);

    const path = document.createElement("div");
    path.className = "assistant-path";
    entries.forEach((entry, index) => {
      const node = entry.peer || entry;
      const chip = document.createElement("button");
      chip.className = node.id === state.selectedId ? "path-chip current" : "path-chip";
      chip.textContent = node.name;
      chip.addEventListener("click", () => {
        expandAncestors(node.id);
        selectNode(node.id);
      });
      path.append(chip);
      if (index < entries.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "path-arrow";
        arrow.textContent = "→";
        path.append(arrow);
      }
    });
    section.append(path);
    return section;
  }

  function breadcrumbOf(node) {
    const chain = [];
    let cursor = node;
    while (cursor) {
      chain.unshift(cursor.name);
      if (!cursor.parent_id) break;
      cursor = state.nodeById.get(cursor.parent_id);
    }
    return chain;
  }
})();
