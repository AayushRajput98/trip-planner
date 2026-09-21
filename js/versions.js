/* ============================================================================
   VERSIONS — the History tab: a merged timeline across all six resources,
   plus a "recently deleted" trash view with one-click restore. Mirrors
   expenses.js's shape: fetch on demand, render into a couple of containers,
   wire clicks. Loaded lazily the first time the History tab is opened.
   ========================================================================== */
const RESOURCE_META = {
  meta:      { label: "Trip info",  color: "var(--maroon)" },
  budget:    { label: "Budget",     color: "var(--gold)" },
  days:      { label: "Days",       color: "var(--green)" },
  reference: { label: "Reference",  color: "#3a6b8a" },
  checklist: { label: "Checklist",  color: "var(--rust)" },
  expenses:  { label: "Expenses",   color: "var(--meat)" },
};

// Singular noun for one trash item, since RESOURCE_META's label is plural
// ("Days", "Expenses") — used only in the restore-confirm sentence.
const ITEM_NOUN = { days: "day", checklist: "checklist item", expenses: "expense" };

const HISTORY = { feed: [], trash: [] };
let historyLoaded = false;
let historyFilter = "";
let historyView = "timeline";

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function timeAgo(iso) {
  const secs = (Date.now() - new Date(iso).getTime()) / 1000;
  if (secs < 60) return "just now";
  if (secs < 3600) return Math.floor(secs / 60) + "m ago";
  if (secs < 86400) return Math.floor(secs / 3600) + "h ago";
  if (secs < 86400 * 30) return Math.floor(secs / 86400) + "d ago";
  return new Date(iso).toLocaleDateString();
}

function fmtVal(v) {
  if (v === null || v === undefined) return "—";
  const s = typeof v === "string" ? v : JSON.stringify(v);
  return s.length > 140 ? s.slice(0, 140) + "…" : s;
}

function itemLabel(resource, content) {
  if (resource === "days") return `${content.n} — ${content.title || ""}`;
  if (resource === "checklist") return content.text || "(no text)";
  if (resource === "expenses") return `₹${content.amount} — ${content.paidBy}${content.note ? " · " + content.note : ""}`;
  return fmtVal(content);
}

function diffHtml(change) {
  const lines = [];
  if (change.kind === "dict") {
    for (const [k, v] of Object.entries(change.added)) lines.push(`<div class="diffline added">+ <b>${escapeHtml(k)}</b>: ${escapeHtml(fmtVal(v))}</div>`);
    for (const [k, v] of Object.entries(change.removed)) lines.push(`<div class="diffline removed">− <b>${escapeHtml(k)}</b>: ${escapeHtml(fmtVal(v))}</div>`);
    for (const [k, [o, n]] of Object.entries(change.changed)) lines.push(`<div class="diffline changed">~ <b>${escapeHtml(k)}</b>: ${escapeHtml(fmtVal(o))} → ${escapeHtml(fmtVal(n))}</div>`);
  } else {
    const idKey = change.id_key;
    change.added.forEach(item => lines.push(`<div class="diffline added">+ ${escapeHtml(fmtVal(item[idKey]))}: ${escapeHtml(fmtVal(item))}</div>`));
    change.removed.forEach(item => lines.push(`<div class="diffline removed">− ${escapeHtml(fmtVal(item[idKey]))}: ${escapeHtml(fmtVal(item))}</div>`));
    change.changed.forEach(c => lines.push(`<div class="diffline changed">~ ${escapeHtml(fmtVal(c.before[idKey]))}: ${escapeHtml(fmtVal(c.before))} → ${escapeHtml(fmtVal(c.after))}</div>`));
    if (change.reordered) lines.push(`<div class="diffline changed">Reordered</div>`);
  }
  return lines.join("") || `<div class="small">No further detail.</div>`;
}

async function loadHistory(force = false) {
  if (historyLoaded && !force) return;
  try {
    const [feed, trash] = await Promise.all([Api.getVersionFeed(80), Api.getTrash()]);
    HISTORY.feed = feed;
    HISTORY.trash = trash;
    historyLoaded = true;
  } catch (e) {
    toast("Could not load history: " + e.message, true);
  }
}

function rowHtml(e) {
  const meta = RESOURCE_META[e.resource] || { label: e.resource, color: "var(--muted)" };
  const canRestore = e.op !== "baseline";
  return `
    <div class="card tl-row">
      <div class="tl-dot" style="background:${meta.color}"></div>
      <div class="tl-body">
        <div class="tl-top">
          <span class="person-avatar tl-avatar">${escapeHtml((e.actor || "?")[0] || "?").toUpperCase()}</span>
          <strong>${escapeHtml(e.actor)}</strong>
          <span class="pill tl-badge" style="background:${meta.color}22;border-color:${meta.color}66;color:${meta.color}">${meta.label}</span>
          <span class="navspacer"></span>
          <span class="small tl-time">${timeAgo(e.ts)}</span>
        </div>
        <div class="tl-summary">${escapeHtml(e.summary)}</div>
        ${e.message ? `<div class="tl-message">“${escapeHtml(e.message)}”</div>` : ""}
        <div class="tl-actions">
          <button class="btn secondary small viewdiffbtn" data-resource="${e.resource}" data-version="${e.version}">View details</button>
          ${canRestore ? `<button class="btn secondary small restorebtn" data-resource="${e.resource}" data-version="${e.version}">Restore this version</button>` : ""}
        </div>
        <div class="tl-diff" hidden></div>
      </div>
    </div>`;
}

function trashHtml(row) {
  const meta = RESOURCE_META[row.resource] || { label: row.resource, color: "var(--muted)" };
  return `
    <div class="card trash-card">
      <span class="pill tl-badge" style="background:${meta.color}22;border-color:${meta.color}66;color:${meta.color}">${meta.label}</span>
      <div class="trash-label">${escapeHtml(itemLabel(row.resource, row.content))}</div>
      <div class="small">Deleted ${timeAgo(row.deletedAt)} by ${escapeHtml(row.deletedBy)}</div>
      <div class="tl-actions">
        <button class="btn secondary small restoretrashbtn" data-resource="${row.resource}" data-id="${escapeHtml(row.id)}">Restore</button>
      </div>
    </div>`;
}

function renderTimeline() {
  const rows = historyFilter ? HISTORY.feed.filter(e => e.resource === historyFilter) : HISTORY.feed;
  $("#timeline").innerHTML = rows.length
    ? rows.map(rowHtml).join("")
    : `<div class="card histempty">No changes yet — edits will show up here.</div>`;
}

function renderTrash() {
  $("#trash").innerHTML = HISTORY.trash.length
    ? `<div class="grid g3">${HISTORY.trash.map(trashHtml).join("")}</div>`
    : `<div class="card histempty">Nothing in the trash — deleted days, checklist items, and expenses show up here.</div>`;
  const badge = $("#trashCount");
  if (HISTORY.trash.length) { badge.textContent = HISTORY.trash.length; badge.hidden = false; }
  else badge.hidden = true;
}

function renderHistoryViews() {
  renderTimeline();
  renderTrash();
}

async function openHistoryTab() {
  await loadHistory();
  renderHistoryViews();
}

async function afterRestore() {
  await refreshAndRerender();
  await loadHistory(true);
  renderHistoryViews();
  toast("Restored.");
}

function wireVersions() {
  $('.tabbtn[data-tab="history"]').addEventListener("click", openHistoryTab);

  $("#histFilter").addEventListener("click", e => {
    const btn = e.target.closest(".chipbtn");
    if (!btn) return;
    historyFilter = btn.dataset.resource;
    $("#histFilter").querySelectorAll(".chipbtn").forEach(b => b.classList.toggle("on", b === btn));
    renderTimeline();
  });

  document.querySelector(".histswitch").addEventListener("click", e => {
    const btn = e.target.closest("[data-histview]");
    if (!btn) return;
    historyView = btn.dataset.histview;
    document.querySelectorAll(".histswitch .tabbtn").forEach(b => b.classList.toggle("on", b === btn));
    $("#histview-timeline").hidden = historyView !== "timeline";
    $("#histview-trash").hidden = historyView !== "trash";
  });

  $("#timeline").addEventListener("click", async e => {
    const viewBtn = e.target.closest(".viewdiffbtn");
    if (viewBtn) {
      const diffEl = viewBtn.closest(".tl-row").querySelector(".tl-diff");
      if (!diffEl.hidden) { diffEl.hidden = true; return; }
      if (!diffEl.dataset.loaded) {
        try {
          const diff = await Api.getVersionDiff(viewBtn.dataset.resource, viewBtn.dataset.version);
          diffEl.innerHTML = diffHtml(diff);
          diffEl.dataset.loaded = "1";
        } catch (err) { toast(err.message, true); return; }
      }
      diffEl.hidden = false;
      return;
    }
    const restoreBtn = e.target.closest(".restorebtn");
    if (restoreBtn) {
      const { resource, version } = restoreBtn.dataset;
      const label = (RESOURCE_META[resource] || {}).label || resource;
      if (!(await confirmDialog(`Restore ${label} to version ${version}? This creates a new version — nothing is lost.`))) return;
      try { await Api.restoreVersion(resource, version); await afterRestore(); }
      catch (err) { toast(err.message, true); }
    }
  });

  $("#trash").addEventListener("click", async e => {
    const btn = e.target.closest(".restoretrashbtn");
    if (!btn) return;
    const { resource, id } = btn.dataset;
    const noun = ITEM_NOUN[resource] || resource;
    if (!(await confirmDialog(`Restore this ${noun}?`))) return;
    try { await Api.restoreTrashItem(resource, id); await afterRestore(); }
    catch (err) { toast(err.message, true); }
  });
}
