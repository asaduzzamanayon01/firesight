"use strict";

// Data helpers for the FireSight backtest dashboard.
// No DOM and no map code in this file, so it can also be run in node for testing.

// Light-to-dark purple ramp (ColorBrewer "BuPu"). Dark = higher risk percentile.
const RISK_STOPS = [
  "#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6",
  "#8c6bb1", "#88419d", "#810f7c", "#4d004b",
];
const RISK_RGB = RISK_STOPS.map(hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)));
const MISSING_COLOUR = "#cbd5e1";

const REQUIRED_COLUMNS = ["cell_id", "lat", "lon", "date", "probability", "actual", "risk_percentile"];
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;


// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

/**
 * Turn the text of forecast.csv into day-by-cell arrays.
 *
 * Returns { dates, cells, nDays, nCells, pct, prob, actual } where
 * pct/prob/actual are flat arrays indexed by (day * nCells + cellPosition).
 */
function parseForecast(text) {
  const lines = text.split(/\r?\n/).filter(line => line.length > 0);
  if (lines.length < 2) throw new Error("forecast.csv has no data rows.");

  const header = lines[0].split(",");
  const col = {};
  for (const name of REQUIRED_COLUMNS) {
    col[name] = header.indexOf(name);
    if (col[name] < 0) throw new Error(`forecast.csv is missing the "${name}" column.`);
  }

  const nRows = lines.length - 1;
  const rowCell = new Int32Array(nRows);
  const rowDate = new Array(nRows);
  const rowPct = new Float64Array(nRows);
  const rowProb = new Float64Array(nRows);
  const rowActual = new Uint8Array(nRows);

  const cellPosition = new Map();   // cell_id -> position in `cells`
  const cells = [];                 // [{ id, lat, lon }]

  for (let r = 0; r < nRows; r++) {
    const f = lines[r + 1].split(",");
    const id = Number(f[col.cell_id]);
    if (!cellPosition.has(id)) {
      cellPosition.set(id, cells.length);
      cells.push({ id, lat: Number(f[col.lat]), lon: Number(f[col.lon]) });
    }
    rowCell[r] = cellPosition.get(id);
    rowDate[r] = f[col.date];
    rowPct[r] = Number(f[col.risk_percentile]);
    rowProb[r] = Number(f[col.probability]);
    rowActual[r] = Number(f[col.actual]) === 1 ? 1 : 0;
  }

  for (const c of cells) {
    if (![c.id, c.lat, c.lon].every(Number.isFinite)) {
      throw new Error("forecast.csv has a cell with a non-numeric id, lat or lon.");
    }
  }

  const dates = [...new Set(rowDate)].sort();
  for (const d of dates) {
    if (!DATE_PATTERN.test(d)) throw new Error(`Unexpected date value "${d}" in forecast.csv.`);
  }
  const dayPosition = new Map(dates.map((d, i) => [d, i]));

  const nDays = dates.length;
  const nCells = cells.length;
  const pct = new Float64Array(nDays * nCells).fill(NaN);
  const prob = new Float64Array(nDays * nCells).fill(NaN);
  const actual = new Uint8Array(nDays * nCells);

  for (let r = 0; r < nRows; r++) {
    const k = dayPosition.get(rowDate[r]) * nCells + rowCell[r];
    pct[k] = rowPct[r];
    prob[k] = rowProb[r];
    actual[k] = rowActual[r];
  }

  return { dates, cells, nDays, nCells, pct, prob, actual };
}


// ---------------------------------------------------------------------------
// Numbers behind the cards
// ---------------------------------------------------------------------------

/** Percentile cut-off for "top X% of cells", e.g. 0.05 -> 0.95. */
function topThreshold(topFraction) {
  return Math.round((1 - topFraction) * 1e9) / 1e9;
}

/** How many real fire starts landed in the top `topFraction` of cells that day. */
function computeCapture(data, topFraction) {
  const threshold = topThreshold(topFraction);
  let fires = 0;
  let caught = 0;
  for (let k = 0; k < data.actual.length; k++) {
    if (data.actual[k] !== 1) continue;
    fires++;
    if (data.pct[k] >= threshold) caught++;
  }
  return { fires, caught };
}

/** Positions of the cells in the top `topFraction` on one day. */
function topCellsOnDay(data, day, topFraction) {
  const threshold = topThreshold(topFraction);
  const base = day * data.nCells;
  const out = [];
  for (let i = 0; i < data.nCells; i++) {
    if (data.pct[base + i] >= threshold) out.push(i);
  }
  return out;
}

/** Positions of the cells where a fire started on one day. */
function fireCellsOnDay(data, day) {
  const base = day * data.nCells;
  const out = [];
  for (let i = 0; i < data.nCells; i++) {
    if (data.actual[base + i] === 1) out.push(i);
  }
  return out;
}

/** Number of days a cell was in the top `topFraction`. */
function countTopDays(data, cell, topFraction) {
  const threshold = topThreshold(topFraction);
  let n = 0;
  for (let day = 0; day < data.nDays; day++) {
    if (data.pct[day * data.nCells + cell] >= threshold) n++;
  }
  return n;
}

/** Days (as positions) on which a fire started in this cell. */
function fireDaysForCell(data, cell) {
  const out = [];
  for (let day = 0; day < data.nDays; day++) {
    if (data.actual[day * data.nCells + cell] === 1) out.push(day);
  }
  return out;
}

/** First day that has at least one fire start, or 0 if there are none. */
function firstDayWithFire(data) {
  for (let day = 0; day < data.nDays; day++) {
    if (fireCellsOnDay(data, day).length > 0) return day;
  }
  return 0;
}


// ---------------------------------------------------------------------------
// Grid and colour
// ---------------------------------------------------------------------------

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function steps(values) {
  const unique = [...new Set(values)].sort((a, b) => a - b);
  return unique.slice(1).map((v, i) => v - unique[i]);
}

/** Cell height and width in degrees, read from the spacing of the cell centres. */
function gridStep(cells) {
  return {
    dLat: median(steps(cells.map(c => c.lat))),
    dLon: median(steps(cells.map(c => c.lon))),
  };
}

/** Map a risk percentile (0 to 1) onto the colour ramp. */
function riskColour(p) {
  if (!Number.isFinite(p)) return MISSING_COLOUR;
  const x = Math.min(1, Math.max(0, p)) * (RISK_RGB.length - 1);
  const i = Math.min(RISK_RGB.length - 2, Math.floor(x));
  const t = x - i;
  const [r, g, b] = RISK_RGB[i].map((lo, k) => Math.round(lo + (RISK_RGB[i + 1][k] - lo) * t));
  return `rgb(${r},${g},${b})`;
}


// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

/** 0.9847 -> "1.5" (meaning "top 1.5%"); 0.6 -> "40". */
function formatTopPercent(p) {
  const v = Math.max(0.1, (1 - p) * 100);
  return v < 10 ? v.toFixed(1) : String(Math.round(v));
}

/** 0.000845 -> "0.085%". */
function formatProbability(p) {
  return `${(p * 100).toPrecision(2)}%`;
}

const DATE_STYLES = {
  long: { weekday: "short", day: "numeric", month: "short", year: "numeric" },   // Thu, 12 Dec 2024
  medium: { day: "numeric", month: "short", year: "numeric" },                    // 12 Dec 2024
  short: { day: "numeric", month: "short" },                                      // 12 Dec
};

/** "2024-12-12" -> "Thu, 12 Dec 2024" (always read as a calendar date, no time zone shift). */
function formatDate(isoDate, style = "long") {
  return new Date(`${isoDate}T00:00:00Z`)
    .toLocaleDateString("en-AU", { ...DATE_STYLES[style], timeZone: "UTC" });
}

/** Where each month starts along the slider: [{ label: "Dec", index: 0 }, ...]. */
function monthTicks(dates) {
  const ticks = [];
  let lastMonth = "";
  dates.forEach((d, index) => {
    const month = d.slice(0, 7);
    if (month === lastMonth) return;
    lastMonth = month;
    const label = new Date(`${d}T00:00:00Z`).toLocaleDateString("en-AU", { month: "short", timeZone: "UTC" });
    ticks.push({ label, index });
  });
  return ticks;
}


if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    parseForecast, topThreshold, computeCapture, topCellsOnDay, fireCellsOnDay,
    countTopDays, fireDaysForCell, firstDayWithFire, gridStep, riskColour,
    formatTopPercent, formatProbability, formatDate, monthTicks, RISK_STOPS,
  };
}
