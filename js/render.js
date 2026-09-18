/* ============================================================================
   RENDERERS — turn the parsed trip data model into the page shell's HTML.
   Ported from the original static page; the only change is that content now
   comes from window.TRIP (set by app.js after parsing data/trip-plan.md)
   instead of a hardcoded object.
   ========================================================================== */
const $ = s => document.querySelector(s);

/* Minimal inline markdown: **bold** / *italic* -> <b>/<i>. Existing raw HTML
   (e.g. hand-written <b>, <br>) passes through untouched. */
function md(s) {
  return String(s == null ? "" : s)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<i>$2</i>");
}

/* ---- Hero ---- */
function renderHero() {
  $("#hKicker").textContent = TRIP.meta.kicker;
  $("#hTitle").textContent  = TRIP.meta.title;
  $("#hSub").innerHTML      = md(TRIP.meta.sub);
  $("#hPills").innerHTML    = TRIP.meta.pills.map(p => `<span class="pill">${p}</span>`).join("");
}

/* ---- Route map (inline SVG, node coords are geographically proportional) ---- */
function renderMap() {
  const nodes = [
    ["DELHI",760,120,2],["Jaipur (lunch)",620,290,0],["Ajmer / Pushkar",500,335,1],
    ["Chittorgarh ×2",503,492,2],["Udaipur ×1",408,522,1],["Mount Abu",311,521,1],
    ["Barmer",179,407,0],["Jaisalmer ×2",131,288,2],["Bikaner",372,179,1]
  ];
  const path = "760,120 620,290 500,335 503,492 408,522 311,521 179,407 131,288 372,179 760,120";
  const dist = [["280",648,200],["135",548,316],["195",540,420],["120",428,516],
                ["165",330,548],["230",196,345],["155",92,348],["330",218,222]];
  $("#routeMap").innerHTML = `
  <svg viewBox="0 0 800 580" xmlns="http://www.w3.org/2000/svg">
    <polyline points="${path}" fill="none" stroke="var(--gold)" stroke-width="4" stroke-linejoin="round"/>
    <polyline points="372,179 760,120" fill="none" stroke="var(--warn)" stroke-width="4" stroke-dasharray="9,6"/>
    ${nodes.map(([l,x,y,s])=>{
      const r = s===2?11:s===1?7:5;
      const fill = s===2?"var(--maroon)":s===1?"var(--rust)":"#a98352";
      const anchor = x>600?"end":"start";
      const dx = x>600?-18:18;
      return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}"/>
              <text x="${x+dx}" y="${y+5}" text-anchor="${anchor}" font-size="16"
                    font-family="inherit" fill="currentColor"
                    font-weight="${s===2?700:400}" opacity="${s===0?.6:1}">${l}</text>`;
    }).join("")}
    ${dist.map(([t,x,y])=>`<text x="${x}" y="${y}" font-size="13" fill="var(--muted)">${t} km</text>`).join("")}
    <text x="540" y="140" font-size="13" fill="var(--warn)">460 km — return leg</text>
    <text x="20" y="572" font-size="12" fill="var(--muted)">Large nodes = 2 nights · faded = pass-through · schematic, geographically proportional</text>
  </svg>`;
  $("#fullMapLink").href = "https://www.google.com/maps/dir/Delhi/Jaipur/Ajmer/Pushkar/Chittorgarh/Udaipur/Mount+Abu/Barmer/Jaisalmer/Bikaner/Delhi";
}

/* ---- Distance ledger ---- */
function renderLedger() {
  const tot = TRIP.legs.reduce((a,l)=>a+l[2],0);
  $("#ledger").innerHTML = `
    <thead><tr><th>Day</th><th>Leg</th><th class="num">km</th><th class="num">Drive time</th>
    <th class="num">Door to door</th><th>Highways</th></tr></thead>
    <tbody>${TRIP.legs.map(l=>`<tr><td><b>${l[0]}</b></td><td>${l[1]}</td><td class="num">${l[2]}</td>
      <td class="num">${l[3]}</td><td class="num">${l[4]}</td><td>${l[5]}</td></tr>`).join("")}
      <tr style="background:var(--maroon)"><td colspan="2" style="color:#fff"><b>TOTAL</b></td>
      <td class="num" style="color:#fff"><b>~${tot.toLocaleString("en-IN")}</b></td>
      <td class="num" style="color:#fff"><b>~48h30</b></td><td class="num" style="color:#fff"><b>~54h</b></td><td></td></tr>
    </tbody>`;
}

/* ---- Day cards ---- */
const STATUS_CYCLE = { planned: "visited", visited: "skipped", skipped: "planned" };
const STATUS_LABEL = { planned: "mark visited", visited: "✓ visited", skipped: "✕ skipped" };

function renderDays() {
  $("#days").innerHTML = TRIP.days.map((d,i)=>`
    <article class="day${d.star?" star":""}" id="day${i}">
      <div class="dayhead" data-toggle="${i}">
        <div class="daynum">${d.n}${d.wd?`<div class="wd">${d.wd}</div>`:""}</div>
        <div class="daytitle">
          <div class="t">${d.title}</div>
          <div class="s">${d.stat||""}</div>
        </div>
        <span class="loadtag">${d.load||""}</span>
        <span class="chev">⌄</span>
      </div>
      <div class="daybody">
        ${(d.alerts||[]).map(a=>`<div class="callout ${a.type}">${md(a.html)}</div>`).join("")}
        <div class="photos" data-photos='${JSON.stringify(d.photos||[])}'></div>
        <h4>Timetable</h4>
        <ul class="tl">${(d.tl||[]).map((t,ti)=>`
          <li class="${t.key?"key":""} status-${t.status||"planned"}">
            <span class="time">${t.time}</span> &nbsp;<span class="what">${md(t.what)}</span>
            <button class="statusbtn" data-day="${d.n}" data-index="${ti}" data-next="${STATUS_CYCLE[t.status||"planned"]}">${STATUS_LABEL[t.status||"planned"]}</button>
            ${t.desc?`<div class="desc">${md(t.desc)}</div>`:""}
          </li>`).join("")}
        </ul>
        <h4>Logistics</h4>
        <div class="tablewrap"><table><tbody>
          ${(d.logistics||[]).map(([k,v])=>`<tr><td style="width:120px"><b>${k}</b></td><td>${md(v)}</td></tr>`).join("")}
        </tbody></table></div>
        ${d.map?`<p style="margin-top:12px"><a href="${d.map}" target="_blank" rel="noopener">▸ Open this leg in Google Maps</a></p>`:""}
        <div class="editbar">
          <button class="btn secondary editdaybtn" data-day="${d.n}">Edit day (JSON)</button>
          <button class="btn secondary deletedaybtn" data-day="${d.n}">Delete day</button>
        </div>
      </div>
    </article>`).join("");
}

/* ---- Food / stays / fuel tables ---- */
function renderTables() {
  $("#foodTable").innerHTML = `
    <thead><tr><th>Day</th><th>City</th><th>Where</th><th>What to order</th></tr></thead>
    <tbody>${TRIP.food.map(f=>`<tr${f[4]?' style="background:#fbf0ed"':''}>
      <td><b>${f[0]}</b></td><td>${f[1]}</td><td>${md(f[2])}</td><td>${md(f[3])}</td></tr>`).join("")}</tbody>`;

  $("#stayTable").innerHTML = `
    <thead><tr><th>Night</th><th>City</th><th>Pick</th><th>Notes for three</th></tr></thead>
    <tbody>${TRIP.stays.map(s=>`<tr><td><b>${s[0]}</b></td><td>${s[1]}</td><td>${md(s[2])}</td><td>${md(s[3])}</td></tr>`).join("")}</tbody>`;

  $("#fuelTable").innerHTML = `
    <thead><tr><th>#</th><th>Where</th><th class="num">Trip km</th><th>Why</th></tr></thead>
    <tbody>${TRIP.fuelStops.map(f=>`<tr><td><b>${f[0]}</b></td>
      <td>${f[4]?`<b>${f[1]}</b>`:f[1]}</td><td class="num">${f[2]}</td>
      <td>${f[4]?`<b>${f[3]}</b>`:f[3]}</td></tr>`).join("")}</tbody>`;
}

/* ---- Variants ---- */
function renderVariants() {
  $("#variantCards").innerHTML = TRIP.variants.map(v=>`
    <div class="card">
      <h3 style="margin-top:0">${v.name}</h3>
      <p class="small"><b>${v.km.toLocaleString("en-IN")} km total</b></p>
      <p>${md(v.how)}</p>
      <div class="callout"><b>Trade-off:</b> ${md(v.tradeoff)}</div>
    </div>`).join("");
}

/* ---- Notes ---- */
function renderNotes() {
  $("#noteBlocks").innerHTML = TRIP.notes.map(n=>`
    <div class="card"><h3 style="margin-top:0">${n.h}</h3>
      <ul style="margin:0;padding-left:18px;font-size:.9rem">${n.items.map(i=>`<li>${md(i)}</li>`).join("")}</ul>
    </div>`).join("");
}

/* ---- Sources ---- */
function renderSources() {
  const el = $("#sourcesList");
  if (!el) return;
  el.innerHTML = (TRIP.sources||[]).map(s=>`<li>${md(s)}</li>`).join("");
}

/* ---- Checklist (server-backed: TRIP.checklist = [{id,text,done}]) ---- */
function renderChecklist() {
  $("#checklist").innerHTML = TRIP.checklist.map(c=>`
    <li class="${c.done?"done":""}"><label><input type="checkbox" data-id="${c.id}" ${c.done?"checked":""}>${c.text}</label></li>`).join("");
}

/* ============================================================================
   BUDGET ENGINE
   ========================================================================== */
const FIELDS = [
  {id:"pax",   label:"Travellers",            type:"number", val:()=>TRIP.prices.defaults.pax,  min:1},
  {id:"veh",   label:"Vehicle variant",       type:"select"},
  {id:"kmpl",  label:"Real-world kmpl",       type:"number", val:()=>17.5, step:0.5},
  {id:"fuel",  label:"Petrol ₹/L (blended)",  type:"number", val:()=>TRIP.prices.blended},
  {id:"km",    label:"Total trip km",         type:"number", val:()=>TRIP.legs.reduce((a,l)=>a+l[2],0)},
  {id:"hotel", label:"Hotel ₹/night (room)",  type:"number", val:()=>TRIP.prices.defaults.hotelPerNight, step:250},
  {id:"nights",label:"Nights",                type:"number", val:()=>TRIP.prices.defaults.nights},
  {id:"food",  label:"Food ₹/person/day",     type:"number", val:()=>TRIP.prices.defaults.foodPerPersonDay, step:100},
  {id:"tolls", label:"Tolls & parking ₹",     type:"number", val:()=>TRIP.prices.defaults.tolls, step:100},
  {id:"entry", label:"Entries ₹/person",      type:"number", val:()=>TRIP.prices.defaults.entriesPerPerson, step:100},
  {id:"camp",  label:"Desert camp ₹/person",  type:"number", val:()=>TRIP.prices.defaults.campPerPerson, step:250},
  {id:"misc",  label:"Guides, tips, misc ₹",  type:"number", val:()=>TRIP.prices.defaults.misc, step:250}
];

function renderCalc() {
  $("#calcFields").innerHTML = FIELDS.map(f=>{
    if (f.type==="select") {
      return `<div class="fld"><label for="f_veh">${f.label}</label>
        <select id="f_veh">${TRIP.vehicle.map(v=>`<option value="${v.kmpl}">${v.label}</option>`).join("")}</select></div>`;
    }
    return `<div class="fld"><label for="f_${f.id}">${f.label}</label>
      <input id="f_${f.id}" type="number" value="${f.val()}" ${f.min!=null?`min="${f.min}"`:""} ${f.step?`step="${f.step}"`:""}></div>`;
  }).join("");

  $("#f_veh").addEventListener("change", e=>{ $("#f_kmpl").value = e.target.value; compute(); });
  $("#calcFields").addEventListener("input", compute);
  compute();
}

function compute() {
  const g = id => parseFloat($("#f_"+id).value) || 0;
  const pax = Math.max(1, g("pax"));
  const litres = g("km") / (g("kmpl") || 1);
  const fuel   = litres * g("fuel");
  const stay   = g("hotel") * g("nights");
  const food   = g("food") * pax * (g("nights") + 1);
  const entry  = g("entry") * pax;
  const camp   = g("camp")  * pax;
  const total  = fuel + stay + food + entry + camp + g("tolls") + g("misc");

  const R = n => "₹" + Math.round(n).toLocaleString("en-IN");
  const stats = [
    ["Total trip cost", R(total), `${pax} travellers, ${g("nights")} nights`],
    ["Per person",      R(total/pax), "all-in"],
    ["Petrol",          R(fuel), `${litres.toFixed(0)} L · ${(litres/45).toFixed(1)} full tanks`],
    ["Fuel per person", R(fuel/pax), "the big win of travelling three"],
    ["Stays",           R(stay), `${R(g("hotel"))}/night`],
    ["Food",            R(food), `${R(g("food"))}/person/day`],
    ["Cost per km",     "₹" + (total/g("km")).toFixed(1), "all-in, whole car"]
  ];
  $("#calcOut").innerHTML = stats.map(([k,v,n])=>
    `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${n}</div></div>`).join("");
}

/* ============================================================================
   PHOTOS — three tiers, tried in order, per image. First that loads wins.
     1. TRIP.photoUrls[slug]  — a URL you set via the editor. Always wins.
     2. images/<slug>.jpg     — a file sitting next to this page.
     3. Wikipedia's API       — only works when served over http(s), not file://.
   ========================================================================== */
const WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/";
const photoCache = {};
let wikiBlocked = false;
let photoStats = { ok:0, fail:0 };

function slugLabel(slug) {
  const w = TRIP.photoWiki && TRIP.photoWiki[slug];
  return (w && w[1]) || slug.replace(/-/g," ");
}

async function wikiPhoto(slug) {
  if (wikiBlocked) return null;
  if (photoCache[slug] !== undefined) return photoCache[slug];
  const w = TRIP.photoWiki && TRIP.photoWiki[slug];
  const title = (w && w[0]) || slug;
  try {
    const r = await fetch(WIKI_API + encodeURIComponent(title.replace(/ /g,"_")));
    if (!r.ok) throw new Error("http " + r.status);
    const j = await r.json();
    const src = (j.originalimage && j.originalimage.source) ||
                (j.thumbnail && j.thumbnail.source) || null;
    photoCache[slug] = src ? { src, page:(j.content_urls||{}).desktop && j.content_urls.desktop.page } : null;
  } catch (e) {
    wikiBlocked = true;
    photoCache[slug] = null;
  }
  return photoCache[slug];
}

function photoCard(slug) {
  const label   = slugLabel(slug);
  const custom  = ((TRIP.photoUrls && TRIP.photoUrls[slug]) || "").trim();
  const local   = "images/" + slug + ".jpg";
  const first   = custom || local;
  const gsearch = "https://www.google.com/search?tbm=isch&q=" + encodeURIComponent(label + " Rajasthan");
  return `
    <figure class="ph" style="margin:0" data-slug="${slug}">
      <div class="imgbox">
        <img src="${first}" alt="${label}" loading="lazy"
             data-tier="${custom ? 1 : 2}" onload="photoOK(this)" onerror="photoNext(this)">
      </div>
      <figcaption class="meta">
        <div class="nm">${label}</div>
        <div class="lk"><a href="${gsearch}" target="_blank" rel="noopener">photos ↗</a></div>
      </figcaption>
    </figure>`;
}

function photoOK(img) { img.style.opacity = 1; photoStats.ok++; }

async function photoNext(img) {
  const fig  = img.closest(".ph");
  const slug = fig.dataset.slug;
  const tier = parseInt(img.dataset.tier, 10);

  if (tier === 1) {
    img.dataset.tier = 2;
    img.src = "images/" + slug + ".jpg";
    return;
  }
  if (tier === 2) {
    img.dataset.tier = 3;
    const data = await wikiPhoto(slug);
    if (data && data.src) {
      img.src = data.src;
      if (data.page) {
        fig.querySelector(".nm").innerHTML = `<a href="${data.page}" target="_blank" rel="noopener">${slugLabel(slug)}</a>`;
      }
      return;
    }
  }
  photoStats.fail++;
  img.parentNode.innerHTML = `<div class="fallback">no image yet<br><span style="opacity:.7">${"images/" + slug + ".jpg"}</span></div>`;
  maybeShowBanner();
}

function maybeShowBanner() {
  if (document.getElementById("photoBanner")) return;
  if (photoStats.fail < 3) return;
  const slugs = Object.keys(TRIP.photoUrls||{}).slice(0,6).map(s=>"images/"+s+".jpg").join(" &middot; ");
  const el = document.createElement("div");
  el.id = "photoBanner";
  el.className = "callout warn";
  el.innerHTML = `
    <b>Photos aren't loading — here's why, and two ten-second fixes.</b><br>
    ${wikiBlocked ? "This page is open as a <code>file://</code> document, so your browser is blocking the automatic photo fetch from Wikipedia. That's a browser security rule, not a bug in the page." : "No local images found and no URLs set."}
    <div style="margin-top:8px"><b>Fix A — serve the file (gets all photos automatically).</b>
      Open a terminal in this folder and run <code>python3 -m http.server 8000</code>,
      then open <code>http://localhost:8000/</code>.</div>
    <div style="margin-top:6px"><b>Fix B — use your own photos (works offline, anywhere).</b>
      Make an <code>images</code> folder beside this page and drop in jpgs named by slug:
      <span class="small">${slugs} …</span><br>
      Or set a photo URL from the editor's day form.</div>`;
  const host = document.getElementById("itinerary");
  host.insertBefore(el, host.querySelector("#days"));
}

function loadPhotos(box) {
  if (!box || box.dataset.loaded) return;
  box.dataset.loaded = "1";
  const slugs = JSON.parse(box.dataset.photos || "[]");
  box.innerHTML = slugs.map(photoCard).join("");
}

function renderAll() {
  renderHero(); renderMap(); renderLedger(); renderDays(); renderTables();
  renderVariants(); renderNotes(); renderSources(); renderCalc(); renderChecklist();
}
