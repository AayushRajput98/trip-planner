/* ============================================================================
   EXPENSES — flat expense log: list, per-payer totals, add/delete, and a
   running "who owes whom" split evenly across the three travellers.
   ========================================================================== */
let EXPENSES = [];
const MEMBERS = ["Aayush", "Upen", "Vikrant"];

async function loadExpenses() {
  EXPENSES = await Api.listExpenses();
  renderExpenses();
}

/* Pure math: equal three-way split of everything logged so far, reduced to
   the fewest "X pays Y" transactions that settle every balance to zero.
   Not an accounting system — a running estimate that gets more accurate as
   more expenses are logged, same spirit as the Budget calculator. */
function computeSettlement(expenses, members) {
  const paid = {};
  members.forEach(m => paid[m] = 0);
  let total = 0;
  expenses.forEach(e => {
    paid[e.paidBy] = (paid[e.paidBy] || 0) + e.amount;
    total += e.amount;
  });
  const share = total / members.length;
  const net = {};
  members.forEach(m => net[m] = (paid[m] || 0) - share);

  const creditors = members.filter(m => net[m] > 0.5).map(m => ({ m, amt: net[m] })).sort((a,b) => b.amt - a.amt);
  const debtors   = members.filter(m => net[m] < -0.5).map(m => ({ m, amt: -net[m] })).sort((a,b) => b.amt - a.amt);
  const transactions = [];
  let i = 0, j = 0;
  while (i < debtors.length && j < creditors.length) {
    const amt = Math.min(debtors[i].amt, creditors[j].amt);
    transactions.push({ from: debtors[i].m, to: creditors[j].m, amount: amt });
    debtors[i].amt -= amt; creditors[j].amt -= amt;
    if (debtors[i].amt < 0.5) i++;
    if (creditors[j].amt < 0.5) j++;
  }
  return { total, share, paid, net, transactions };
}

function renderExpenses() {
  const hasExpenses = EXPENSES.length > 0;
  $("#expenseEmpty").hidden = hasExpenses;
  $("#expenseContent").hidden = !hasExpenses;
  $("#overviewSettle").hidden = !hasExpenses;
  if (!hasExpenses) return;

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

  renderSettleUp(R);
}

function settleRows(transactions, R, compact) {
  if (!transactions.length) {
    return `<div class="settle-balanced">${icon("checkCircle", 15)} Everyone's settled up — nothing owed either way.</div>`;
  }
  return `<div class="settle-rows${compact?" compact":""}">${transactions.map(t => `
    <div class="settle-row">
      <span class="settle-who settle-from">${t.from}</span>
      <span class="settle-arrow">→</span>
      <span class="settle-who settle-to">${t.to}</span>
      <span class="settle-amt">${R(t.amount)}</span>
    </div>`).join("")}</div>`;
}

function renderSettleUp(R) {
  const s = computeSettlement(EXPENSES, MEMBERS);

  $("#settleUpCard").innerHTML = `
    <div class="tile-head">
      <div class="tile-ico">${icon("person", 18)}</div>
      <div>
        <div class="tile-title">Settle up</div>
        <div class="tile-sub">Equal three-way split of everything logged — adjusts as you add more</div>
      </div>
    </div>
    ${settleRows(s.transactions, R, false)}`;

  $("#overviewSettle").innerHTML = `
    <div style="margin:14px 0 10px;border-top:1px solid var(--line);padding-top:14px;display:flex;align-items:center;gap:6px;font-weight:700;color:var(--ink);font-size:.82rem">
      ${icon("person",13)} Who owes whom
    </div>
    ${settleRows(s.transactions, R, true)}
    <div class="n" style="margin-top:8px">Based on ${EXPENSES.length} logged expense${EXPENSES.length===1?"":"s"} · split evenly, ${R(s.share)} each</div>`;
}

function addExpenseForm() {
  const today = new Date().toISOString().slice(0, 10);
  const defaultName = MEMBERS.includes(getPerson()) ? getPerson() : MEMBERS[0];
  openModal("Log an expense", `
    ${field("Date", "e_date", today, "date")}
    ${field("Amount (₹)", "e_amount", "", "number")}
    <div class="field"><label>Paid by</label><select id="e_paidBy">
      ${MEMBERS.map(m => `<option value="${m}" ${m===defaultName?"selected":""}>${m}</option>`).join("")}
    </select></div>
    ${field("Category", "e_category", "")}
    ${field("Note", "e_note", "")}
  `, async () => {
    await Api.addExpense({
      date: $("#e_date").value,
      amount: parseFloat($("#e_amount").value),
      paidBy: $("#e_paidBy").value,
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
    if (!(await confirmDialog("Delete this expense? You can bring it back later from History → Recently deleted."))) return;
    try {
      await Api.deleteExpense(btn.dataset.id);
      await loadExpenses();
    } catch (err) { toast(err.message, true); }
  });
}
