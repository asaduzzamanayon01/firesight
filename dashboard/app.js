"use strict";

// FireSight backtest dashboard: wires the forecast data to the map and controls.
// Data logic lives in forecast.js.

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const DATA_URL = "data/forecast.csv";
const TOP_FRACTION = 0.05; // "top 5% of cells each day"
const SIX_SEASON_CAPTURE = 0.32; // supplied by the team lead (model evaluation); not derivable from forecast.csv
const EXAMPLE_CELL = 679; // cell used for the worked example
const EXAMPLE_TOP_FRACTION = 0.02; // "top 2%"
const PLAY_INTERVAL_MS = 400;

const COLOURS = { fire: "#e11d1d", outline: "#111827", highlight: "#06b6d4" };

const $ = (id) => document.getElementById(id);
const percentText = (fraction) => String(Math.round(fraction * 100));

const state = { data: null, day: 0, timer: null, exampleOn: false };

let map;
let cellLayer, outlineLayer, fireLayer, highlightLayer;
let rects = []; // one Leaflet rectangle per cell
let cellBounds = []; // [[south, west], [north, east]] per cell
let exampleCell = -1; // position of EXAMPLE_CELL in data.cells, or -1 if it is not in the file

// ---------------------------------------------------------------------------
// Start-up
// ---------------------------------------------------------------------------

async function init() {
    if (typeof L === "undefined") {
        showProblem(
            "The map library could not be loaded. Check your internet connection and reload.",
        );
        return;
    }
    buildMap();

    let text;
    try {
        const response = await fetch(DATA_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        text = await response.text();
    } catch (err) {
        showProblem(
            `Could not load ${DATA_URL} (${err.message}). Serve this folder with ` +
                `"python3 -m http.server 8000" instead of opening index.html directly. See README.md.`,
        );
        $("date-label").textContent = "";
        return;
    }

    try {
        state.data = parseForecast(text);
    } catch (err) {
        showProblem(err.message);
        $("date-label").textContent = "";
        return;
    }

    buildCells();
    fillStaticText();
    buildLegend();
    buildTicks();
    buildExample();
    wireControls();

    $("slider").max = state.data.nDays - 1;
    $("slider").disabled = false;
    setDay(firstDayWithFire(state.data));
}

function showProblem(message) {
    const box = $("problem");
    box.textContent = message;
    box.hidden = false;
}

// ---------------------------------------------------------------------------
// Map
// ---------------------------------------------------------------------------

function buildMap() {
    map = L.map("map", { preferCanvas: true, zoomSnap: 0.25 });
    map.setView([-32.0, 116.0], 9); // replaced by fitBounds once the data is loaded

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);
}

/** One rectangle per cell, sized from the spacing of the cell centres. */
function buildCells() {
    const { dLat, dLon } = gridStep(state.data.cells);

    cellLayer = L.layerGroup();
    state.data.cells.forEach((cell, i) => {
        const bounds = [
            [cell.lat - dLat / 2, cell.lon - dLon / 2],
            [cell.lat + dLat / 2, cell.lon + dLon / 2],
        ];
        cellBounds.push(bounds);

        const rect = L.rectangle(bounds, { stroke: false, fillOpacity: 0.8 });
        rect.bindTooltip(() => cellTooltip(i), { sticky: true });
        rect.addTo(cellLayer);
        rects.push(rect);
    });
    cellLayer.addTo(map);

    // Everything shares one canvas, drawn in the order it is added: cells, then
    // outlines, then the example highlight, then fire dots. (Separate map panes
    // would each get their own canvas, and only the top canvas receives hover.)
    // setDay() redraws these in that order every time.
    outlineLayer = L.layerGroup().addTo(map);
    fireLayer = L.layerGroup().addTo(map);
    highlightLayer = L.layerGroup().addTo(map);

    map.fitBounds(L.latLngBounds(cellBounds.flat()), { padding: [12, 12] });
}

function cellTooltip(i) {
    const d = state.data;
    const k = state.day * d.nCells + i;
    const id = d.cells[i].id;
    if (!Number.isFinite(d.pct[k])) return `Cell ${id}: no data for this day`;

    const fire =
        d.actual[k] === 1 ? "<br><strong>A fire started here</strong>" : "";
    return (
        `<strong>Cell ${id}</strong><br>` +
        `Risk percentile ${d.pct[k].toFixed(2)} (top ${formatTopPercent(d.pct[k])}%)<br>` +
        `Probability ${formatProbability(d.prob[k])}${fire}`
    );
}

// ---------------------------------------------------------------------------
// Drawing one day
// ---------------------------------------------------------------------------

function setDay(day) {
    const d = state.data;
    state.day = day;
    $("slider").value = day;
    $("date-label").textContent = formatDate(d.dates[day]);

    const base = day * d.nCells;
    for (let i = 0; i < d.nCells; i++) {
        rects[i].setStyle({ fillColor: riskColour(d.pct[base + i]) });
    }

    drawOutlines();
    drawHighlight();
    drawFires();
    updateDaySummary();
}

function drawOutlines() {
    outlineLayer.clearLayers();
    if (!$("toggle-outline").checked) return;

    for (const i of topCellsOnDay(state.data, state.day, TOP_FRACTION)) {
        L.rectangle(cellBounds[i], {
            fill: false,
            color: COLOURS.outline,
            weight: 1.5,
            interactive: false,
        }).addTo(outlineLayer);
    }
}

function drawFires() {
    fireLayer.clearLayers();
    const d = state.data;
    const base = state.day * d.nCells;

    for (const i of fireCellsOnDay(d, state.day)) {
        const cell = d.cells[i];
        L.circleMarker([cell.lat, cell.lon], {
            radius: 8,
            color: "#ffffff",
            weight: 2.5,
            fillColor: COLOURS.fire,
            fillOpacity: 1,
        })
            .bindTooltip(
                `<strong>Fire started</strong><br>Cell ${cell.id}, top ${formatTopPercent(d.pct[base + i])}% that day`,
                { sticky: true },
            )
            .addTo(fireLayer);
    }
}

function updateDaySummary() {
    const d = state.data;
    const base = state.day * d.nCells;
    const fires = fireCellsOnDay(d, state.day);
    const box = $("day-summary");
    box.replaceChildren();

    const summary = document.createElement("p");
    box.append(summary);

    if (fires.length === 0) {
        summary.textContent = "No fire starts recorded on this day.";
        return;
    }

    const threshold = topThreshold(TOP_FRACTION);
    const inTop = fires.filter((i) => d.pct[base + i] >= threshold).length;
    summary.textContent =
        `${fires.length} fire start${fires.length === 1 ? "" : "s"} recorded, ` +
        `${inTop} in the top ${percentText(TOP_FRACTION)}% of cells.`;

    const list = document.createElement("ul");
    for (const i of fires) {
        const item = document.createElement("li");
        item.textContent = `Cell ${d.cells[i].id}: ranked in the top ${formatTopPercent(d.pct[base + i])}% that day`;
        list.append(item);
    }
    box.append(list);
}

// ---------------------------------------------------------------------------
// Side panel
// ---------------------------------------------------------------------------

function fillStaticText() {
    const d = state.data;
    const first = d.dates[0];
    const last = d.dates[d.nDays - 1];
    const windowText = `${formatDate(first, "medium")} to ${formatDate(last, "medium")}`;

    $("subtitle").textContent =
        `Model predictions for ${windowText}, compared with fires that really started. ` +
        `Perth peri-urban interface, 3 km grid.`;

    $("top-pct").textContent = percentText(TOP_FRACTION);
    $("random-pct").textContent = percentText(TOP_FRACTION);
    $("outline-pct").textContent = percentText(TOP_FRACTION);
    $("stat-six").textContent = `${percentText(SIX_SEASON_CAPTURE)}%`;

    const { fires, caught } = computeCapture(d, TOP_FRACTION);
    $("stat-window-name").textContent =
        `This summer window (${formatDate(first, "short")} to ${formatDate(last, "short")})`;
    if (fires === 0) {
        $("stat-window").textContent = "-";
        $("stat-window-detail").textContent = "no fire starts in this file";
    } else {
        $("stat-window").textContent = `${percentText(caught / fires)}%`;
        $("stat-window-detail").textContent =
            `${caught} of ${fires} fire starts`;
    }
}

function buildLegend() {
    $("legend-bar").style.background =
        `linear-gradient(to right, ${RISK_STOPS.join(", ")})`;
}

function buildTicks() {
    const { dates } = state.data;
    const ticks = $("ticks");
    for (const { label, index } of monthTicks(dates)) {
        const tick = document.createElement("span");
        tick.className = "tick";
        tick.textContent = label;
        tick.style.left = `${(index / Math.max(1, dates.length - 1)) * 100}%`;
        ticks.append(tick);
    }
}

/** Worked example: one cell, the days a fire started there, and how often it ranked highly. */
function buildExample() {
    const d = state.data;
    exampleCell = d.cells.findIndex((c) => c.id === EXAMPLE_CELL);
    if (exampleCell < 0) return;

    const topDays = countTopDays(d, exampleCell, EXAMPLE_TOP_FRACTION);
    const fireDays = fireDaysForCell(d, exampleCell);

    $("example-cell").textContent = String(EXAMPLE_CELL);
    $("example-context").textContent =
        `Cell ${EXAMPLE_CELL} was in the top ${percentText(EXAMPLE_TOP_FRACTION)}% on ${topDays} of ${d.nDays} days. ` +
        (fireDays.length === 0
            ? "No fire started there in this window."
            : `A fire started there on ${fireDays.length} day${fireDays.length === 1 ? "" : "s"}:`);

    const buttons = $("example-buttons");
    for (const day of fireDays) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.textContent = formatDate(d.dates[day], "short");
        chip.addEventListener("click", () => showExample(day));
        buttons.append(chip);
    }

    $("example").hidden = false;
}

function showExample(day) {
    stopPlay();
    state.exampleOn = true;
    setDay(day);

    const centre = L.latLng(
        state.data.cells[exampleCell].lat,
        state.data.cells[exampleCell].lon,
    );
    if (!map.getBounds().contains(centre)) map.panTo(centre);
}

function clearExample() {
    state.exampleOn = false;
    setDay(state.day); // redraws in the right order
}

function drawHighlight() {
    highlightLayer.clearLayers();
    $("example-clear").hidden = !state.exampleOn;
    if (!state.exampleOn) return;

    // A ring around the cell. It is a circle bigger than the cell, because the red
    // fire dot would otherwise cover a ring drawn on the cell's own edge.
    const cell = state.data.cells[exampleCell];
    L.circleMarker([cell.lat, cell.lon], {
        radius: 17,
        fill: false,
        color: COLOURS.highlight,
        weight: 3.5,
        interactive: false,
    }).addTo(highlightLayer);
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------

function wireControls() {
    const last = () => state.data.nDays - 1;

    $("slider").addEventListener("input", (e) => {
        stopPlay();
        setDay(Number(e.target.value));
    });
    $("prev").addEventListener("click", () => {
        stopPlay();
        setDay(Math.max(0, state.day - 1));
    });
    $("next").addEventListener("click", () => {
        stopPlay();
        setDay(Math.min(last(), state.day + 1));
    });
    $("play").addEventListener("click", togglePlay);
    $("toggle-outline").addEventListener("change", () => setDay(state.day));
    $("example-clear").addEventListener("click", clearExample);
}

function togglePlay() {
    if (state.timer) {
        stopPlay();
        return;
    }
    const last = state.data.nDays - 1;
    if (state.day >= last) setDay(0);

    $("play").textContent = "Pause";
    state.timer = setInterval(() => {
        if (state.day >= last) {
            stopPlay();
            return;
        }
        setDay(state.day + 1);
    }, PLAY_INTERVAL_MS);
}

function stopPlay() {
    if (state.timer) clearInterval(state.timer);
    state.timer = null;
    $("play").textContent = "Play";
}

init();
