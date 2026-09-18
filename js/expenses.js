/* ============================================================================
   EXPENSES — flat expense log: list, per-payer totals, add/delete.
   ========================================================================== */
let EXPENSES = [];

async function loadExpenses() {
  EXPENSES = await Api.listExpenses();
  renderExpenses();
}

function renderExpenses() {
  const totals = {};
  let grand = 0;
  EXPENSES.forEach(e => {
    totals[e.paidBy] = (totals[e.paidBy] || 0) + e.amount;
    grand += e.amount;
  });
  const R = n => "₹" + Math.round(n).toLocaleString("en-IN");

  $("#expenseTotals").innerHTML = [
    `<div class="stat"><div class="stat-ico">${icon("wallet", 14)}</div><div class="k">Total spent</div><div class="v">${R(grand)}</div><div class="n">${EXPENSES.length} entries</div></div>`,
    ...Object.entries(totals).map(([who, amt]) =>
      `<div class="stat"><div class="stat-ico">${icon("person", 14)}</div><div class="k">${who}</div><div class="v">${R(amt)}</div><div class="n">paid</div></div>`)
  ].join("");

  const catIcon = cat => {
    const c = (cat || "").toLowerCase();
    if (c.includes("fuel") || c.includes("petrol") || c.includes("diesel")) return "fuel";
    if (c.includes("food") || c.includes("lunch") || c.includes("dinner") || c.includes("meal")) return "fork";
    if (c.includes("stay") || c.includes("hotel") || c.includes("room")) return "bed";
    return "wallet";
  };

  const rows = [...EXPENSES].sort((a,b) => (a.date < b.date ? 1 : -1));
  $("#expenseTable").innerHTML = `
    <thead><tr><th>Date</th><th>Paid by</th><th>Category</th><th>Note</th><th class="num">Amount</th><th></th></tr></thead>
    <tbody>${rows.map(e => `
      <tr>
        <td>${e.date}</td>
        <td>${e.paidBy}</td>
        <td>${e.category ? `<span class="cat-ico">${icon(catIcon(e.category), 13)}</span>${e.category}` : ""}</td>
        <td>${e.note||""}</td>
        <td class="num">${R(e.amount)} ${e.currency !== "INR" ? e.currency : ""}</td>
        <td><button class="icon-btn delexpensebtn" data-id="${e.id}" title="Delete">${icon("x", 13)}</button></td>
      </tr>`).join("")}</tbody>`;
}

function addExpenseForm() {
  const today = new Date().toISOString().slice(0, 10);
  const defaultName = getPerson();
  openModal("Log an expense", `
    ${field("Date", "e_date", today, "date")}
    ${field("Amount (₹)", "e_amount", "", "number")}
    ${field("Paid by", "e_paidBy", defaultName)}
    ${field("Category", "e_category", "")}
    ${field("Note", "e_note", "")}
  `, async () => {
    await Api.addExpense({
      date: $("#e_date").value,
      amount: parseFloat($("#e_amount").value),
      paidBy: $("#e_paidBy").value.trim(),
      category: $("#e_category").value.trim() || null,
      note: $("#e_note").value.trim() || null,
    });
    await loadExpenses();
  });
}

function wireExpenses() {
  $("#btnAddExpense").addEventListener("click", addExpenseForm);
  $("#expenseTable").addEventListener("click", async e => {
    const btn = e.target.closest(".delexpensebtn");
    if (!btn) return;
    if (!(await confirmDialog("Delete this expense?"))) return;
    try {
      await Api.deleteExpense(btn.dataset.id);
      await loadExpenses();
    } catch (err) { toast(err.message, true); }
  });
}
