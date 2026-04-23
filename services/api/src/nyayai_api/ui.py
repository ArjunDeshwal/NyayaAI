"""Zero-build landing UI for the prototype.

Served at ``/`` so judges (and the team) can demo NyayaAI with a browser
instead of curl. The Flutter app in ``apps/flutter/`` is the canonical UI
for the finals submission; this page exists purely so the prototype
demo-video moment works without a Flutter SDK install.
"""

from __future__ import annotations

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NyayaAI — Algorithmic Fairness Audit</title>
  <meta name="description" content="NyayaAI: agentic, India-aware bias auditor for public-interest AI. Upload a dataset, get a DPDP Rule 13 + EU AI Act-aligned audit report." />
  <style>
    :root {
      --saffron: #FF9933;
      --green:   #138808;
      --navy:    #000080;
      --ink:     #1a1a1a;
      --muted:   #545454;
      --ok:      #0a7b2e;
      --warn:    #b45309;
      --fail:    #b91c1c;
      --bg:      #fafafa;
      --card:    #ffffff;
      --border:  #e5e5e5;
    }
    * { box-sizing: border-box; }
    html, body { margin:0; padding:0; background:var(--bg); color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans",sans-serif;
      font-size:14px; line-height:1.55;
    }
    .shell { max-width: 960px; margin: 0 auto; padding: 40px 24px 80px; }
    header { border-bottom:2px solid var(--border); padding-bottom:16px; margin-bottom:24px; }
    .brand { font-size:32px; font-weight:700; color:var(--navy); letter-spacing:-0.5px; }
    .brand .n { color:var(--saffron); }
    .brand .a { color:var(--green); }
    .tagline { color:var(--muted); margin-top:4px; font-size:15px; }
    .hindi { color:var(--muted); font-size:13px; margin-top:2px; }
    h2 { color:var(--navy); font-size:18px; margin:24px 0 12px; }
    .card { background:var(--card); border:1px solid var(--border); border-top:4px solid var(--navy);
            padding:24px 28px; margin-bottom:20px; border-radius:4px; }
    label { display:block; font-weight:600; margin:12px 0 4px; color:var(--ink); font-size:13px; }
    .hint { color:var(--muted); font-weight:400; font-size:12px; margin-left:6px; }
    input[type=text], input[type=number], textarea, select {
      width:100%; padding:8px 10px; font:inherit; border:1px solid #cbd5e1; border-radius:4px;
      background:#fff; min-height:38px;
    }
    input:focus, textarea:focus, select:focus {
      outline:3px solid var(--navy); outline-offset:1px; border-color:var(--navy);
    }
    textarea { min-height:72px; resize:vertical; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    @media (max-width:640px){ .row { grid-template-columns:1fr; } }
    button {
      background:var(--navy); color:#fff; border:none; padding:12px 22px; font:inherit;
      font-weight:600; border-radius:4px; cursor:pointer; min-height:48px;
    }
    button:focus { outline:3px solid var(--saffron); outline-offset:2px; }
    button:disabled { opacity:0.6; cursor:wait; }
    button.secondary { background:#fff; color:var(--navy); border:2px solid var(--navy); }
    .actions { margin-top:20px; display:flex; gap:10px; flex-wrap:wrap; }
    .example {
      margin-top:8px; background:#f0f9ff; border-left:4px solid var(--navy); padding:10px 14px;
      font-size:13px;
    }
    .example code { font-family:"SF Mono",Menlo,monospace; }
    .status { margin-top:24px; padding:16px 20px; border-radius:4px; }
    .status.running { background:#fef3c7; border-left:4px solid var(--warn); }
    .status.error   { background:#fee2e2; border-left:4px solid var(--fail); color:var(--fail); }
    .status.ok      { background:#f0f9ff; border-left:4px solid var(--navy); }
    .big { font-size:40px; font-weight:700; font-variant-numeric: tabular-nums; }
    .big.fail { color:var(--fail); }
    .big.pass { color:var(--ok); }
    .badge {
      display:inline-block; padding:3px 12px; border-radius:14px; font-size:11px;
      font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-left:8px;
    }
    .badge.pass   { background:#dcfce7; color:var(--ok); }
    .badge.fail   { background:#fee2e2; color:var(--fail); }
    .badge.major  { background:#fee2e2; color:var(--fail); }
    .badge.minor  { background:#fef3c7; color:var(--warn); }
    .badge.none   { background:#f3f4f6; color:var(--muted); }
    .spinner {
      display:inline-block; width:16px; height:16px; border:2px solid #d1d5db;
      border-top-color:var(--navy); border-radius:50%; animation:spin 0.8s linear infinite;
      vertical-align:middle; margin-right:10px;
    }
    @keyframes spin { to { transform:rotate(360deg); } }
    footer { margin-top:40px; color:var(--muted); font-size:12px; text-align:center; }
    footer a { color:var(--navy); }
    .pipeline { display:flex; gap:6px; font-size:12px; color:var(--muted); margin-top:6px; }
    .pipeline span { padding:2px 8px; background:#f3f4f6; border-radius:10px; }
    .pipeline span.live { background:var(--navy); color:#fff; }
    .pipeline span.done { background:#dcfce7; color:var(--ok); }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand"><span class="n">Nyaya</span><span class="a">AI</span></div>
      <div class="tagline">Agentic, India-aware bias auditor for public-interest AI</div>
      <div class="hindi">न्याय AI — सार्वजनिक-हित एआई के लिए पक्षपात लेखा-परीक्षक</div>
    </header>

    <div class="card">
      <h2>1. Describe the audit</h2>

      <div class="example">
        <strong>Try the built-in MUDRA-Lite demo.</strong>
        <button type="button" class="secondary" style="margin-top:6px; padding:6px 14px; min-height:32px; font-size:13px;"
                onclick="fillDemo()">Load MUDRA-Lite demo</button>
        <div style="margin-top:6px;">A synthetic loan-approval model with a known caste and gender disparity, calibrated to fail the 4/5ths rule.</div>
      </div>

      <form id="auditForm" onsubmit="runAudit(event)">
        <label for="dataset_name">Dataset name</label>
        <input id="dataset_name" type="text" required maxlength="200" />

        <label for="dataset_uri">Dataset URI <span class="hint">(server-side path to parquet or CSV)</span></label>
        <input id="dataset_uri" type="text" required placeholder="benchmarks/mudra-lite/data/mudra-lite.parquet" />

        <label for="goal">Goal</label>
        <textarea id="goal" required minlength="5" maxlength="2000"></textarea>

        <div class="row">
          <div>
            <label for="regime">Regulatory regime</label>
            <select id="regime">
              <option value="DPDP">DPDP (India, 2023)</option>
              <option value="EU_AI_ACT">EU AI Act</option>
              <option value="RBI">RBI Digital Lending</option>
            </select>
          </div>
          <div>
            <label for="model_id">Model id</label>
            <input id="model_id" type="text" value="unknown" />
          </div>
        </div>

        <label for="protected_columns">Protected columns <span class="hint">(comma-separated)</span></label>
        <input id="protected_columns" type="text" required placeholder="caste_disclosed,gender" />

        <div class="row">
          <div>
            <label for="outcome_column">Outcome column</label>
            <input id="outcome_column" type="text" required placeholder="approved" />
          </div>
          <div>
            <label for="model_score_column">Model-score column <span class="hint">(optional)</span></label>
            <input id="model_score_column" type="text" placeholder="model_score" />
          </div>
        </div>

        <div class="actions">
          <button type="submit" id="submitBtn">Run audit</button>
          <button type="button" class="secondary" onclick="window.open('/docs','_blank')">Open API docs</button>
        </div>
      </form>

      <div id="statusBox"></div>
      <div id="resultBox"></div>
    </div>

    <footer>
      Apache-2.0 · GSC 2026 · 4-person student team · All LLM calls routed through Model Armor + Sensitive Data Protection ·
      Backed by Google Gemini 3.1 Pro, Gemini 3 Flash, Gemini 3.1 Flash-Lite, Fairlearn, Vertex AI Agent Engine
    </footer>
  </div>

<script>
function fillDemo() {
  document.getElementById('dataset_name').value = 'mudra-lite';
  document.getElementById('dataset_uri').value = 'benchmarks/mudra-lite/data/mudra-lite.parquet';
  document.getElementById('goal').value = 'Audit MUDRA-Lite loan-approval model for caste and gender disparity per DPDP Rule 13 and RBI digital-lending norms.';
  document.getElementById('regime').value = 'DPDP';
  document.getElementById('model_id').value = 'mudra_lite_v1';
  document.getElementById('protected_columns').value = 'caste_disclosed,gender';
  document.getElementById('outcome_column').value = 'approved';
  document.getElementById('model_score_column').value = 'model_score';
}

async function runAudit(ev) {
  ev.preventDefault();
  const submitBtn = document.getElementById('submitBtn');
  const statusBox = document.getElementById('statusBox');
  const resultBox = document.getElementById('resultBox');

  submitBtn.disabled = true;
  resultBox.innerHTML = '';
  statusBox.innerHTML = `
    <div class="status running" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <strong>Running audit…</strong>
      <div class="pipeline">
        <span class="live">Planner (Gemini 3.1 Pro)</span>
        <span>Fairness engine (Fairlearn)</span>
        <span>Narrator (Gemini 3 Flash)</span>
        <span>Watcher (Gemini 3.1 Flash-Lite)</span>
      </div>
    </div>`;

  const body = {
    dataset_name: val('dataset_name'),
    dataset_uri:  val('dataset_uri'),
    goal:         val('goal'),
    regime:       val('regime'),
    model_id:     val('model_id'),
    model_task:   'binary_classification',
    protected_columns: val('protected_columns').split(',').map(s => s.trim()).filter(Boolean),
    outcome_column:    val('outcome_column'),
    model_score_column: val('model_score_column') || null,
    requested_attributes: [],
  };

  try {
    const r = await fetch('/audit/by-uri', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({detail: r.statusText}));
      throw new Error(err.detail || 'Audit failed');
    }
    const data = await r.json();
    statusBox.innerHTML = '';
    const di = data.overall_disparate_impact;
    const passFail = di !== null && di >= 0.8;
    resultBox.innerHTML = `
      <div class="status ok">
        <h2 style="margin-top:0;">Audit complete</h2>
        <div style="display:flex; gap:32px; flex-wrap:wrap; align-items:baseline; margin:12px 0;">
          <div>
            <div style="color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Overall disparate impact</div>
            <div class="big ${passFail ? 'pass' : 'fail'}">${di === null ? '—' : di.toFixed(3)}</div>
            <span class="badge ${passFail ? 'pass' : 'fail'}">
              ${di === null ? 'no data' : (passFail ? 'passes 4/5ths rule' : 'fails 4/5ths rule')}
            </span>
          </div>
          <div>
            <div style="color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Drift</div>
            <div class="big">
              <span class="badge ${data.drift_level}">${data.drift_level}</span>
            </div>
          </div>
          <div>
            <div style="color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Audit ID</div>
            <div style="font-family:'SF Mono',Menlo,monospace; font-size:14px;">${data.audit_id}</div>
          </div>
        </div>
        <div class="actions">
          <a href="${data.report_html_url}" target="_blank"><button type="button">Open full HTML report</button></a>
          <a href="${data.report_json_url}" target="_blank"><button type="button" class="secondary">Download JSON</button></a>
          ${data.report_pdf_url ? `<a href="${data.report_pdf_url}" target="_blank"><button type="button" class="secondary">Download PDF</button></a>` : ''}
        </div>
      </div>`;
  } catch (e) {
    statusBox.innerHTML = `<div class="status error" role="alert"><strong>Error:</strong> ${escapeHtml(e.message)}</div>`;
  } finally {
    submitBtn.disabled = false;
  }
}

function val(id) { return document.getElementById(id).value; }
function escapeHtml(s) { return String(s).replace(/[<>&'"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;',"'":'&#39;','"':'&quot;'}[c])); }
</script>
</body>
</html>
"""
