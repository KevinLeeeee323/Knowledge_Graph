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
    const edges = collectEdges(nodeIds);

    const elements = [];
    nodeIds.forEach((id) => {
      const node = state.nodeById.get(id);
      if (!node) return;
      const colors = nodeColors(node);
      elements.push({
        data: {
          id: node.id,
          name: node.name,
          level: node.level,
          bg: colors.bg,
          border: colors.border,
          fg: colors.fg,
        },
        classes: node.id === state.selectedId ? "selected" : "",
      });
    });
    edges.forEach((edge) => {
      elements.push({
        data: {
          id: `${edge.source}->${edge.target}::${edge.type}`,
          source: edge.source,
          target: edge.target,
          type: edge.type,
          color: state.relationColor.get(edge.type) || "#888",
          label: state.relationLabel.get(edge.type) || edge.type,
        },
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
      const key = `${edge.source}->${edge.target}::${edge.type}`;
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

  function relationActive(type) {
    if (type === "CONTAINS") return state.includeContains;
    return state.enabledRelations.has(type);
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
