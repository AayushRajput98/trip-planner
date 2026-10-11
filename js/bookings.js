/* ============================================================================
   BOOKINGS — the Bookings tab: a per-person shelf of ID documents (shared
   with hotels at check-in) plus a list of hotel bookings with confirm/pending
   status and uploaded receipts. Mirrors expenses.js's shape: fetch on
   demand, render into containers, wire clicks. Loaded at boot alongside
   expenses, not lazily, since it's a top-level tab like Expenses.
   ========================================================================== */
let BOOKINGS = [];
let DOCUMENTS = [];

const PERSON_COLOR = { Aayush: "var(--maroon)", Upen: "var(--rust)", Vikrant: "var(--gold)" };
const STATUS_NEXT = { pending: "confirmed", confirmed: "pending" };

async function loadBookingsData() {
  [BOOKINGS, DOCUMENTS] = await Promise.all([Api.listBookings(), Api.listDocuments()]);
  renderDocPeople();
  renderBookingCards();
}

/* ---- Travel documents (per-person ID shelf) ---- */
function renderDocPeople() {
  $("#docPeople").innerHTML = MEMBERS.map(person => {
    const docs = DOCUMENTS.filter(d => d.person === person);
    return `
      <div class="card doc-card">
        <div class="tile-head">
          <span class="person-avatar" style="background:${PERSON_COLOR[person]}">${person[0]}</span>
          <div class="tile-title">${person}</div>
        </div>
        <div class="doc-chips">
          ${docs.length ? docs.map(d => `
            <span class="doc-chip">
              <a href="${d.url}" target="_blank" rel="noopener">${icon("externalLink", 12)} ${d.label}</a>
              <button class="doc-chip-x deldocbtn" data-id="${d.id}" title="Remove">${icon("x", 10)}</button>
            </span>`).join("") : `<span class="small">No ID uploaded yet</span>`}
        </div>
        <button class="btn secondary small adddocbtn" data-person="${person}">
          ${icon("plus", 13)} Upload ID
        </button>
      </div>`;
  }).join("");
}

function addDocumentForm(person) {
  openModal(`Upload ID — ${person}`, `
    ${field("Label", "doc_label", "Aadhaar")}
    <div class="field"><label>File (image or PDF)</label><input type="file" id="doc_file" accept="image/*,.pdf"></div>
  `, async () => {
    const file = $("#doc_file").files[0];
    const label = $("#doc_label").value.trim();
    if (!file) throw new Error("Choose a file first.");
    if (!label) throw new Error("Give it a label, e.g. Passport.");
    const uploaded = await Api.uploadFile(file);
    await Api.addDocument({ person, label, url: uploaded.url, name: uploaded.name });
    await loadBookingsData();
  });
}

/* ---- Hotel bookings ---- */
function bookingReceiptsHtml(b) {
  return (b.receipts || []).map(r => `
    <span class="doc-chip">
      <a href="${r.url}" target="_blank" rel="noopener">${icon("externalLink", 12)} ${r.name || "Receipt"}</a>
      <button class="doc-chip-x delreceiptbtn" data-id="${b.id}" data-url="${r.url}" title="Remove">${icon("x", 10)}</button>
    </span>`).join("");
}

function bookingCardHtml(b) {
  const nights = (b.checkIn && b.checkOut)
    ? Math.round((new Date(b.checkOut) - new Date(b.checkIn)) / 86400000)
    : null;
  return `
    <div class="card booking-card">
      <div class="tile-head">
        <div class="tile-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-7a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v2M3 18v3M3 18h18M21 18v3M12 13h7a2 2 0 0 1 2 2v3"/><circle cx="7" cy="9" r="1.5"/></svg></div>
        <div style="flex:1">
          <div class="tile-title">${b.hotel}</div>
          <div class="tile-sub">${b.city}</div>
        </div>
        <button class="booking-status is-${b.status} statusbookingbtn" data-id="${b.id}" data-next="${STATUS_NEXT[b.status]}">
          ${icon(b.status === "confirmed" ? "checkCircle" : "clock", 13)} ${b.status === "confirmed" ? "Confirmed" : "Pending"}
        </button>
      </div>
      ${(b.checkIn || b.checkOut) ? `<p class="small">${b.checkIn || "?"} → ${b.checkOut || "?"}${nights != null ? ` · ${nights} night${nights===1?"":"s"}` : ""}</p>` : ""}
      ${b.confirmationNumber ? `<p class="small">Confirmation #: <b>${b.confirmationNumber}</b></p>` : ""}
      ${b.notes ? `<p class="small">${b.notes}</p>` : ""}
      <div class="doc-chips">${bookingReceiptsHtml(b)}</div>
      <div class="editbar">
        <button class="btn secondary small uploadreceiptbtn" data-id="${b.id}">${icon("plus", 13)} Upload receipt</button>
        <button class="btn secondary small delbookingbtn" data-id="${b.id}">${icon("x", 13)} Delete</button>
      </div>
    </div>`;
}

function renderBookingCards() {
  $("#bookingsEmpty").hidden = BOOKINGS.length > 0;
  $("#bookingCards").innerHTML = BOOKINGS.map(bookingCardHtml).join("");
}

function addBookingForm() {
  openModal("Add booking", `
    ${field("Hotel name", "bk_hotel", "")}
    ${field("City", "bk_city", "")}
    <div class="grid g2">
      ${field("Check-in", "bk_checkIn", "", "date")}
      ${field("Check-out", "bk_checkOut", "", "date")}
    </div>
    <div class="field"><label>Status</label><select id="bk_status">
      <option value="pending" selected>Pending</option>
      <option value="confirmed">Confirmed</option>
    </select></div>
    ${field("Confirmation number", "bk_conf", "")}
    ${field("Notes", "bk_notes", "")}
  `, async () => {
    await Api.addBooking({
      hotel: $("#bk_hotel").value.trim(),
      city: $("#bk_city").value.trim(),
      checkIn: $("#bk_checkIn").value || null,
      checkOut: $("#bk_checkOut").value || null,
      status: $("#bk_status").value,
      confirmationNumber: $("#bk_conf").value.trim() || null,
      notes: $("#bk_notes").value.trim() || null,
    });
    await loadBookingsData();
  });
}

function wireBookings() {
  $("#btnAddBooking").addEventListener("click", addBookingForm);

  $("#docPeople").addEventListener("click", async e => {
    const addBtn = e.target.closest(".adddocbtn");
    if (addBtn) { addDocumentForm(addBtn.dataset.person); return; }
    const delBtn = e.target.closest(".deldocbtn");
    if (delBtn) {
      if (!(await confirmDialog("Remove this document?"))) return;
      try { await Api.deleteDocument(delBtn.dataset.id); await loadBookingsData(); }
      catch (err) { toast(err.message, true); }
    }
  });

  $("#bookingCards").addEventListener("click", async e => {
    const statusBtn = e.target.closest(".statusbookingbtn");
    if (statusBtn) {
      try { await Api.updateBooking(statusBtn.dataset.id, { status: statusBtn.dataset.next }); await loadBookingsData(); }
      catch (err) { toast(err.message, true); }
      return;
    }
    const delBtn = e.target.closest(".delbookingbtn");
    if (delBtn) {
      if (!(await confirmDialog("Delete this booking? You can bring it back later from History → Recently deleted."))) return;
      try { await Api.deleteBooking(delBtn.dataset.id); await loadBookingsData(); }
      catch (err) { toast(err.message, true); }
      return;
    }
    const delReceiptBtn = e.target.closest(".delreceiptbtn");
    if (delReceiptBtn) {
      const booking = BOOKINGS.find(b => b.id === delReceiptBtn.dataset.id);
      if (!booking) return;
      try {
        await Api.updateBooking(booking.id, { receipts: (booking.receipts || []).filter(r => r.url !== delReceiptBtn.dataset.url) });
        await loadBookingsData();
      } catch (err) { toast(err.message, true); }
      return;
    }
    const uploadBtn = e.target.closest(".uploadreceiptbtn");
    if (uploadBtn) {
      const input = $("#receiptFileInput");
      input.dataset.bookingId = uploadBtn.dataset.id;
      input.value = "";
      input.click();
    }
  });

  $("#receiptFileInput").addEventListener("change", async e => {
    const file = e.target.files[0];
    const bookingId = e.target.dataset.bookingId;
    const booking = BOOKINGS.find(b => b.id === bookingId);
    if (!file || !booking) return;
    try {
      const uploaded = await Api.uploadFile(file);
      await Api.updateBooking(bookingId, { receipts: [...(booking.receipts || []), uploaded] });
      await loadBookingsData();
      toast("Receipt uploaded.");
    } catch (err) { toast(err.message, true); }
  });
}
