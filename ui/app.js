// =============================================================
// Karim's Money - frontend logic v3
// Preserves v2 (defensive number checks, fmtAED/fmtMo helpers,
// dynamic title updates) and adds:
//   • Sidebar collapse/expand
//   • CSV upload / replace
//   • Question history (localStorage)
// =============================================================

const API_BASE = "http://localhost:8000";

const AGENT_ORDER = [
  "expense_analyzer",
  "risk_profiler",
  "investment_advisor",
  "goal_planner",
  "compliance_recommender",
];

const AGENT_DISPLAY = {
  expense_analyzer: { name: "Expense Analyzer", label: "Categorizing spend" },
  risk_profiler: { name: "Risk Profiler", label: "Assessing risk" },
  investment_advisor: { name: "Investment Advisor", label: "Matching products" },
  goal_planner: { name: "Goal Planner", label: "Drafting plan" },
  compliance_recommender: { name: "Compliance Recommender", label: "Final synthesis" },
};

const NAME_TO_KEY = {
  "Expense Analyzer": "expense_analyzer",
  "Risk Profiler": "risk_profiler",
  "Investment Advisor": "investment_advisor",
  "Goal Planner": "goal_planner",
  "Compliance Recommender": "compliance_recommender",
};

const HISTORY_KEY = "km_history_v1";
const SIDEBAR_KEY = "km_sidebar_collapsed_v1";
const MAX_HISTORY = 10;

let lastRunData = null;

// =============================================================
// On load
// =============================================================
window.addEventListener("DOMContentLoaded", () => {
  renderCategoryList(DEFAULT_CATEGORIES);

  document.getElementById("ask-btn").addEventListener("click", askAgents);

  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const input = document.getElementById("query-input");
      input.value = chip.getAttribute("data-query");
      input.focus();
    });
  });

  document.getElementById("query-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askAgents(); }
  });

  // Modal handlers
  document.getElementById("view-trace-btn").addEventListener("click", openTraceModal);
  document.getElementById("modal-close").addEventListener("click", closeTraceModal);
  document.getElementById("trace-modal").addEventListener("click", (e) => {
    if (e.target.id === "trace-modal") closeTraceModal();
  });
  document.getElementById("modal-copy").addEventListener("click", copyTraceToClipboard);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeTraceModal();
  });

  // NEW: sidebar toggle
  document.getElementById("sidebar-toggle").addEventListener("click", toggleSidebar);
  restoreSidebarState();

  // NEW: file upload
  document.getElementById("upload-btn").addEventListener("click", () => {
    document.getElementById("upload-input").click();
  });
  document.getElementById("upload-input").addEventListener("change", handleFileUpload);
  loadDataFiles();

  // NEW: history (loaded from server)
  document.getElementById("history-clear").addEventListener("click", clearHistory);
  loadHistoryFromServer();

  // NEW v4: Voice input (mic button → Compass Whisper)
  document.getElementById("mic-btn").addEventListener("click", openVoiceModal);
  document.getElementById("voice-cancel").addEventListener("click", cancelVoice);
  document.getElementById("voice-send").addEventListener("click", stopAndSendVoice);
  document.getElementById("voice-modal").addEventListener("click", (e) => {
    if (e.target.id === "voice-modal") cancelVoice();
  });

  // History collapse / expand toggle
  const historyToggle = document.getElementById("history-toggle");
  const historyList = document.getElementById("history-list");
  historyToggle.addEventListener("click", () => {
    const isCollapsed = historyList.classList.toggle("collapsed");
    historyToggle.classList.toggle("collapsed", isCollapsed);
    try { localStorage.setItem("km_history_collapsed", isCollapsed ? "1" : "0"); } catch (e) { }
  });
  try {
    const stored = localStorage.getItem("km_history_collapsed");
    const shouldCollapse = stored === null ? true : stored === "1";
    historyList.classList.toggle("collapsed", shouldCollapse);
    historyToggle.classList.toggle("collapsed", shouldCollapse);
  } catch (e) { /* keep default collapsed */ }
});

const DEFAULT_CATEGORIES = [
  { name: "Groceries", amount: 1896, flagged: false },
  { name: "Food Delivery", amount: 601, flagged: true },
  { name: "Dining Out", amount: 584, flagged: true },
  { name: "Online Shopping", amount: 462, flagged: true },
  { name: "Subscriptions", amount: 359, flagged: true },
  { name: "Coffee", amount: 177, flagged: false },
];

function renderCategoryList(categories) {
  const list = document.getElementById("category-list");
  const max = Math.max(...categories.map(c => c.amount));
  list.innerHTML = categories.map(c => `
    <div class="category-row ${c.flagged ? "flagged" : ""}">
      <span class="category-name">${escape(c.name)}</span>
      <div class="category-bar">
        <div class="category-fill" style="width: ${(c.amount / max * 100).toFixed(0)}%"></div>
      </div>
      <span class="category-amount">${Math.round(c.amount).toLocaleString()}</span>
    </div>
  `).join("");
}

// =============================================================
// Sidebar toggle
// =============================================================
function toggleSidebar() {
  const layout = document.getElementById("layout");
  layout.classList.toggle("sidebar-collapsed");
  try {
    localStorage.setItem(SIDEBAR_KEY,
      layout.classList.contains("sidebar-collapsed") ? "1" : "0");
  } catch (e) { /* localStorage unavailable */ }
}

function restoreSidebarState() {
  try {
    if (localStorage.getItem(SIDEBAR_KEY) === "1") {
      document.getElementById("layout").classList.add("sidebar-collapsed");
    }
  } catch (e) { /* ignore */ }
}

// =============================================================
// File upload
// =============================================================
async function loadDataFiles() {
  const container = document.getElementById("upload-files");
  try {
    const resp = await fetch(`${API_BASE}/data-files`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    renderFileList(data.files || []);
  } catch (err) {
    container.innerHTML = `<div class="upload-empty">Could not load file list (backend offline?)</div>`;
  }
}

function renderFileList(files, justUploaded = []) {
  const container = document.getElementById("upload-files");
  if (!files.length) {
    container.innerHTML = `<div class="upload-empty">No CSV files in data/ yet</div>`;
    return;
  }
  container.innerHTML = files.map(f => {
    const isFresh = justUploaded.includes(f.name);
    return `
      <div class="upload-file-row ${isFresh ? "just-uploaded" : ""}" data-kind="${escape(f.kind)}">
        <div class="upload-file-icon"></div>
        <div class="upload-file-name" title="${escape(f.name)}">${escape(f.name)}</div>
        <div class="upload-file-meta">${f.size_kb} KB</div>
      </div>`;
  }).join("");
}

async function handleFileUpload(e) {
  const files = Array.from(e.target.files || []);
  if (!files.length) return;

  const statusEl = document.getElementById("upload-status");
  statusEl.classList.remove("hidden", "success", "error");
  statusEl.classList.add("uploading");
  statusEl.textContent = `Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`;

  const uploaded = [];
  try {
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);
      const resp = await fetch(`${API_BASE}/upload-csv`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      uploaded.push(data.saved_as);
    }

    statusEl.classList.remove("uploading");
    statusEl.classList.add("success");
    statusEl.textContent = `✓ Replaced ${uploaded.length} file${uploaded.length === 1 ? "" : "s"}. Ask a question to use the new data.`;

    // Reload list to show new files (and flash the just-uploaded ones)
    const resp = await fetch(`${API_BASE}/data-files`);
    if (resp.ok) {
      const data = await resp.json();
      renderFileList(data.files || [], uploaded);
    }

    setTimeout(() => statusEl.classList.add("hidden"), 4000);
  } catch (err) {
    statusEl.classList.remove("uploading");
    statusEl.classList.add("error");
    statusEl.textContent = `Upload failed: ${err.message || err}`;
  } finally {
    // reset input so re-selecting same file works
    e.target.value = "";
  }
}

// =============================================================
// Question history - now stored server-side in data/history.json
// =============================================================
let historyCache = [];

async function loadHistoryFromServer() {
  try {
    const resp = await fetch(`${API_BASE}/history`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    historyCache = Array.isArray(data.entries) ? data.entries : [];
  } catch (err) {
    console.warn("Could not load history from server:", err);
    historyCache = [];
  }
  renderHistory();
}

async function saveHistoryEntry(entry) {
  try {
    const resp = await fetch(`${API_BASE}/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entry),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    historyCache = Array.isArray(data.entries) ? data.entries : historyCache;
    renderHistory();
  } catch (err) {
    console.warn("Could not save history entry:", err);
    // optimistic local update so UI still feels responsive
    historyCache.unshift(entry);
    historyCache = historyCache.slice(0, MAX_HISTORY);
    renderHistory();
  }
}

function renderHistory() {
  const list = document.getElementById("history-list");
  const clearBtn = document.getElementById("history-clear");
  const entries = historyCache;

  if (!entries.length) {
    list.innerHTML = `<div class="history-empty">No questions yet — try one of the chips →</div>`;
    clearBtn.classList.add("hidden");
    return;
  }
  clearBtn.classList.remove("hidden");

  list.innerHTML = entries.map((e, i) => {
    const date = new Date(e.timestamp);
    const timeStr = isNaN(date) ? "" : date.toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    });
    const elapsed = e.elapsed_seconds || e.elapsed || "?";
    return `
      <div class="history-item" data-idx="${i}" title="Click to restore this answer">
        <div class="history-query">${escape(e.query)}</div>
        <div class="history-meta">
          <span>${escape(timeStr)}</span>
          <span>·</span>
          <span>${escape(String(elapsed))}s</span>
          <span>·</span>
          <span>${e.mode === "live" ? "Compass" : "Sample"}</span>
        </div>
      </div>`;
  }).join("");

  list.querySelectorAll(".history-item").forEach(el => {
    el.addEventListener("click", () => {
      const idx = parseInt(el.getAttribute("data-idx"));
      restoreHistoryEntry(idx);
      list.querySelectorAll(".history-item").forEach(x => x.classList.remove("active"));
      el.classList.add("active");
    });
  });
}

function restoreHistoryEntry(idx) {
  const e = historyCache[idx];
  if (!e || !e.data) return;

  lastRunData = e.data;
  document.getElementById("welcome-state").classList.add("hidden");
  document.getElementById("thinking-card").classList.add("hidden");

  if (e.data.findings && e.data.findings.financial_summary) {
    updateDashboard(e.data.findings.financial_summary);
  }

  resetActivityFeed();
  resetStatusDots();
  (e.data.trace_events || []).forEach(ev => {
    const action = (ev.action || "").toLowerCase();
    if (action === "write_blackboard" && (ev.key === "transactions" || ev.key === "user_profile")) return;
    appendActivityItem(ev);
  });
  document.getElementById("activity-counter").textContent =
    `${document.querySelectorAll("#activity-feed .activity-item").length} events`;
  AGENT_ORDER.forEach(markDotDone);
  setStatusText("Restored from history");

  const elapsed = e.elapsed_seconds || e.elapsed || 0;
  renderAnswer(e.data.answer, e.data.agents_involved, elapsed,
    e.data.sample_mode, e.data.use_case_id, e.data.findings);
}

async function clearHistory() {
  if (!confirm("Clear all question history?")) return;
  try {
    const resp = await fetch(`${API_BASE}/history`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  } catch (err) {
    console.warn("Could not clear history on server:", err);
  }
  historyCache = [];
  renderHistory();
}

// =============================================================
// Submit query (preserves v2 thinking-state behaviour)
// =============================================================
async function askAgents() {
  const queryInput = document.getElementById("query-input");
  const query = queryInput.value.trim();
  if (!query) return;

  const askBtn = document.getElementById("ask-btn");
  askBtn.disabled = true;
  askBtn.querySelector(".ask-btn-label").textContent = "Thinking...";

  document.getElementById("welcome-state").classList.add("hidden");
  document.getElementById("answer-card").classList.add("hidden");
  resetActivityFeed();
  resetStatusDots();
  showThinkingState();
  setStatusText("Running agents...");

  const payload = {
    query,
    context: {
      user_id: "karim_mansour_001",
      csv_files: [
        "data/ADCB_Savings_KarimMansour.csv",
        "data/ADCB_CreditCard_KarimMansour.csv"
      ],
      profile_file: "data/user_profile.json"
    }
  };

  const progressCtrl = startThinkingProgress();

  try {
    const t0 = Date.now();
    const resp = await fetch(`${API_BASE}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    const data = await resp.json();
    lastRunData = data;
    const elapsed = ((Date.now() - t0) / 1000).toFixed(2);

    progressCtrl.complete();

    if (data.findings && data.findings.financial_summary) {
      updateDashboard(data.findings.financial_summary);
    }

    await sleep(400);
    hideThinkingState();
    await animateTraceEvents(data.trace_events || []);

    renderAnswer(data.answer, data.agents_involved, elapsed,
      data.sample_mode, data.use_case_id, data.findings);

    // NEW: save to history (server-side data/history.json)
    saveHistoryEntry({
      timestamp: new Date().toISOString(),
      query: query,
      elapsed_seconds: parseFloat(elapsed),
      mode: data.sample_mode ? "sample" : "live",
      data: data,
    });

    setStatusText(`Done · ${elapsed}s`);
  } catch (err) {
    console.error(err);
    progressCtrl.complete();
    hideThinkingState();
    setStatusText("Error");
    appendActivityItem({
      agent_name: "System",
      action: "Error",
      output_summary: err.message || String(err),
    });
  } finally {
    askBtn.disabled = false;
    askBtn.querySelector(".ask-btn-label").textContent = "Ask";
  }
}

// =============================================================
// Thinking state (unchanged from v2 — preserves dynamic title)
// =============================================================
function showThinkingState() {
  const card = document.getElementById("thinking-card");
  card.classList.remove("hidden");
  const container = document.getElementById("thinking-agents");
  container.innerHTML = AGENT_ORDER.map(key => `
    <div class="thinking-agent-pill" data-agent="${key}">
      <span class="dot-mini"></span>
      <span>${AGENT_DISPLAY[key].name}</span>
    </div>
  `).join("");
  document.getElementById("thinking-progress-bar").style.width = "0%";
}

function hideThinkingState() {
  document.getElementById("thinking-card").classList.add("hidden");
}

function startThinkingProgress() {
  const bar = document.getElementById("thinking-progress-bar");
  const sub = document.getElementById("thinking-sub");
  const pills = document.querySelectorAll(".thinking-agent-pill");

  let pct = 0;
  let agentIdx = 0;
  let stopped = false;
  const phrases = [
    "Parsing your bank statements…",
    "Categorizing transactions…",
    "Building your risk profile…",
    "Drafting savings plan…",
    "Critiquing for emergency-fund safety…",
    "Matching investment products…",
    "Composing final answer…",
  ];
  let phraseIdx = 0;

  const title = document.querySelector(".thinking-title");
  function rotateAgents() {
    if (stopped) return;
    pills.forEach((p, i) => {
      p.classList.toggle("active", i === agentIdx);
      p.classList.toggle("done", i < agentIdx);
    });
    if (title) {
      const currentKey = AGENT_ORDER[agentIdx];
      const currentName = currentKey && AGENT_DISPLAY[currentKey]
        ? AGENT_DISPLAY[currentKey].name
        : "Agents";
      title.textContent = `${currentName} Agent is reasoning`;
    }
    agentIdx = Math.min(agentIdx + 1, pills.length - 1);
  }
  const agentTimer = setInterval(rotateAgents, 4000);
  rotateAgents();

  function tickBar() {
    if (stopped) return;
    pct = Math.min(85, pct + Math.random() * 2.5);
    bar.style.width = pct.toFixed(0) + "%";
  }
  const barTimer = setInterval(tickBar, 600);

  function rotatePhrase() {
    if (stopped) return;
    sub.textContent = phrases[phraseIdx % phrases.length];
    phraseIdx++;
  }
  rotatePhrase();
  const phraseTimer = setInterval(rotatePhrase, 3500);

  return {
    complete() {
      stopped = true;
      clearInterval(agentTimer);
      clearInterval(barTimer);
      clearInterval(phraseTimer);
      bar.style.width = "100%";
      pills.forEach(p => { p.classList.remove("active"); p.classList.add("done"); });
      sub.textContent = "All agents finished.";
      const title = document.querySelector(".thinking-title");
      if (title) title.textContent = "All agents finished reasoning";
    }
  };
}

// =============================================================
// Activity feed (unchanged from v2)
// =============================================================
async function animateTraceEvents(events) {
  const filtered = events.filter(e => {
    const action = (e.action || "").toLowerCase();
    if (action === "write_blackboard" && (e.key === "transactions" || e.key === "user_profile")) return false;
    return true;
  });

  const counter = document.getElementById("activity-counter");
  let shown = 0;

  for (const event of filtered) {
    appendActivityItem(event);
    shown++;
    counter.textContent = `${shown} event${shown === 1 ? "" : "s"}`;

    const key = NAME_TO_KEY[event.agent_name];
    if (key) lightUpDot(key);

    const isCritique = (event.action || "").toLowerCase() === "critique";
    const isRevision = (event.action || "").toLowerCase().includes("revis");
    const isApproval = (event.action || "").toLowerCase().includes("approve");

    let delay = 110;
    if (isCritique) delay = 800;
    else if (isRevision) delay = 450;
    else if (isApproval) delay = 350;
    await sleep(delay);
  }

  for (const k of AGENT_ORDER) markDotDone(k);
}

function appendActivityItem(event) {
  const feed = document.getElementById("activity-feed");
  const empty = feed.querySelector(".activity-empty");
  if (empty) empty.remove();

  const action = (event.action || "").toLowerCase();
  const isCritique = action === "critique";
  const name = event.agent_name || "System";
  const key = NAME_TO_KEY[name] || (name.toLowerCase() === "system" ? "system" : name.toLowerCase().replace(/\s+/g, "_"));

  const num = String(feed.querySelectorAll(".activity-item").length + 1).padStart(2, "0");

  const target = event.target_agent && event.target_agent !== "Shared Blackboard"
    ? `<span class="act-arrow">→</span> <span class="act-target">${escape(event.target_agent)}</span>` : "";
  const summary = event.output_summary
    ? `<div class="act-summary">${escape(truncate(event.output_summary, 180))}</div>` : "";
  const tag = isCritique ? `<span class="act-critique-tag">Critique</span>` : "";

  const item = document.createElement("div");
  item.className = "activity-item" + (isCritique ? " critique" : "");
  item.setAttribute("data-agent", key);
  item.innerHTML = `
    <div class="act-icon"></div>
    <span class="act-num">${num}</span>
    ${tag}
    <div class="act-agent">${escape(name)}</div>
    <div class="act-action">${escape(prettyAction(event.action))} ${target}</div>
    ${summary}
  `;
  feed.appendChild(item);
  feed.scrollTop = feed.scrollHeight;
}

function resetActivityFeed() {
  const feed = document.getElementById("activity-feed");
  feed.innerHTML = `<div class="activity-empty"><div class="empty-icon">·</div>Agents are working...</div>`;
  document.getElementById("activity-counter").textContent = "0 events";
}

function resetStatusDots() {
  document.querySelectorAll(".dot").forEach(d => d.className = "dot");
}

function lightUpDot(key) {
  const dot = document.querySelector(`.dot[data-agent="${key}"]`);
  if (dot && !dot.classList.contains("done")) dot.classList.add("active");
}

function markDotDone(key) {
  const dot = document.querySelector(`.dot[data-agent="${key}"]`);
  if (dot) { dot.classList.remove("active"); dot.classList.add("done"); }
}

function setStatusText(t) { document.getElementById("status-text").textContent = t; }

// =============================================================
// Polished answer rendering (unchanged from v2)
// =============================================================
function renderAnswer(rawAnswer, agentsInvolved, elapsed, sampleMode, useCaseId, findings) {
  const card = document.getElementById("answer-card");
  const body = document.getElementById("answer-body");
  const meta = document.getElementById("answer-meta");

  const fs = findings?.financial_summary || {};
  const plan = findings?.plan || {};
  const invs = findings?.investment_recommendations || [];

  let html = "";

  const firstParagraph = extractDirectAnswer(rawAnswer);
  if (firstParagraph) {
    html += `<div class="answer-section">
      <div class="answer-body-text">${formatInline(firstParagraph)}</div>
    </div>`;
  }

  if (fs.monthly_income_aed) {
    html += `<div class="answer-stats">
      <div class="answer-stat">
        <div class="answer-stat-label">Income/mo</div>
        <div class="answer-stat-value">AED ${Math.round(fs.monthly_income_aed).toLocaleString()}</div>
      </div>
      <div class="answer-stat">
        <div class="answer-stat-label">Net savings</div>
        <div class="answer-stat-value">AED ${Math.round(fs.monthly_savings_aed).toLocaleString()} (${fs.savings_rate_pct?.toFixed(1)}%)</div>
      </div>
      <div class="answer-stat">
        <div class="answer-stat-label">Buffer</div>
        <div class="answer-stat-value">${fs.buffer_months?.toFixed(1)} months</div>
      </div>
      <div class="answer-stat">
        <div class="answer-stat-label">Risk band</div>
        <div class="answer-stat-value">${findings?.risk_profile?.band || "—"}</div>
      </div>
    </div>`;
  }

  if (plan.type === "goal_purchase" && plan.options && plan.options.length) {
    html += `<div class="answer-section">
      <h4 class="answer-section-title">Your options</h4>`;
    plan.options.forEach((opt, i) => {
      html += `<div class="answer-option">
        <div class="answer-option-bullet">${i + 1}</div>
        <div class="answer-option-text"><b>${escape(opt.label)}</b> — ${formatInline(escape(opt.description))}</div>
      </div>`;
    });
    html += `</div>`;
  }

  if (plan.type === "cut_expenses" && plan.targets) {
    html += `<div class="answer-section">
      <h4 class="answer-section-title">Cut targets (50% reduction)</h4>`;
    plan.targets.forEach((t, i) => {
      html += `<div class="answer-option">
        <div class="answer-option-bullet">${i + 1}</div>
        <div class="answer-option-text"><b>${escape(t.category)}</b>: <span class="aed-amount">AED ${Math.round(t.current_aed).toLocaleString()}</span> → <span class="aed-amount">AED ${Math.round(t.suggested_aed).toLocaleString()}</span>/month (saves <span class="aed-amount">AED ${Math.round(t.monthly_savings).toLocaleString()}</span>/month)</div>
      </div>`;
    });
    html += `<div style="margin-top: 12px; font-size: 0.9rem; color: var(--navy);"><b>Total potential savings:</b> <span class="aed-amount">AED ${Math.round(plan.total_monthly_savings).toLocaleString()}</span>/month · <span class="aed-amount">AED ${Math.round(plan.annual_savings).toLocaleString()}</span>/year</div>
    </div>`;
  }

  if (plan.type === "vacation") {
    const tier = plan.recommended_tier;
    const budget = plan.budget_tiers?.[tier];
    html += `<div class="answer-section">
      <h4 class="answer-section-title">Recommended timing & budget</h4>
      <div style="margin-bottom: 10px;"><b>Best month:</b> ${escape(plan.best_month)} — ${escape(plan.reasoning)}</div>`;
    if (budget) {
      html += `<div class="answer-stats">
        <div class="answer-stat"><div class="answer-stat-label">Flights</div><div class="answer-stat-value">AED ${budget.flight.toLocaleString()}</div></div>
        <div class="answer-stat"><div class="answer-stat-label">Hotel</div><div class="answer-stat-value">AED ${budget.hotel.toLocaleString()}</div></div>
        <div class="answer-stat"><div class="answer-stat-label">Food</div><div class="answer-stat-value">AED ${budget.food.toLocaleString()}</div></div>
        <div class="answer-stat"><div class="answer-stat-label">Total (${tier})</div><div class="answer-stat-value">AED ${budget.total_aed.toLocaleString()}</div></div>
      </div>
      <div style="font-size: 0.85rem; color: var(--navy-mute);">Destinations: ${budget.destination_examples?.slice(0, 3).join(" · ")}</div>`;
    }
    html += `</div>`;
  }

  const critiques = findings?.critiques || [];
  if (critiques.length > 0) {
    html += `<div class="answer-revision">
      <span class="answer-revision-tag">Revised after critique</span>
      <div><b>${escape(critiques[0].critic)}</b> challenged the plan: <i>${escape(critiques[0].critique)}</i></div>
      <div style="margin-top: 6px;">The plan was revised to preserve emergency runway before proceeding.</div>
    </div>`;
  }

  if (invs.length) {
    html += `<div class="answer-section">
      <h4 class="answer-section-title">Investment products matching your risk band</h4>
      <div class="answer-investments">`;
    invs.forEach(p => {
      html += `<div class="answer-investment">
        <div class="answer-investment-name">${escape(p.product)}</div>
        <div class="answer-investment-meta">${escape(p.type)} · ${escape(p.risk)} risk · min AED ${Math.round(p.min_aed).toLocaleString()}</div>
        <div class="answer-investment-return">Expected ${escape(p.expected_return)}/year</div>
      </div>`;
    });
    html += `</div></div>`;
  }

  const dMatch = rawAnswer.match(/(⚠️[\s\S]*$|This guidance is generated[\s\S]*$)/);
  if (dMatch) {
    html += `<div class="answer-disclaimer">${escape(dMatch[0].trim())}</div>`;
  }

  body.innerHTML = html;

  const modeTag = sampleMode ? "Sample mode" : "Live · Compass";
  meta.textContent = `${elapsed}s · ${agentsInvolved.length} agents · Use Case ${useCaseId} · ${modeTag}`;

  card.classList.remove("hidden");
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function extractDirectAnswer(raw) {
  const lines = raw.split("\n").map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (line.length < 30) continue;
    if (line.startsWith("**") || line.startsWith("Question") || line.startsWith("Your current")) continue;
    if (line.includes("AED") || line.includes("feasible") || line.includes("Yes") || line.includes("No") ||
      line.includes("Best") || line.includes("Total") || line.includes("Top") || line.includes("recommend")) {
      return line.slice(0, 400);
    }
  }
  return lines.find(l => l.length > 60) || raw.slice(0, 280);
}

function formatInline(text) {
  let s = text;
  s = s.replace(/\*\*([^*]+?)\*\*/g, "<b>$1</b>");
  s = s.replace(/AED\s+(\d{1,3}(?:[,\s]?\d{3})*(?:\.\d+)?)/g,
    (_, num) => `<span class="aed-amount">AED ${num}</span>`);
  return s;
}

// =============================================================
// Dashboard update (PRESERVES v2 defensive checks)
// =============================================================
function updateDashboard(fs) {
  if (!fs || typeof fs !== "object") {
    console.warn("[updateDashboard] no financial_summary in response", fs);
    return;
  }

  const fmtAED = v => (Number.isFinite(v) ? `AED ${Math.round(v).toLocaleString()}` : "—");
  const fmtMo = v => (Number.isFinite(v) ? `${v.toFixed(1)} mo` : "—");
  const fmtPct = v => (Number.isFinite(v) ? `${v.toFixed(1)}%` : "—");

  const income = Number(fs.monthly_income_aed);
  const fixed = Number(fs.monthly_fixed_costs_aed);
  const savings = Number(fs.monthly_savings_aed);
  const rate = Number(fs.savings_rate_pct);
  const buffer = Number(fs.current_buffer_aed);
  const bufferMo = Number(fs.buffer_months);
  const months = Number(fs.months_analyzed);

  document.getElementById("metric-income").textContent = fmtAED(income);
  document.getElementById("metric-fixed").textContent = fmtAED(fixed);

  const savingsEl = document.getElementById("metric-savings");
  savingsEl.textContent = fmtAED(savings);
  savingsEl.className = "tile-value " +
    (rate >= 15 ? "good" : rate >= 5 ? "warn" : "danger");
  document.getElementById("metric-savings-sub").textContent =
    `${fmtPct(rate)} rate · target 15-20%`;

  const bufferEl = document.getElementById("metric-buffer");
  bufferEl.textContent = fmtMo(bufferMo);
  bufferEl.className = "tile-value " +
    (bufferMo >= 6 ? "good" : bufferMo >= 3 ? "warn" : "danger");
  const bufSub = document.getElementById("metric-buffer-sub");
  if (bufSub) bufSub.textContent = "target 3-6 months";

  document.getElementById("metric-balance").textContent = fmtAED(buffer);

  const trendEl = document.getElementById("metric-trend");
  if (trendEl) {
    if (Number.isFinite(savings) && Number.isFinite(months) && months > 0) {
      const total = Math.round(savings * months);
      const sign = total >= 0 ? "+ " : "− ";
      trendEl.textContent = `${sign}AED ${Math.abs(total).toLocaleString()} over ${months} month${months === 1 ? "" : "s"}`;
      trendEl.className = "metric-trend " + (total >= 0 ? "up" : "down");
    } else {
      trendEl.textContent = "";
    }
  }

  if (fs.by_category) {
    const skip = new Set(["Salary", "Bonus", "Card Payment", "Savings Transfer",
      "ATM Cash", "Rent", "Mortgage", "Car Loan", "Education"]);
    const top = Object.entries(fs.by_category)
      .filter(([cat]) => !skip.has(cat))
      .slice(0, 6)
      .map(([cat, s]) => ({
        name: cat,
        amount: Math.round((s && s.avg_per_month) || 0),
        flagged: ["Food Delivery", "Subscriptions", "Coffee", "Online Shopping", "Dining Out"].includes(cat),
      }));
    if (top.length) renderCategoryList(top);
  }
}

// =============================================================
// Trace modal
// =============================================================
function openTraceModal() {
  if (!lastRunData) return;
  const events = lastRunData.trace_events || [];

  const body = document.getElementById("modal-body");
  body.innerHTML = events.map((e, i) => {
    const name = e.agent_name || "system";
    const key = NAME_TO_KEY[name] || (name.toLowerCase() === "system" ? "system" : name.toLowerCase().replace(/\s+/g, "_"));
    const action = (e.action || "").toLowerCase();
    const isCritique = action === "critique";
    const target = e.target_agent ? `<span style="color: var(--gold);">→ ${escape(e.target_agent)}</span>` : "";
    const summary = e.output_summary ? `<div class="trace-event-summary">${escape(e.output_summary)}</div>` : "";
    const ts = e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "";

    return `<div class="trace-event ${isCritique ? "critique" : ""}" data-agent="${key}">
      <div class="trace-event-num">${String(i + 1).padStart(2, "0")}</div>
      <div>
        <div class="trace-event-agent">${escape(name)} ${isCritique ? '<span class="act-critique-tag">Critique</span>' : ''}</div>
        <div class="trace-event-meta">${escape(prettyAction(e.action))} ${target}</div>
        ${summary}
        <div class="trace-event-time">${escape(ts)}</div>
      </div>
    </div>`;
  }).join("");

  document.getElementById("modal-sub").textContent =
    `${events.length} events · ${lastRunData.trace_path || "/logs/"}`;
  document.getElementById("trace-modal").classList.remove("hidden");
}

function closeTraceModal() {
  document.getElementById("trace-modal").classList.add("hidden");
  const copyBtn = document.getElementById("modal-copy");
  copyBtn.textContent = "Copy JSON";
  copyBtn.classList.remove("copied");
}

async function copyTraceToClipboard() {
  if (!lastRunData) return;
  const json = JSON.stringify(lastRunData.trace_events, null, 2);
  try {
    await navigator.clipboard.writeText(json);
    const btn = document.getElementById("modal-copy");
    btn.textContent = "Copied ✓";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "Copy JSON";
      btn.classList.remove("copied");
    }, 2000);
  } catch (err) {
    console.error("Clipboard write failed:", err);
  }
}

// =============================================================
// Utilities
// =============================================================
function prettyAction(a) { return (a || "").replace(/_/g, " "); }
function truncate(s, n) { if (!s) return ""; return s.length <= n ? s : s.slice(0, n).trim() + "…"; }
function escape(s) {
  if (s == null) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }


// =============================================================
// v4.1: Voice input - records WAV directly via Web Audio API
// Compass Whisper rejects webm; we capture raw PCM and encode as WAV in-browser.
// =============================================================
let voiceState = {
  audioContext: null,
  stream: null,
  source: null,
  analyser: null,
  processor: null,
  pcmChunks: [],
  sampleRate: 16000,
  startTs: 0,
  durationTimer: null,
  rafId: null,
  maxDurationMs: 60 * 1000,
  cancelled: false,
  recording: false,
};

async function openVoiceModal() {
  voiceState = {
    audioContext: null, stream: null, source: null, analyser: null,
    processor: null, pcmChunks: [], sampleRate: 16000,
    startTs: 0, durationTimer: null, rafId: null,
    maxDurationMs: 60 * 1000, cancelled: false, recording: false,
  };

  const modal = document.getElementById("voice-modal");
  const card = modal.querySelector(".voice-modal-card");
  const sub = document.getElementById("voice-modal-sub");
  const sendBtn = document.getElementById("voice-send");
  const cancelBtn = document.getElementById("voice-cancel");
  const visualizer = document.querySelector(".voice-visualizer");
  const duration = document.getElementById("voice-duration");

  card.classList.remove("transcribing");
  document.getElementById("voice-bars").classList.remove("show");
  sub.innerHTML = "Requesting microphone…";
  sendBtn.disabled = true;
  cancelBtn.disabled = false;
  cancelBtn.textContent = "Cancel";
  duration.textContent = "00:00";
  duration.classList.remove("warn");
  visualizer.removeAttribute("data-active");
  visualizer.style.setProperty("--audio-level", "0");

  modal.classList.remove("hidden");

  // Request microphone
  try {
    voiceState.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      }
    });
  } catch (err) {
    console.error("Mic permission denied:", err);
    sub.innerHTML = `<b>Microphone access denied.</b> Please allow mic access and try again.`;
    sendBtn.disabled = true;
    return;
  }

  // Create AudioContext (browser may use 44100 or 48000 — we resample later if needed)
  try {
    voiceState.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });
  } catch (err) {
    // Fallback: some browsers ignore the sampleRate hint
    voiceState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  voiceState.sampleRate = voiceState.audioContext.sampleRate;

  voiceState.source = voiceState.audioContext.createMediaStreamSource(voiceState.stream);

  // Branch 1: analyser for visualizer
  voiceState.analyser = voiceState.audioContext.createAnalyser();
  voiceState.analyser.fftSize = 256;
  voiceState.analyser.smoothingTimeConstant = 0.6;
  voiceState.source.connect(voiceState.analyser);

  // Branch 2: ScriptProcessor to capture raw PCM samples
  const bufSize = 4096;
  voiceState.processor = voiceState.audioContext.createScriptProcessor(bufSize, 1, 1);
  voiceState.processor.onaudioprocess = (e) => {
    if (!voiceState.recording) return;
    // IMPORTANT: copy the buffer — the underlying memory gets reused
    const input = e.inputBuffer.getChannelData(0);
    voiceState.pcmChunks.push(new Float32Array(input));
  };
  voiceState.source.connect(voiceState.processor);
  voiceState.processor.connect(voiceState.audioContext.destination);

  voiceState.recording = true;
  voiceState.startTs = Date.now();
  visualizer.setAttribute("data-active", "true");
  sub.innerHTML = `Listening — click <b>Stop &amp; Send</b> when done`;
  sendBtn.disabled = false;

  document.getElementById("mic-btn").classList.add("recording");
  visualizeLoop();
  voiceState.durationTimer = setInterval(updateDuration, 250);

  console.log("[voice] recording at", voiceState.sampleRate, "Hz");
}

function visualizeLoop() {
  if (!voiceState.analyser) return;
  const buffer = new Uint8Array(voiceState.analyser.frequencyBinCount);
  voiceState.analyser.getByteFrequencyData(buffer);
  let sum = 0;
  const range = Math.min(buffer.length, 40);
  for (let i = 0; i < range; i++) sum += buffer[i];
  const avg = sum / range / 255;
  const level = Math.min(1, Math.pow(avg, 0.6) * 2);
  const visualizer = document.querySelector(".voice-visualizer");
  if (visualizer) visualizer.style.setProperty("--audio-level", level.toFixed(3));
  voiceState.rafId = requestAnimationFrame(visualizeLoop);
}

function updateDuration() {
  const elapsed = Date.now() - voiceState.startTs;
  const seconds = Math.floor(elapsed / 1000);
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  const el = document.getElementById("voice-duration");
  el.textContent = `${mm}:${ss}`;
  if (elapsed > voiceState.maxDurationMs - 5000) el.classList.add("warn");
  if (elapsed >= voiceState.maxDurationMs) {
    document.getElementById("voice-modal-sub").innerHTML =
      `<b>Max length reached (60s).</b> Sending now…`;
    stopAndSendVoice();
  }
}

function stopAndSendVoice() {
  if (!voiceState.recording) return;
  voiceState.recording = false;
  // Disconnect graph to stop receiving samples
  try {
    if (voiceState.processor) voiceState.processor.disconnect();
    if (voiceState.analyser) voiceState.analyser.disconnect();
  } catch (e) { /* already disconnected */ }
  handleRecordingStop();
}

function cancelVoice() {
  voiceState.cancelled = true;
  voiceState.recording = false;
  cleanupRecording();
  document.getElementById("voice-modal").classList.add("hidden");
  document.getElementById("mic-btn").classList.remove("recording");
}

function cleanupRecording() {
  if (voiceState.rafId) cancelAnimationFrame(voiceState.rafId);
  if (voiceState.durationTimer) clearInterval(voiceState.durationTimer);
  voiceState.rafId = null;
  voiceState.durationTimer = null;
  try {
    if (voiceState.processor) voiceState.processor.disconnect();
    if (voiceState.analyser) voiceState.analyser.disconnect();
    if (voiceState.source) voiceState.source.disconnect();
  } catch (e) { }
  if (voiceState.stream) voiceState.stream.getTracks().forEach(t => t.stop());
  if (voiceState.audioContext && voiceState.audioContext.state !== "closed") {
    try { voiceState.audioContext.close(); } catch (e) { }
  }
  voiceState.stream = null;
  voiceState.audioContext = null;
  voiceState.analyser = null;
  voiceState.processor = null;
  voiceState.source = null;
}

/**
 * Encode an array of Float32 PCM chunks into a 16-bit mono WAV blob.
 * Whisper accepts WAV reliably regardless of provider.
 */
function pcmToWavBlob(pcmChunks, sampleRate) {
  const totalSamples = pcmChunks.reduce((a, c) => a + c.length, 0);
  const merged = new Float32Array(totalSamples);
  let offset = 0;
  for (const chunk of pcmChunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  // Convert Float32 [-1,1] -> Int16 [-32768, 32767]
  const int16 = new Int16Array(merged.length);
  for (let i = 0; i < merged.length; i++) {
    const s = Math.max(-1, Math.min(1, merged[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  // Build WAV file: 44-byte header + PCM data
  const dataBytes = int16.length * 2;
  const buffer = new ArrayBuffer(44 + dataBytes);
  const view = new DataView(buffer);

  let p = 0;
  function writeString(s) {
    for (let i = 0; i < s.length; i++) view.setUint8(p++, s.charCodeAt(i));
  }
  function writeUint32(n) { view.setUint32(p, n, true); p += 4; }
  function writeUint16(n) { view.setUint16(p, n, true); p += 2; }

  writeString("RIFF");
  writeUint32(36 + dataBytes);
  writeString("WAVE");
  writeString("fmt ");
  writeUint32(16);             // fmt chunk size
  writeUint16(1);              // PCM format
  writeUint16(1);              // mono
  writeUint32(sampleRate);
  writeUint32(sampleRate * 2); // byte rate
  writeUint16(2);              // block align (mono * 16-bit)
  writeUint16(16);             // bits per sample
  writeString("data");
  writeUint32(dataBytes);

  // PCM data, little-endian
  for (let i = 0; i < int16.length; i++) {
    view.setInt16(44 + i * 2, int16[i], true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}

async function handleRecordingStop() {
  if (voiceState.cancelled) {
    cleanupRecording();
    return;
  }

  const modal = document.getElementById("voice-modal");
  const card = modal.querySelector(".voice-modal-card");
  const sub = document.getElementById("voice-modal-sub");
  const sendBtn = document.getElementById("voice-send");
  const cancelBtn = document.getElementById("voice-cancel");
  const visualizer = document.querySelector(".voice-visualizer");

  card.classList.add("transcribing");
  document.getElementById("voice-bars").classList.add("show");
  visualizer.removeAttribute("data-active");
  sub.innerHTML = "Transcribing via Compass Whisper…";
  sendBtn.disabled = true;
  cancelBtn.disabled = true;

  // Build WAV from PCM chunks
  if (!voiceState.pcmChunks.length) {
    sub.innerHTML = `<b>No audio captured.</b> Try speaking closer to the microphone.`;
    cancelBtn.disabled = false;
    cancelBtn.textContent = "Close";
    cleanupRecording();
    return;
  }

  const audioBlob = pcmToWavBlob(voiceState.pcmChunks, voiceState.sampleRate);
  console.log("[voice] WAV blob built:", audioBlob.size, "bytes,",
    voiceState.pcmChunks.length, "chunks,", voiceState.sampleRate, "Hz");

  // Stop the mic stream now that we have all the audio
  if (voiceState.stream) voiceState.stream.getTracks().forEach(t => t.stop());
  if (voiceState.rafId) cancelAnimationFrame(voiceState.rafId);
  if (voiceState.durationTimer) clearInterval(voiceState.durationTimer);
  document.getElementById("mic-btn").classList.remove("recording");

  try {
    const formData = new FormData();
    formData.append("file", audioBlob, "voice.wav");

    const resp = await fetch(`${API_BASE}/transcribe`, {
      method: "POST",
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: "Transcription failed" }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    const text = (data.text || "").trim();

    if (!text || text.toLowerCase() === "you" || text.length < 2) {
      sub.innerHTML = `<b>No speech detected.</b> Try speaking closer to the microphone.`;
      cancelBtn.disabled = false;
      cancelBtn.textContent = "Close";
      return;
    }

    // Success: fill textarea, close modal
    const input = document.getElementById("query-input");
    input.value = text;
    input.focus();
    modal.classList.add("hidden");
    setStatusText("Voice transcribed · click Ask");
  } catch (err) {
    console.error("Transcription failed:", err);
    sub.innerHTML = `<b>Transcription failed.</b> ${escape(err.message || String(err))}`;
    cancelBtn.disabled = false;
    cancelBtn.textContent = "Close";
  } finally {
    cleanupRecording();
  }
}