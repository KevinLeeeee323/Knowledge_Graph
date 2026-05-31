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
      state.relationLabel.set(rt.key, rt.label);
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
      text.textContent = rt.label;
      label.append(checkbox, swatch, text);
      dom.legend.append(label);
    });
  }

  function relationDescription(key) {
    const descs = {
      PREREQUISITE_OF: "A 是理解 B 的前置。",
      USED_IN: "A 是证明、计算或理解 B 时的工具。",
      GENERALIZES: "A 是 B 的推广。",
      SPECIAL_CASE_OF: "A 是 B 的特例。",
      SIMILAR_TO: "A 与 B 方法、结构、思想相似可类比。",
      EASILY_CONFUSED_WITH: "A 与 B 易混，需要对比辨析。",
      RELATED_TO: "A 与 B 弱相关。",
      CONTAINS: "层级父子（章 → 节 → 知识点）。",
    };
    return descs[key] || key;
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
    renderTree();
    renderDetail();
    renderGraph();
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
          width: 1.4,
          "line-color": "data(color)",
          "target-arrow-color": "data(color)",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.9,
          opacity: 0.7,
          label: "data(label)",
          "font-size": 9,
          color: "#6b7280",
          "text-rotation": "autorotate",
          "text-background-color": "#faf9f7",
          "text-background-opacity": 0.95,
          "text-background-padding": 2,
          "text-background-shape": "round-rectangle",
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
    state.cy.fit(undefined, 50);
    state.cy.center(state.cy.getElementById(state.selectedId));
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
    const dom = domainOf(node);
    const domNode = state.nodeById.get(dom);
    if (domNode && dom !== node.id) meta.push(domNode.name);
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
