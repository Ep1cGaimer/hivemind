(() => {
  "use strict";

  const state = {
    user: null,
    projects: [],
    project: null,
    members: [],
    memories: [],
    graph: { nodes: [], edges: [] },
    selected: null,
    editing: false,
    search: "",
    zoom: 1,
    pan: { x: 0, y: 0 },
    positions: {},
    dragging: null,
  };

  const dom = {
    loginView: document.querySelector("#login-view"),
    projectsView: document.querySelector("#projects-view"),
    projectView: document.querySelector("#project-view"),
    loginForm: document.querySelector("#login-form"),
    loginError: document.querySelector("#login-error"),
    loginUsername: document.querySelector("#login-username"),
    loginPassword: document.querySelector("#login-password"),
    userName: document.querySelector("#user-name"),
    logout: document.querySelector("#logout-button"),
    toast: document.querySelector("#toast"),
    newProject: document.querySelector("#new-project-button"),
    projectForm: document.querySelector("#project-form"),
    projectName: document.querySelector("#project-name"),
    projectDescription: document.querySelector("#project-description-input"),
    cancelProject: document.querySelector("#cancel-project-button"),
    projectList: document.querySelector("#project-list"),
    emptyProjects: document.querySelector("#empty-projects"),
    backProjects: document.querySelector("#back-projects-button"),
    projectTitle: document.querySelector("#project-title"),
    projectDescriptionView: document.querySelector("#project-description"),
    peopleButton: document.querySelector("#people-button"),
    agentButton: document.querySelector("#agent-button"),
    newMemory: document.querySelector("#new-memory-button"),
    graph: document.querySelector("#memory-graph"),
    graphEmpty: document.querySelector("#graph-empty"),
    fitGraph: document.querySelector("#fit-graph-button"),
    zoomIn: document.querySelector("#zoom-in-button"),
    zoomOut: document.querySelector("#zoom-out-button"),
    memoryCount: document.querySelector("#memory-count"),
    memorySearch: document.querySelector("#memory-search"),
    memoryList: document.querySelector("#memory-list"),
    editorSection: document.querySelector("#editor-section"),
    editorKicker: document.querySelector("#editor-kicker"),
    editorHeading: document.querySelector("#editor-heading"),
    versionLabel: document.querySelector("#version-label"),
    memoryForm: document.querySelector("#memory-form"),
    memoryTitle: document.querySelector("#memory-title"),
    memoryBody: document.querySelector("#memory-body"),
    memoryTags: document.querySelector("#memory-tags"),
    cancelMemory: document.querySelector("#cancel-memory-button"),
    emptyEditor: document.querySelector("#empty-editor-button"),
    peoplePanel: document.querySelector("#people-panel"),
    memberList: document.querySelector("#member-list"),
    memberForm: document.querySelector("#member-form"),
    memberUser: document.querySelector("#member-user"),
    memberRole: document.querySelector("#member-role"),
    agentPanel: document.querySelector("#agent-panel"),
    agentForm: document.querySelector("#agent-form"),
    agentLabel: document.querySelector("#agent-label"),
    agentResult: document.querySelector("#agent-result"),
    agentToken: document.querySelector("#agent-token"),
    copyToken: document.querySelector("#copy-token-button"),
  };

  class ApiError extends Error {
    constructor(message, status) { super(message); this.status = status; }
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) throw new ApiError(payload.error?.message || `Request failed (${response.status})`, response.status);
    return payload;
  }

  function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function date(value) {
    if (!value) return "";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(parsed);
  }

  let toastTimer;
  function toast(message, kind = "info") {
    clearTimeout(toastTimer);
    dom.toast.textContent = message;
    dom.toast.dataset.kind = kind;
    dom.toast.hidden = false;
    toastTimer = setTimeout(() => { dom.toast.hidden = true; }, 3000);
  }

  function formBusy(form, busy, label) {
    const submit = form?.querySelector('button[type="submit"]');
    if (!submit) return;
    if (busy) {
      submit.disabled = true;
      submit.dataset.idleLabel = submit.textContent;
      submit.textContent = label;
    } else {
      submit.disabled = false;
      submit.textContent = submit.dataset.idleLabel || submit.textContent;
    }
  }

  function showLogin() {
    state.user = null;
    dom.loginView.hidden = false;
    dom.projectsView.hidden = true;
    dom.projectView.hidden = true;
    dom.userName.hidden = true;
    dom.logout.hidden = true;
  }

  function showProjects() {
    dom.loginView.hidden = true;
    dom.projectsView.hidden = false;
    dom.projectView.hidden = true;
    dom.userName.hidden = false;
    dom.userName.textContent = state.user.display_name;
    dom.logout.hidden = false;
  }

  function showProject() {
    dom.loginView.hidden = true;
    dom.projectsView.hidden = true;
    dom.projectView.hidden = false;
    dom.userName.hidden = false;
    dom.userName.textContent = state.user.display_name;
  }

  function openProjectForm(open) {
    dom.projectForm.hidden = !open;
    if (open) dom.projectName.focus();
  }

  function renderProjects() {
    dom.projectList.innerHTML = state.projects.map((project) => `
      <li class="project-item">
        <button class="project-row" type="button" data-project-id="${escapeHtml(project.id)}">
          <span class="project-row-main"><strong>${escapeHtml(project.name)}</strong><span>${escapeHtml(project.description || "No description yet.")}</span></span>
          <span class="project-row-meta"><span>${project.memory_count} memories</span><span>${project.member_count} people</span><span class="project-role">${escapeHtml(project.role || "member")}</span></span>
          <span class="project-row-arrow" aria-hidden="true">→</span>
        </button>
      </li>
    `).join("");
    dom.emptyProjects.hidden = state.projects.length !== 0;
  }

  function filteredMemories() {
    const needle = state.search.trim().toLowerCase();
    if (!needle) return state.memories;
    return state.memories.filter((memory) => [memory.title, memory.body, ...(memory.tags || [])].join(" ").toLowerCase().includes(needle));
  }

  function renderMemoryList() {
    const memories = filteredMemories();
    dom.memoryCount.textContent = String(state.memories.length);
    dom.memoryList.innerHTML = memories.map((memory) => `
      <button class="memory-row${memory.id === state.selected ? " is-selected" : ""}" type="button" data-memory-id="${escapeHtml(memory.id)}">
        <span class="memory-row-title">${escapeHtml(memory.title)}</span>
        <span class="memory-row-preview">${escapeHtml(memory.body)}</span>
        <span class="memory-row-meta">${escapeHtml((memory.tags || []).join(" · ") || "No tags")}</span>
      </button>
    `).join("");
    if (!memories.length) {
      dom.memoryList.innerHTML = state.memories.length
        ? '<p class="empty-list">No memories match that search.</p>'
        : '<p class="empty-list">No memories yet.</p>';
    }
  }

  function selectedMemory() { return state.memories.find((memory) => memory.id === state.selected) || null; }

  function renderEditor() {
    const memory = selectedMemory();
    dom.editorKicker.textContent = state.editing ? "Edit memory" : "Memory";
    dom.editorHeading.textContent = memory ? memory.title : (state.editing ? "New memory" : "Select a memory");
    dom.versionLabel.hidden = !memory;
    dom.versionLabel.textContent = memory ? `v${memory.version}` : "";
    dom.memoryForm.hidden = !state.editing;
    dom.emptyEditor.hidden = state.editing;
  }

  function fillEditor(memory) {
    dom.memoryTitle.value = memory?.title || "";
    dom.memoryBody.value = memory?.body || "";
    dom.memoryTags.value = (memory?.tags || []).join(", ");
    renderEditor();
  }

  function graphLayout(nodes) {
    const memories = nodes.filter((node) => node.type === "memory" && node.current);
    const people = nodes.filter((node) => node.type === "person");
    const positions = { ...state.positions };
    const centerX = 500; const centerY = 270;
    memories.forEach((node, index) => {
      if (!positions[node.id]) {
        const angle = memories.length ? (index / memories.length) * Math.PI * 2 - Math.PI / 2 : 0;
        const radius = memories.length === 1 ? 0 : Math.min(250, 115 + memories.length * 19);
        positions[node.id] = { x: centerX + Math.cos(angle) * radius, y: centerY + Math.sin(angle) * radius };
      }
    });
    people.forEach((node, index) => { if (!positions[node.id]) positions[node.id] = { x: 240 + index * 160, y: 520 }; });
    state.positions = positions;
    return positions;
  }

  function renderGraph() {
    const currentNodes = state.graph.nodes.filter((node) => node.type === "person" || (node.type === "memory" && node.current));
    dom.graphEmpty.hidden = currentNodes.some((node) => node.type === "memory");
    if (!currentNodes.length) { dom.graph.innerHTML = ""; return; }
    const positions = graphLayout(state.graph.nodes);
    const currentIds = new Set(currentNodes.map((node) => node.id));
    const edges = state.graph.edges.filter((edge) => currentIds.has(edge.from) && currentIds.has(edge.to));
    const transform = `translate(${state.pan.x} ${state.pan.y}) scale(${state.zoom})`;
    const edgeMarkup = edges.map((edge) => {
      const from = positions[edge.from]; const to = positions[edge.to];
      return from && to ? `<line class="graph-edge ${edge.type === "version" ? "version" : ""}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />` : "";
    }).join("");
    const nodeMarkup = currentNodes.map((node) => {
      const point = positions[node.id]; const memory = node.type === "memory";
      const label = memory ? node.title : node.name;
      const safeLabel = escapeHtml(label.length > 27 ? `${label.slice(0, 27)}…` : label);
      return `<g class="graph-node ${memory ? "memory" : "person"}${node.id === state.selected ? " is-selected" : ""}" data-node-id="${escapeHtml(node.id)}" transform="translate(${point.x} ${point.y})"><circle r="${memory ? 42 : 28}" /><text text-anchor="middle" y="${memory ? -3 : 4}">${safeLabel}</text>${memory ? `<text class="node-meta" text-anchor="middle" y="14">v${node.version}</text>` : ""}</g>`;
    }).join("");
    dom.graph.innerHTML = `<g class="graph-world" transform="${transform}">${edgeMarkup}${nodeMarkup}</g>`;
  }

  function renderMembers() {
    dom.memberList.innerHTML = state.members.length
      ? state.members.map((member) => `<div class="member-row"><span class="member-name">${escapeHtml(member.user_id)}</span><span class="member-role">${escapeHtml(member.role)}</span></div>`).join("")
      : '<p class="empty-list">No people have been added to this project.</p>';
  }

  function renderProject() {
    dom.projectTitle.textContent = state.project?.name || "";
    dom.projectDescriptionView.textContent = state.project?.description || "";
    renderMemoryList();
    renderEditor();
    renderGraph();
    renderMembers();
  }

  async function loadProjects() {
    showProjects();
    dom.projectList.setAttribute("aria-busy", "true");
    dom.projectList.innerHTML = '<li class="loading-state">Loading projects…</li>';
    dom.emptyProjects.hidden = true;
    try {
      const payload = await api("/api/projects");
      state.projects = payload.projects || [];
      renderProjects();
    } catch (error) {
      if (error.status === 401) showLogin();
      else {
        dom.projectList.innerHTML = `<li class="error-state">${escapeHtml(error.message || "Projects could not be loaded.")}</li>`;
        toast(error.message, "error");
      }
    } finally {
      dom.projectList.removeAttribute("aria-busy");
    }
  }

  async function openProject(projectId) {
    showProject();
    dom.graph.setAttribute("aria-busy", "true");
    dom.graphEmpty.hidden = false;
    dom.graphEmpty.innerHTML = "<strong>Loading project</strong><span>Getting the latest memories and connections.</span>";
    try {
      const [detail, graph] = await Promise.all([api(`/api/projects/${encodeURIComponent(projectId)}`), api(`/api/projects/${encodeURIComponent(projectId)}/graph`)]);
      state.project = detail.project;
      state.members = detail.members || [];
      state.memories = detail.memories || [];
      state.graph = graph;
      state.selected = state.memories[0]?.id || null;
      state.editing = false;
      state.search = "";
      state.positions = {};
      fillEditor(selectedMemory());
      renderProject();
    } catch (error) {
      dom.graph.innerHTML = "";
      dom.graphEmpty.hidden = false;
      dom.graphEmpty.innerHTML = `<strong>Project could not be loaded.</strong><span>${escapeHtml(error.message || "Try again.")}</span>`;
      toast(error.message, "error");
    } finally {
      dom.graph.removeAttribute("aria-busy");
    }
  }

  function selectMemory(memoryId) {
    const memory = state.memories.find((item) => item.id === memoryId);
    if (!memory) return;
    state.selected = memory.id;
    state.editing = true;
    fillEditor(memory);
    renderProject();
  }

  function newMemory() {
    state.selected = null;
    state.editing = true;
    fillEditor(null);
    renderProject();
    dom.memoryTitle.focus();
  }

  async function saveMemory(event) {
    event.preventDefault();
    if (!state.project) return;
    const payload = { title: dom.memoryTitle.value.trim(), body: dom.memoryBody.value.trim(), tags: dom.memoryTags.value.split(",").map((tag) => tag.trim()).filter(Boolean) };
    if (!payload.title || !payload.body) { toast("Add a title and memory text.", "error"); return; }
    const base = `/api/projects/${encodeURIComponent(state.project.id)}/memories`;
    formBusy(dom.memoryForm, true, "Saving…");
    try {
      const result = await api(state.selected ? `${base}/${encodeURIComponent(state.selected)}` : base, { method: state.selected ? "PATCH" : "POST", body: JSON.stringify(payload) });
      state.selected = result.memory.id;
      state.editing = true;
      await openProject(state.project.id);
      state.selected = result.memory.id;
      state.editing = true;
      fillEditor(result.memory);
      renderProject();
    } catch (error) { toast(error.message, "error"); }
    finally { formBusy(dom.memoryForm, false); }
  }

  async function createProject(event) {
    event.preventDefault();
    if (!dom.projectName.value.trim()) return;
    formBusy(dom.projectForm, true, "Creating…");
    try {
      const result = await api("/api/projects", { method: "POST", body: JSON.stringify({ name: dom.projectName.value.trim(), description: dom.projectDescription.value.trim() }) });
      dom.projectForm.reset(); openProjectForm(false); await loadProjects(); await openProject(result.project.id);
    } catch (error) { toast(error.message, "error"); }
    finally { formBusy(dom.projectForm, false); }
  }

  async function addMember(event) {
    event.preventDefault();
    formBusy(dom.memberForm, true, "Adding…");
    try {
      const result = await api(`/api/projects/${encodeURIComponent(state.project.id)}/members`, { method: "POST", body: JSON.stringify({ user_id: dom.memberUser.value.trim(), role: dom.memberRole.value }) });
      state.members.push(result.member); dom.memberUser.value = ""; renderMembers();
    } catch (error) { toast(error.message, "error"); }
    finally { formBusy(dom.memberForm, false); }
  }

  async function createAgent(event) {
    event.preventDefault();
    formBusy(dom.agentForm, true, "Creating…");
    try {
      const result = await api(`/api/projects/${encodeURIComponent(state.project.id)}/agents`, { method: "POST", body: JSON.stringify({ label: dom.agentLabel.value.trim() }) });
      dom.agentResult.hidden = false; dom.agentToken.textContent = result.token; dom.agentLabel.value = "";
      toast("Project token created. Copy it now.", "success");
    } catch (error) { toast(error.message, "error"); }
    finally { formBusy(dom.agentForm, false); }
  }

  function closePanels() { dom.peoplePanel.hidden = true; dom.agentPanel.hidden = true; }

  function bindGraphEvents() {
    dom.graph.addEventListener("click", (event) => {
      const node = event.target.closest("[data-node-id]");
      if (node && node.classList.contains("memory")) selectMemory(node.dataset.nodeId);
    });
    dom.graph.addEventListener("pointerdown", (event) => {
      const node = event.target.closest("[data-node-id]");
      if (node) {
        state.dragging = { type: "node", id: node.dataset.nodeId, x: event.clientX, y: event.clientY };
      } else {
        state.dragging = { type: "pan", x: event.clientX, y: event.clientY };
      }
      dom.graph.setPointerCapture?.(event.pointerId);
    });
    dom.graph.addEventListener("pointermove", (event) => {
      if (!state.dragging) return;
      const dx = (event.clientX - state.dragging.x) / state.zoom;
      const dy = (event.clientY - state.dragging.y) / state.zoom;
      if (state.dragging.type === "node") {
        const point = state.positions[state.dragging.id];
        if (point) { point.x += dx; point.y += dy; }
      } else { state.pan.x += dx; state.pan.y += dy; }
      state.dragging.x = event.clientX; state.dragging.y = event.clientY; renderGraph();
    });
    dom.graph.addEventListener("pointerup", () => { state.dragging = null; });
  }

  function bindEvents() {
    dom.loginForm.addEventListener("submit", async (event) => {
      event.preventDefault(); dom.loginError.hidden = true;
      try { const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username: dom.loginUsername.value.trim(), password: dom.loginPassword.value }) }); state.user = result.user; await loadProjects(); }
      catch (error) { dom.loginError.textContent = error.message; dom.loginError.hidden = false; }
    });
    dom.logout.addEventListener("click", async () => { try { await api("/api/auth/logout", { method: "POST", body: "{}" }); } catch (_) {} showLogin(); });
    dom.newProject.addEventListener("click", () => openProjectForm(true)); dom.cancelProject.addEventListener("click", () => openProjectForm(false)); dom.projectForm.addEventListener("submit", createProject);
    dom.projectList.addEventListener("click", (event) => { const card = event.target.closest("[data-project-id]"); if (card) openProject(card.dataset.projectId); });
    dom.emptyProjects.addEventListener("click", () => openProjectForm(true));
    dom.backProjects.addEventListener("click", () => { closePanels(); loadProjects(); });
    dom.newMemory.addEventListener("click", newMemory); dom.emptyEditor.addEventListener("click", newMemory); dom.memoryForm.addEventListener("submit", saveMemory); dom.cancelMemory.addEventListener("click", () => { state.editing = false; fillEditor(selectedMemory()); renderProject(); });
    dom.memoryList.addEventListener("click", (event) => { const row = event.target.closest("[data-memory-id]"); if (row) selectMemory(row.dataset.memoryId); });
    dom.memorySearch.addEventListener("input", (event) => { state.search = event.target.value; renderMemoryList(); });
    dom.peopleButton.addEventListener("click", () => { closePanels(); dom.peoplePanel.hidden = false; }); dom.agentButton.addEventListener("click", () => { closePanels(); dom.agentPanel.hidden = false; dom.agentLabel.focus(); });
    document.addEventListener("click", (event) => { const close = event.target.closest("[data-close-panel]"); if (close) document.querySelector(`#${close.dataset.closePanel}`).hidden = true; });
    dom.memberForm.addEventListener("submit", addMember); dom.agentForm.addEventListener("submit", createAgent);
    dom.copyToken.addEventListener("click", async () => { try { await navigator.clipboard.writeText(dom.agentToken.textContent); dom.copyToken.textContent = "Copied"; setTimeout(() => { dom.copyToken.textContent = "Copy"; }, 1400); } catch (_) { toast("Copy failed; select the token manually.", "error"); } });
    dom.fitGraph.addEventListener("click", () => { state.zoom = 1; state.pan = { x: 0, y: 0 }; renderGraph(); }); dom.zoomIn.addEventListener("click", () => { state.zoom = Math.min(2.5, state.zoom + .15); renderGraph(); }); dom.zoomOut.addEventListener("click", () => { state.zoom = Math.max(.55, state.zoom - .15); renderGraph(); });
    bindGraphEvents();
  }

  async function start() {
    bindEvents();
    try { const result = await api("/api/auth/me"); state.user = result.user; await loadProjects(); }
    catch (error) { if (error.status === 401) showLogin(); else toast("The workspace could not be reached.", "error"); }
  }

  start();
})();
