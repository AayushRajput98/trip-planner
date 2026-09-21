/* ============================================================================
   APP — boot, tabs, the Trip Toolkit grid, theme, print, checklist
   wiring, the person picker, settings modal.
   ========================================================================== */
let TRIP = null;
const TABS = ["overview", "itinerary", "expenses", "history"];

function wireTabs() {
  document.querySelectorAll(".tabbtn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      TABS.forEach(t => { document.getElementById("tab-" + t).hidden = (t !== target); });
      document.querySelectorAll(".tabbtn").forEach(b => b.classList.toggle("on", b === btn));
    });
  });
}

function wireToolkit() {
  document.querySelectorAll(".quick-tile[data-popup]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById(btn.dataset.popup).hidden = false;
    });
  });
  document.querySelectorAll(".util-popup").forEach(popup => {
    popup.addEventListener("click", e => {
      if (e.target.closest("[data-close]")) popup.hidden = true;
    });
  });
}

function wirePerson() {
  function refreshLabel() {
    const p = getPerson();
    $("#personLabel").textContent = p || "Who's viewing?";
    $("#personAvatar").textContent = p ? p[0].toUpperCase() : "?";
  }
  $("#btnPerson").onclick = () => { $("#personModal").hidden = false; };
  $("#personModal").querySelectorAll("[data-person]").forEach(btn => {
    btn.addEventListener("click", () => {
      setPerson(btn.dataset.person);
      $("#personModal").hidden = true;
      refreshLabel();
    });
  });
  refreshLabel();
  if (!getPerson()) $("#personModal").hidden = false;
}

function wireDays() {
  $("#days").addEventListener("click", e=>{
    const head = e.target.closest("[data-toggle]");
    if(!head) return;
    const card = head.parentNode;
    card.classList.toggle("open");
    if(card.classList.contains("open")) loadPhotos(card.querySelector(".photos"));
  });
}

function wireChrome() {
  $("#btnExpand").onclick = ()=>{
    const cards = document.querySelectorAll(".day");
    const anyClosed = [...cards].some(c=>!c.classList.contains("open"));
    cards.forEach(c=>{
      c.classList.toggle("open", anyClosed);
      if(anyClosed) loadPhotos(c.querySelector(".photos"));
    });
  };
  $("#btnTheme").onclick = ()=>{
    document.body.classList.toggle("dark");
    const dark = document.body.classList.contains("dark");
    $("#themeIconMoon").hidden = dark;
    $("#themeIconSun").hidden = !dark;
    try{ localStorage.setItem("fc_theme", dark?"dark":"light"); }catch(e){}
  };
  $("#btnPrint").onclick = ()=>window.print();
}

function wireChecklist() {
  $("#checklist").addEventListener("change", async e=>{
    const id = e.target.dataset.id;
    if (!id) return;
    try {
      await Api.setChecklistItem(id, { done: e.target.checked });
      e.target.closest("li").classList.toggle("done", e.target.checked);
    } catch (err) {
      toast(err.message, true);
      e.target.checked = !e.target.checked;
    }
  });
}

function wireSettings() {
  $("#btnSettings").onclick = () => {
    const s = getSettings();
    $("#settingsToken").value = s.token || "";
    $("#settingsModal").hidden = false;
  };
  $("#settingsModal").addEventListener("click", e => {
    if (e.target.dataset.close !== undefined) $("#settingsModal").hidden = true;
  });
  $("#btnSaveSettings").onclick = () => {
    saveSettings({ token: $("#settingsToken").value.trim() });
    $("#settingsModal").hidden = true;
    updateSyncMsg();
  };
}

function updateSyncMsg() {
  $("#syncMsg").textContent = hasToken()
    ? "Connected — edits will be saved to the shared trip."
    : "View-only — open Settings and add the shared token to edit.";
}

async function boot() {
  wireSettings();
  wirePerson();
  updateSyncMsg();
  try {
    if (localStorage.getItem("fc_theme") === "dark") {
      document.body.classList.add("dark");
      $("#themeIconMoon").hidden = true;
      $("#themeIconSun").hidden = false;
    }
  } catch (e) { /* ignore */ }

  try {
    TRIP = await Api.getTrip();
  } catch (e) {
    $("#syncMsg").textContent = "Could not reach the backend: " + e.message;
    return;
  }
  document.getElementById("pageTitle").textContent = "TripCraft — " + TRIP.meta.title;
  renderAll();
  wireTabs();
  wireToolkit();
  wireDays();
  wireChrome();
  wireChecklist();
  wireEditor();
  wireExpenses();
  wireVersions();

  const first = $("#day0");
  if (first) { first.classList.add("open"); loadPhotos(first.querySelector(".photos")); }

  loadExpenses().catch(e => console.error("expenses load failed", e));
}

boot();
