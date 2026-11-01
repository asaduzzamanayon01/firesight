# FireSight dashboard (FS-47)

A map page that replays the FireSight **backtest** for 1 Dec 2024 to 28 Feb 2025. Drag the date slider to see each cell's risk percentile for that day, with red dots where a fire really started. It is a backtest, not a live forecast.

## Run it

From the repo root:

```bash
cd dashboard
python3 -m http.server 8000
```

Then open http://localhost:8000 in a browser.

Opening `index.html` by double-clicking will not work, because browsers block a page from reading `data/forecast.csv` that way. You also need an internet connection for the map tiles and the Leaflet library.

## What is in this folder

| File | What it does |
|---|---|
| `index.html` | Page layout |
| `style.css` | Styling |
| `forecast.js` | Reads `forecast.csv` and works out the numbers (no map code) |
| `app.js` | Map, slider and side panel |
| `data/forecast.csv` | Forecast file: `cell_id, lat, lon, date, probability, actual, season, risk_percentile` |

## Things to know

- Cells are coloured by `risk_percentile` (0 to 1, rank within each day), not `probability`.
- "Top 5%" means `risk_percentile >= 0.95`.
- The "this summer window" number is counted from `forecast.csv` when the page loads. The "six seasons" number (32%) is typed into `app.js` as `SIX_SEASON_CAPTURE`, because it comes from the model evaluation and cannot be worked out from this file.
- The example cell is set by `EXAMPLE_CELL` at the top of `app.js`.
- To show a different forecast, replace `data/forecast.csv` with a file that has the same columns.
