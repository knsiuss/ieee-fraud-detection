/* FraUd Detection Console — vanilla JS + Chart.js.
   Set window.API_BASE before this script to point at a remote FastAPI
   service; by default it uses the same origin. */

const API_BASE = (typeof window.API_BASE !== "undefined") ? window.API_BASE : "";
const TIER_META = {
  low: { label: "Low risk", cls: "low", color: "#16a34a" },
  medium: { label: "Medium risk", cls: "medium", color: "#ea580c" },
  high: { label: "High risk", cls: "high", color: "#dc2626" },
};

let lastValues = {};
let shapChart = null;

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) { /* not json */ }
    throw new Error(detail);
  }
  return res.json();
}

const $ = (sel) => document.querySelector(sel);

/* Tabs */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach((p) => {
      p.classList.toggle("active", p.id === "tab-" + btn.dataset.tab);
    });
  });
});

/* Health + model info on load */
(async function init() {
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
  try {
    const stats = await api("/api/stats");
    renderModelTab(stats);
  } catch (e) {
    console.error("stats failed", e);
  }
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
    tf.map((f, i) =>
      `<tr><td>${i + 1}</td><td>${f.feature}</td><td>${fmtInt(f.importance)}</td></tr>`
    ).join("");
}

function fmtInt(v) {
  if (v == null) return "–";
  return Number(v).toLocaleString("en-US");
}

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

async function loadExplanation(values) {
  try {
    const exp = await api("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    renderShap(exp.features || []);
  } catch (e) {
    console.error("explain failed", e);
  }
}

function renderShap(features) {
  if (!features.length) return;
  const rows = [...features].reverse();
  if (shapChart) shapChart.destroy();
  shapChart = new Chart($("#shap-chart"), {
    type: "bar",
    data: {
      labels: rows.map((f) => f.feature),
      datasets: [{
        data: rows.map((f) => f.contribution),
        backgroundColor: rows.map((f) => f.direction === "fraud" ? "#dc2626" : "#2563eb"),
        borderRadius: 4,
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
        x: { title: { display: true, text: "log-odds contribution" }, grid: { color: "#eef1f6" } },
        y: { grid: { display: false } },
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
  } catch (e) {
    alert("Feedback failed: " + e.message);
  }
}

/* Batch scoring */
$("#batch-btn").addEventListener("click", async () => {
  const fileInput = $("#batch-file");
  if (!fileInput.files.length) {
    showBatchError("Choose a CSV file first.");
    return;
  }
  $("#batch-btn").disabled = true;
  hideBatchError();
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  try {
    const res = await api("/api/predict/batch", { method: "POST", body: formData });
    renderBatch(res);
  } catch (e) {
    showBatchError(e.message);
  } finally {
    $("#batch-btn").disabled = false;
  }
});

function renderBatch(res) {
  const rows = res.rows || [];
  const dist = { low: 0, medium: 0, high: 0 };
  rows.forEach((r) => { dist[r.risk_tier] = (dist[r.risk_tier] || 0) + 1; });
  $("#batch-summary").innerHTML = `
    <span><b>${fmtInt(rows.length)}</b> transactions scored</span>
    <span style="color:#16a34a"><b>${fmtInt(dist.low)}</b> low</span>
    <span style="color:#ea580c"><b>${fmtInt(dist.medium)}</b> medium</span>
    <span style="color:#dc2626"><b>${fmtInt(dist.high)}</b> high</span>
  `;

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

  $("#batch-result").classList.remove("hidden");
  bindDownload(rows);
}

function bindDownload(rows) {
  const dl = $("#batch-dl");
  dl.onclick = () => {
    const header = "id,probability,risk_tier,action\n";
    const body = rows.map((r) =>
      [r.id ?? "", r.probability.toFixed(6), r.risk_tier, `"${r.action}"`].join(",")
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "scored_transactions.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  };
}

function showBatchError(msg) {
  const el = $("#batch-err");
  el.textContent = msg;
  el.classList.remove("hidden");
}
function hideBatchError() { $("#batch-err").classList.add("hidden"); }
