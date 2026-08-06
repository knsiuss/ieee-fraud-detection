/* IEEE-CIS Fraud Detection Console — vanilla JS + Chart.js.
   Set window.API_BASE before this script to point at a remote FastAPI
   service; by default it uses the same origin. */

const API_BASE = (typeof window.API_BASE !== "undefined") ? window.API_BASE : "";
const TIER_META = {
  low: { label: "Low risk", cls: "low", color: "#22c55e" },
  medium: { label: "Medium risk", cls: "medium", color: "#f59e0b" },
  high: { label: "High risk", cls: "high", color: "#ef4444" },
};
const PRESETS = {
  typical: { TransactionAmt: 150, card1: 9500, dist1: 12, C1: 1, C13: 1, D1: 0 },
  high: { TransactionAmt: 840, card1: 10616, dist1: 0, C1: 12, C13: 44, D1: 120 },
  low: { TransactionAmt: 45.5, card1: 13748, dist1: 7, C1: 1, C13: 1, D1: 0 },
};

let lastValues = {};
let shapChart = null;
let batchChart = null;
let lastShap = [];
let lastBatch = [];

const $ = (sel) => document.querySelector(sel);

/* Theme */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("#theme-toggle").textContent = theme === "dark" ? "Light" : "Dark";
  refreshCharts();
}
function initTheme() {
  const saved = localStorage.getItem("fd-theme") || "dark";
  applyTheme(saved);
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("fd-theme", next);
    applyTheme(next);
  });
}

function chartDefaults() {
  const dark = document.documentElement.dataset.theme === "dark";
  return { grid: dark ? "rgba(230,237,246,0.08)" : "rgba(16,24,40,0.07)", tick: dark ? "#8ba1bd" : "#667085" };
}

function refreshCharts() {
  if (lastShap.length) renderShap(lastShap);
  if (lastBatch.length) renderBatchChart(lastBatch);
}

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const body = await res.json(); detail = body.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

/* Tabs */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + btn.dataset.tab));
  });
});

/* Health + model info on load */
(async function init() {
  initTheme();
  setMode("checkout");
  loadSimFields();
  try {
    const health = await api("/api/health");
    const pill = $("#status-pill");
    if (health.model_present) {
      pill.textContent = "model online · " + (health.model_version || "v?");
      pill.className = "pill ok";
    } else {
      pill.textContent = "model not trained — run scripts/train_model.py";
      pill.className = "pill err";
    }
    loadModelTab();
  } catch (e) {
    $("#status-pill").textContent = "API unreachable";
    $("#status-pill").className = "pill err";
    console.error(e);
  }
})();

async function loadModelTab() {
  try { renderModelTab(await api("/api/stats")); } catch (e) { console.error("stats failed", e); }
}

function renderModelTab(stats) {
  const m = stats.model || {};
  const cards = [
    ["Model backend", m.backend || "–"],
    ["ROC-AUC (val)", Number(m.roc_auc).toFixed(4)],
    ["Features", String(m.n_features ?? "–")],
    ["Trained", (m.trained_at || "–").slice(0, 16)],
    ["Version", m.version || "–"],
    ["Status", m.status || "–"],
  ];
  $("#model-cards").innerHTML = cards.map(([k, v]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div></div>`
  ).join("");

  const o = stats.overview || {};
  const kpis = [
    ["Rows", fmtInt(o.total_rows)],
    ["Fraud rate", o.fraud_rate != null ? o.fraud_rate.toFixed(2) + "%" : "–"],
    ["Imbalance", o.imbalance_ratio != null ? "1 : " + fmtInt(o.imbalance_ratio) : "–"],
    ["Identity coverage", o.identity_coverage_pct != null ? o.identity_coverage_pct.toFixed(1) + "%" : "–"],
  ];
  $("#overview").innerHTML = kpis.map(([k, v]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div></div>`
  ).join("");

  const tf = stats.top_features || [];
  $("#topfeat-table").innerHTML =
    "<tr><th>#</th><th>Feature</th><th>Importance</th></tr>" +
    tf.map((f, i) => `<tr><td>${i + 1}</td><td>${f.feature}</td><td>${fmtInt(f.importance)}</td></tr>`).join("");
}

function fmtInt(v) {
  if (v == null) return "–";
  return Number(v).toLocaleString("en-US");
}

/* Input mode toggle: checkout (friendly) vs features (advanced) */
function setMode(mode) {
  const checkout = mode === "checkout";
  $("#sim-form").classList.toggle("hidden", !checkout);
  $("#advanced-wrap").classList.toggle("hidden", checkout);
  $("#mode-checkout").classList.toggle("active", checkout);
  $("#mode-advanced").classList.toggle("active", !checkout);
}
$("#mode-checkout").addEventListener("click", () => setMode("checkout"));
$("#mode-advanced").addEventListener("click", () => setMode("advanced"));

/* Checkout simulator */
let simFields = [];
async function loadSimFields() {
  try {
    const res = await api("/api/sim/fields");
    simFields = res.fields || [];
    renderSimFields();
  } catch (e) { console.error("sim fields failed", e); }
}
function renderSimFields() {
  $("#sim-fields").innerHTML = simFields.map((f) => {
    if (f.type === "select") {
      const opts = f.options.map((o) => `<option value="${o}">${o}</option>`).join("");
      return `<label>${f.label}<select name="${f.name}">${opts}</select></label>`;
    }
    return `<label>${f.label}<input type="number" name="${f.name}" min="${f.min ?? ""}" max="${f.max ?? ""}" value="${f.value}" step="1"></label>`;
  }).join("");
}
function gatherSimValues() {
  const values = {};
  $("#sim-fields").querySelectorAll("input, select").forEach((el) => {
    if (!el.name) return;
    if (el.type === "number") { const v = parseFloat(el.value); if (Number.isFinite(v)) values[el.name] = v; }
    else values[el.name] = el.value;
  });
  values.profile = $("#sim-profile").value;
  return values;
}
$("#sim-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = $("#sim-btn");
  btn.disabled = true; btn.textContent = "Detecting…";
  try {
    const sim = await api("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(gatherSimValues()),
    });
    renderResult(sim);
    loadExplanation(sim.mapped_values || {}, payload.profile);
    $("#result").classList.remove("hidden");
  } catch (e) {
    alert("Simulation failed: " + e.message);
  } finally {
    btn.disabled = false; btn.textContent = "Detect fraud";
  }
});

/* Presets */
document.querySelectorAll("#presets .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const vals = PRESETS[chip.dataset.preset] || {};
    Object.entries(vals).forEach(([name, val]) => {
      const el = document.querySelector(`#score-form input[name="${name}"]`);
      if (el) el.value = val;
    });
  });
});

/* Single scoring */
$("#score-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const btn = $("#score-btn");
  btn.disabled = true; btn.textContent = "Scoring…";
  lastValues = {};
  document.querySelectorAll("#score-form input[name]").forEach((el) => {
    const v = parseFloat(el.value);
    if (Number.isFinite(v)) lastValues[el.name] = v;
  });

  try {
    const pred = await api("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: lastValues }),
    });
    renderResult(pred);
    loadExplanation(lastValues);
    $("#result").classList.remove("hidden");
  } catch (e) {
    alert("Scoring failed: " + e.message);
  } finally {
    btn.disabled = false; btn.textContent = "Score transaction";
  }
});

function renderResult(pred) {
  const meta = TIER_META[pred.risk_tier] || TIER_META.low;
  $("#risk-tier").textContent = meta.label;
  $("#risk-tier").className = "tier " + meta.cls;
  $("#risk-action").textContent = pred.action;

  const pct = (pred.probability * 100).toFixed(2) + "%";
  $("#prob-label").textContent = pct;
  const bar = $("#prob-bar");
  bar.style.width = (pred.probability * 100) + "%";
  bar.className = "fill " + meta.cls;
  $("#fb-note").classList.add("hidden");
}

async function loadExplanation(values, profile) {
  try {
    const body = { values };
    if (profile) body.profile = profile;
    const exp = await api("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderExplanation(exp);
  } catch (e) { console.error("explain failed", e); }
}

function renderExplanation(exp) {
  lastShap = exp.features || [];
  renderShap(lastShap);

  $("#summary-text").textContent = exp.summary || "";
  const drivers = exp.drivers || [];
  $("#drivers-table").innerHTML = drivers.length
    ? "<tr><th>Signal</th><th>Value</th><th>Typical</th><th>Effect</th></tr>" +
      drivers.map((d) => {
        const fraud = d.direction === "fraud";
        const cls = fraud ? "high" : "low";
        const effect = fraud ? "raises risk" : "lowers risk";
        return `<tr>
          <td>${d.label}</td>
          <td>${d.value_text}</td>
          <td>${d.typical_text}</td>
          <td><span class="tag ${cls}">${effect}</span></td>
        </tr>`;
      }).join("")
    : "";
}

function renderShap(features) {
  if (!features.length) return;
  const d = chartDefaults();
  const rows = [...features].reverse();
  if (shapChart) shapChart.destroy();
  shapChart = new Chart($("#shap-chart"), {
    type: "bar",
    data: {
      labels: rows.map((f) => f.feature),
      datasets: [{
        data: rows.map((f) => f.contribution),
        backgroundColor: rows.map((f) => f.direction === "fraud" ? "#ef4444" : "#3b82f6"),
        borderRadius: 5,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => (c.raw >= 0 ? "+" : "") + c.raw.toFixed(4) } },
      },
      scales: {
        x: { title: { display: true, text: "log-odds contribution", color: d.tick }, ticks: { color: d.tick }, grid: { color: d.grid } },
        y: { ticks: { color: d.tick }, grid: { display: false } },
      },
    },
  });
}

/* Feedback */
$("#fb-safe").addEventListener("click", () => sendFeedback("safe"));
$("#fb-fraud").addEventListener("click", () => sendFeedback("fraud"));

async function sendFeedback(verdict) {
  try {
    const res = await api("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: lastValues, verdict }),
    });
    const note = $("#fb-note");
    note.textContent = `Recorded as ${verdict}. Retraining pool now has ${res.pool_size} label(s).`;
    note.classList.remove("hidden");
  } catch (e) { alert("Feedback failed: " + e.message); }
}

/* Batch — dropzone + file input */
const dropzone = $("#dropzone");
const batchFile = $("#batch-file");
dropzone.addEventListener("click", () => batchFile.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length) {
    batchFile.files = e.dataTransfer.files;
    updateDropLabel();
  }
});
batchFile.addEventListener("change", updateDropLabel);
function updateDropLabel() {
  const f = batchFile.files[0];
  $("#dz-label").innerHTML = f ? `<span class="dz-file">${f.name}</span> · ${fmtInt(f.size)} bytes` : "Drop a CSV here or click to browse";
}

/* Batch — sample template (real rows from the training set, full feature set) */
$("#sample-csv").addEventListener("click", () => {
  fetch(API_BASE + "/sample_transactions.csv")
    .then((r) => { if (!r.ok) throw new Error(); return r.blob(); })
    .then((blob) => { downloadBlob("sample_transactions.csv", blob, "text/csv"); })
    .catch(() => console.warn("sample file not served"));
});

/* Batch — scoring */
$("#batch-btn").addEventListener("click", async () => {
  if (!batchFile.files.length) { showBatchError("Choose a CSV file first."); return; }
  $("#batch-btn").disabled = true;
  hideBatchError();
  const formData = new FormData();
  formData.append("file", batchFile.files[0]);
  try {
    const res = await api("/api/predict/batch", { method: "POST", body: formData });
    lastBatch = res.rows || [];
    renderBatchSummary(lastBatch);
    renderBatchChart(lastBatch);
    renderBatchTable(lastBatch);
    $("#batch-result").classList.remove("hidden");
    bindDownload(lastBatch);
  } catch (e) {
    showBatchError(e.message);
  } finally {
    $("#batch-btn").disabled = false;
  }
});

function renderBatchSummary(rows) {
  const dist = { low: 0, medium: 0, high: 0 };
  rows.forEach((r) => { dist[r.risk_tier] = (dist[r.risk_tier] || 0) + 1; });
  const total = rows.length || 1;
  const highPct = (dist.high / total * 100).toFixed(1);
  $("#batch-summary").innerHTML = [
    ["Transactions", fmtInt(rows.length)],
    ["Low risk", fmtInt(dist.low), "low"],
    ["Medium risk", fmtInt(dist.medium), "medium"],
    ["High risk", fmtInt(dist.high), "high"],
    ["High %", highPct + "%", "high"],
  ].map(([k, v, cls]) =>
    `<div class="kpi"><div class="k">${k}</div><div class="v" style="color:var(--${cls || "text"})">${v}</div></div>`
  ).join("");
}

function renderBatchChart(rows) {
  const dist = { low: 0, medium: 0, high: 0 };
  rows.forEach((r) => { dist[r.risk_tier] = (dist[r.risk_tier] || 0) + 1; });
  if (batchChart) batchChart.destroy();
  batchChart = new Chart($("#batch-chart"), {
    type: "doughnut",
    data: {
      labels: ["Low", "Medium", "High"],
      datasets: [{
        data: [dist.low, dist.medium, dist.high],
        backgroundColor: ["#22c55e", "#f59e0b", "#ef4444"],
        borderColor: "#121a2b",
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { position: "bottom", labels: { color: chartDefaults().tick } },
        tooltip: { callbacks: { label: (c) => `${c.label}: ${c.raw} (${(c.raw / (rows.length || 1) * 100).toFixed(1)}%)` } },
      },
    },
  });
}

function renderBatchTable(rows) {
  $("#batch-table").innerHTML =
    "<tr><th>ID</th><th>Probability</th><th>Risk</th><th>Action</th></tr>" +
    rows.map((r) => {
      const meta = TIER_META[r.risk_tier] || TIER_META.low;
      return `<tr>
        <td>${r.id ?? ""}</td>
        <td>${(r.probability * 100).toFixed(2)}%</td>
        <td><span class="tag ${meta.cls}">${meta.label}</span></td>
        <td>${r.action}</td>
      </tr>`;
    }).join("");
}

function bindDownload(rows) {
  $("#batch-dl").onclick = () => {
    const header = "id,probability,risk_tier,action\n";
    const body = rows.map((r) =>
      [r.id ?? "", r.probability.toFixed(6), r.risk_tier, `"${r.action}"`].join(",")
    ).join("\n");
    downloadBlob("scored_transactions.csv", header + body, "text/csv");
  };
}

function downloadBlob(name, content, type) {
  const blob = new Blob([content], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

function showBatchError(msg) { const el = $("#batch-err"); el.textContent = msg; el.classList.remove("hidden"); }
function hideBatchError() { $("#batch-err").classList.add("hidden"); }
