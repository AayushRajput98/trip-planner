/* ============================================================================
   APP — boot, nav, theme, print, checklist wiring, settings modal.
   ========================================================================== */
let TRIP = null;

function buildNav() {
  const bar = $("#navbar");
  const links = [["Overview","overview"],["Budget","budget"],["Itinerary","itinerary"],
                 ["Expenses","expenses"],["Food","food"],["Stays & Fuel","logistics"],
                 ["Variants","variants"],["Notes","notes"]];
  const frag = links.map(([l,id])=>`<button data-jump="${id}">${l}</button>`).join("");
  bar.insertAdjacentHTML("afterbegin", frag);
  bar.addEventListener("click", e=>{
    const id = e.target.dataset.jump;
    if(!id) return;
    document.getElementById(id).scrollIntoView({behavior:"smooth"});
    bar.querySelectorAll("[data-jump]").forEach(b=>b.classList.toggle("on", b===e.target));
  });
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
    try{ localStorage.setItem("fc_theme", document.body.classList.contains("dark")?"dark":"light"); }catch(e){}
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
    $("#settingsName").value = s.name || "";
    $("#settingsModal").hidden = false;
  };
  $("#settingsModal").addEventListener("click", e => {
    if (e.target.dataset.close !== undefined) $("#settingsModal").hidden = true;
  });
  $("#btnSaveSettings").onclick = () => {
    saveSettings({ token: $("#settingsToken").value.trim(), name: $("#settingsName").value.trim() });
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
  updateSyncMsg();
  try {
    if (localStorage.getItem("fc_theme") === "dark") document.body.classList.add("dark");
  } catch (e) { /* ignore */ }

  try {
    TRIP = await Api.getTrip();
  } catch (e) {
    $("#syncMsg").textContent = "Could not reach the backend: " + e.message;
    return;
  }
  document.getElementById("pageTitle").textContent = TRIP.meta.title;
  renderAll();
  buildNav();
  wireDays();
  wireChrome();
  wireChecklist();
  wireEditor();
  wireExpenses();

  const first = $("#day0");
  if (first) { first.classList.add("open"); loadPhotos(first.querySelector(".photos")); }

  loadExpenses().catch(e => console.error("expenses load failed", e));
}

boot();
