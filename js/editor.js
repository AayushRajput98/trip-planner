/* ============================================================================
   EDITOR — a small generic modal, plus one form builder per editable thing.
   Simple flat fields (meta, budget defaults, checklist item) get real inputs.
   Deeply-nested things (a day's timetable/alerts/logistics, reference
   tables) are edited as a JSON blob in a textarea — honest and simple, and
   the primary way most edits will actually happen is through the MCP server
   via Claude anyway, so this is the human fallback/power-user path rather
   than the main interface.
   ========================================================================== */
let modalSaveHandler = null;

function openModal(title, bodyHtml, onSave) {
  $("#modalTitle").textContent = title;
  $("#modalBody").innerHTML = bodyHtml;
  $("#modalMessage").value = "";
  setNextMessage(null); // clear any stale note left over from a skipped edit
  modalSaveHandler = onSave;
  $("#genericModal").hidden = false;
}

function closeModal() {
  $("#genericModal").hidden = true;
  modalSaveHandler = null;
}

async function refreshAndRerender() {
  const openIds = [...document.querySelectorAll(".day.open")].map(el => el.id);
  TRIP = await Api.getTrip();
  renderAll();
  openIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.classList.add("open"); loadPhotos(el.querySelector(".photos")); }
  });
}

function field(label, id, value, type = "text") {
  return `<div class="field"><label>${label}</label><input type="${type}" id="${id}" value="${(value ?? "").toString().replace(/"/g,"&quot;")}"></div>`;
}

function textareaField(label, id, value) {
  return `<div class="field"><label>${label}</label><textarea id="${id}" style="min-height:260px">${value ?? ""}</textarea></div>`;
}

/* ---- Meta ---- */
function editMetaForm() {
  const m = TRIP.meta;
  openModal("Edit trip info", `
    ${field("Title", "m_title", m.title)}
    ${field("Kicker", "m_kicker", m.kicker)}
    ${field("Subtitle (HTML ok)", "m_sub", m.sub)}
    ${field("Pills (comma-separated)", "m_pills", (m.pills||[]).join(", "))}
  `, async () => {
    await Api.updateMeta({
      title: $("#m_title").value,
      kicker: $("#m_kicker").value,
      sub: $("#m_sub").value,
      pills: $("#m_pills").value.split(",").map(s=>s.trim()).filter(Boolean),
    });
  });
}

/* ---- Budget defaults ---- */
function editBudgetForm() {
  const d = TRIP.prices.defaults;
  openModal("Edit budget defaults", `
    ${field("Travellers", "b_pax", d.pax, "number")}
    ${field("Nights", "b_nights", d.nights, "number")}
    ${field("Hotel ₹/night", "b_hotel", d.hotelPerNight, "number")}
    ${field("Food ₹/person/day", "b_food", d.foodPerPersonDay, "number")}
    ${field("Tolls & parking ₹", "b_tolls", d.tolls, "number")}
    ${field("Entries ₹/person", "b_entry", d.entriesPerPerson, "number")}
    ${field("Desert camp ₹/person", "b_camp", d.campPerPerson, "number")}
    ${field("Misc ₹", "b_misc", d.misc, "number")}
    ${field("Blended petrol ₹/L", "b_blended", TRIP.prices.blended, "number")}
  `, async () => {
    await Api.updateBudget({
      prices: {
        blended: parseFloat($("#b_blended").value),
        defaults: {
          pax: parseInt($("#b_pax").value, 10),
          nights: parseInt($("#b_nights").value, 10),
          hotelPerNight: parseFloat($("#b_hotel").value),
          foodPerPersonDay: parseFloat($("#b_food").value),
          tolls: parseFloat($("#b_tolls").value),
          entriesPerPerson: parseFloat($("#b_entry").value),
          campPerPerson: parseFloat($("#b_camp").value),
          misc: parseFloat($("#b_misc").value),
        },
      },
    });
  });
}

/* ---- Day (JSON blob) ---- */
function editDayForm(day) {
  openModal(`Edit ${day.n}`, textareaField("Day JSON", "d_json", JSON.stringify(day, null, 2)), async () => {
    const patch = JSON.parse($("#d_json").value);
    await Api.updateDay(day.n, patch);
  });
}

function addDayForm() {
  const template = { n: "Day X", title: "New day", wd: "", km: 0, load: "Light",
    stat: "", map: "", photos: [], alerts: [], tl: [], logistics: [] };
  openModal("Add day", textareaField("Day JSON", "d_json", JSON.stringify(template, null, 2)), async () => {
    const day = JSON.parse($("#d_json").value);
    await Api.addDay(day);
  });
}

/* ---- Reference sections (food/stays/fuelStops/variants/notes) ---- */
function editReferenceForm(section, label) {
  const current = TRIP[section];
  openModal(`Edit ${label} (raw JSON)`, textareaField(`${label} JSON`, "r_json", JSON.stringify(current, null, 2)), async () => {
    const data = JSON.parse($("#r_json").value);
    await Api.updateReference(section, data);
  });
}

/* ---- Checklist ---- */
function addChecklistItemForm() {
  openModal("Add checklist item", field("Item text", "c_text", ""), async () => {
    const text = $("#c_text").value.trim();
    if (text) await Api.addChecklistItem(text);
  });
}

/* ---- Wiring ---- */
function wireEditor() {
  $("#genericModal").addEventListener("click", e => {
    if (e.target.dataset.close !== undefined) closeModal();
  });
  $("#btnModalSave").addEventListener("click", async () => {
    if (!modalSaveHandler) return;
    try {
      setNextMessage($("#modalMessage").value);
      await modalSaveHandler();
      closeModal();
      await refreshAndRerender();
      toast("Saved.");
    } catch (e) {
      toast(e.message, true);
    }
  });

  $("#btnEditMeta").addEventListener("click", editMetaForm);
  $("#btnEditBudget").addEventListener("click", editBudgetForm);
  $("#btnAddDay").addEventListener("click", addDayForm);
  $("#btnEditFood").addEventListener("click", () => editReferenceForm("food", "Food"));
  $("#btnEditStays").addEventListener("click", () => editReferenceForm("stays", "Stays"));
  $("#btnEditFuel").addEventListener("click", () => editReferenceForm("fuelStops", "Fuel stops"));
  $("#btnEditVariants").addEventListener("click", () => editReferenceForm("variants", "Variants"));
  $("#btnEditNotes").addEventListener("click", () => editReferenceForm("notes", "Notes"));
  $("#btnAddChecklistItem").addEventListener("click", addChecklistItemForm);

  $("#days").addEventListener("click", async e => {
    const statusBtn = e.target.closest(".statusbtn");
    if (statusBtn) {
      e.stopPropagation();
      try {
        await Api.setTimetableStatus(statusBtn.dataset.day, parseInt(statusBtn.dataset.index, 10), statusBtn.dataset.next);
        await refreshAndRerender();
      } catch (err) { toast(err.message, true); }
      return;
    }
    const editBtn = e.target.closest(".editdaybtn");
    if (editBtn) {
      e.stopPropagation();
      const day = TRIP.days.find(d => d.n === editBtn.dataset.day);
      if (day) editDayForm(day);
      return;
    }
    const delBtn = e.target.closest(".deletedaybtn");
    if (delBtn) {
      e.stopPropagation();
      if (!(await confirmDialog(`Delete ${delBtn.dataset.day}? You can bring it back later from History → Recently deleted.`))) return;
      try {
        await Api.deleteDay(delBtn.dataset.day);
        await refreshAndRerender();
      } catch (err) { toast(err.message, true); }
    }
  });
}
