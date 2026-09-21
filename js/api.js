/* ============================================================================
   UI helpers — non-blocking toast + confirm dialog. Native alert()/confirm()
   freeze the page (and browser automation) until dismissed, so everything
   here uses ordinary DOM elements instead.
   ========================================================================== */
let toastTimer = null;
function toast(message, isError = false) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle("err", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}

function confirmDialog(message) {
  return new Promise(resolve => {
    const modal = document.getElementById("confirmModal");
    const noteInput = document.getElementById("confirmMessage");
    document.getElementById("confirmMsg").textContent = message;
    noteInput.value = "";
    setNextMessage(null); // clear any stale note left over from a skipped edit
    modal.hidden = false;
    const cleanup = result => {
      modal.hidden = true;
      // setNextMessage lives in this same file, defined below.
      if (result) setNextMessage(noteInput.value);
      yesBtn.removeEventListener("click", onYes);
      noBtn.removeEventListener("click", onNo);
      resolve(result);
    };
    const yesBtn = document.getElementById("confirmYes");
    const noBtn = document.getElementById("confirmNo");
    const onYes = () => cleanup(true);
    const onNo = () => cleanup(false);
    yesBtn.addEventListener("click", onYes);
    noBtn.addEventListener("click", onNo);
  });
}

/* ============================================================================
   API — fetch wrapper for the FastAPI backend. Read calls need no auth;
   write calls attach the shared bearer token from localStorage.
   ========================================================================== */
const SETTINGS_KEY = "fc_settings";

function getSettings() {
  try { return JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}"); }
  catch (e) { return {}; }
}

function saveSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function hasToken() {
  return !!getSettings().token;
}

/* Which of the three of you is looking at the page right now — remembered
   per device, used to attribute expenses. Not an auth identity. */
const PERSON_KEY = "fc_person";

function getPerson() {
  try { return localStorage.getItem(PERSON_KEY) || ""; }
  catch (e) { return ""; }
}

function setPerson(name) {
  try { localStorage.setItem(PERSON_KEY, name); }
  catch (e) { /* ignore */ }
}

/* One-shot "why" note for the next write — set right before a save/delete
   that has a Note field, consumed (and cleared) by the very next api() call
   so no individual Api.* call site needs its own message parameter. */
let pendingMessage = null;
function setNextMessage(msg) {
  pendingMessage = (msg || "").trim() || null;
}

async function api(path, { method = "GET", body, auth = method !== "GET" } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getSettings().token;
    if (!token) throw new Error("No shared token set — open Settings and paste it first.");
    headers.Authorization = `Bearer ${token}`;
    headers["X-Editor-Name"] = getPerson() || "Someone";
    // Header values must stay ASCII-safe — encode in case a note has ₹, accents, etc.
    if (pendingMessage) headers["X-Edit-Message"] = encodeURIComponent(pendingMessage);
    pendingMessage = null;
  }
  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(`${method} ${path} failed (${res.status}): ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const Api = {
  getTrip: () => api("/api/trip"),

  updateMeta: patch => api("/api/meta", { method: "PUT", body: patch }),

  updateBudget: patch => api("/api/budget", { method: "PUT", body: patch }),

  listDays: () => api("/api/days"),
  addDay: day => api("/api/days", { method: "POST", body: day }),
  updateDay: (n, patch) => api(`/api/days/${encodeURIComponent(n)}`, { method: "PUT", body: patch }),
  deleteDay: n => api(`/api/days/${encodeURIComponent(n)}`, { method: "DELETE" }),
  reorderDays: order => api("/api/days/reorder", { method: "POST", body: order }),
  setTimetableStatus: (n, index, status) =>
    api(`/api/days/${encodeURIComponent(n)}/timetable/${index}/status`, { method: "PUT", body: { status } }),

  getReference: section => api(`/api/reference/${section}`),
  updateReference: (section, data) => api(`/api/reference/${section}`, { method: "PUT", body: data }),

  getChecklist: () => api("/api/checklist"),
  addChecklistItem: text => api("/api/checklist", { method: "POST", body: { text } }),
  setChecklistItem: (id, patch) => api(`/api/checklist/${id}`, { method: "PUT", body: patch }),
  removeChecklistItem: id => api(`/api/checklist/${id}`, { method: "DELETE" }),

  listExpenses: () => api("/api/expenses"),
  addExpense: entry => api("/api/expenses", { method: "POST", body: entry }),
  deleteExpense: id => api(`/api/expenses/${id}`, { method: "DELETE" }),

  getVersionFeed: (limit = 50) => api(`/api/versions/feed?limit=${limit}`),
  getVersionHistory: resource => api(`/api/versions/${resource}`),
  getVersionDiff: (resource, version) => api(`/api/versions/${resource}/${version}/diff`),
  restoreVersion: (resource, version) => api(`/api/versions/${resource}/${version}/restore`, { method: "POST" }),
  getTrash: () => api("/api/versions/trash"),
  restoreTrashItem: (resource, id) =>
    api(`/api/versions/trash/${resource}/${encodeURIComponent(id)}/restore`, { method: "POST" }),
};
