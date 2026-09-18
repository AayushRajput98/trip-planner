/* ============================================================================
   ICONS — a small inline-SVG set (stroke-based, 24x24 grid) used everywhere
   render.js/editor.js/expenses.js build icon markup in JS. Static icons in
   index.html are written as literal <svg> instead — no JS needed for those.
   ========================================================================== */
const ICON_PATHS = {
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/>',
  moon: '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
  printer: '<path d="M6 9V3h12v6M6 18H4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2M6 14h12v7H6z"/>',
  expand: '<path d="M8 9l4-4 4 4M8 15l4 4 4-4"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15 9l-2 6-6 2 2-6z"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  wallet: '<path d="M3 7a2 2 0 0 1 2-2h13a1 1 0 0 1 1 1v3M3 7v11a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1H8"/><circle cx="16" cy="14" r="1.2" fill="currentColor"/>',
  pencil: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  externalLink: '<path d="M14 3h7v7M21 3l-9 9M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/>',
  fork: '<path d="M4 2v6a2 2 0 0 0 4 0V2M6 8v14M16 2s-2 2-2 6 2 4 2 4v10"/>',
  bed: '<path d="M3 18v-7a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v2M3 18v3M3 18h18M21 18v3M12 13h7a2 2 0 0 1 2 2v3"/><circle cx="7" cy="9" r="1.5"/>',
  fuel: '<path d="M4 21V6a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v15M4 21h9M16 10l2.5 2.5A2 2 0 0 1 19 14v4a1.5 1.5 0 0 1-3 0v-3h-1"/><rect x="6" y="6" width="5" height="5" rx=".5"/>',
  shuffle: '<path d="M4 6h3l7 12h4M4 18h3l3-5M17 6h3M17 6l-2.5-2.5M17 6l-2.5 2.5M20 18l-2.5-2.5M20 18l-2.5 2.5"/>',
  notes: '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 3.5h6a1 1 0 0 1 1 1V6H8V4.5a1 1 0 0 1 1-1zM9 11h6M9 15h6M9 19h3"/>',
  checkSquare: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 12l2.5 2.5L16 9"/>',
  calculator: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8"/><circle cx="8.3" cy="11.3" r=".9" fill="currentColor" stroke="none"/><circle cx="12" cy="11.3" r=".9" fill="currentColor" stroke="none"/><circle cx="15.7" cy="11.3" r=".9" fill="currentColor" stroke="none"/><circle cx="8.3" cy="15" r=".9" fill="currentColor" stroke="none"/><circle cx="12" cy="15" r=".9" fill="currentColor" stroke="none"/><circle cx="15.7" cy="15" r=".9" fill="currentColor" stroke="none"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
  circle: '<circle cx="12" cy="12" r="9"/>',
  xCircle: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  mapPin: '<path d="M12 21s7-6.5 7-11a7 7 0 1 0-14 0c0 4.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  moonNight: '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
};

function icon(name, size) {
  const s = size || 18;
  const body = ICON_PATHS[name] || "";
  return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}
