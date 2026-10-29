# FS-8 Validation protocol and evaluation plan

**Owner:** Saad · **Date:** 2026-10-29 · **Jira:** FS-8
**Related:** decisions D2, D3, D5 in `docs/decisions.md`; code in `src/evaluation/`

This is the rulebook for every number FireSight reports. If a result was not
produced this way, it does not go in the report or on a slide.

## 1. What we predict

For each 3 km cell (1,575 cells) and each day: the probability that a fire
**starts** there that day. Features use weather up to the day before, so the
model forecasts **one day ahead**. Do not claim 24 to 72 hours unless task A7
is delivered.

Positive rate is about 0.3% (1 fire cell-day in ~300).

## 2. How data is split

| Split | Code | Role |
|---|---|---|
| **Leave-one-season-out (LOSO)** | `leave_one_season_out()` | **Primary.** Each fire season (Jul to Jun) is held out once. 6 seasons, 2019-20 to 2024-25, so 6 folds |
| Forward chaining | `forward_chaining(min_train=3)` | Stricter check. Trains only on earlier seasons, so 3 folds (2022-23, 2023-24, 2024-25). Use if LOSO is challenged as optimistic |
| Spatial blocks | `spatial_block_split(n_blocks=5)` | Tests unseen geography |

Rules:
1. **No random splits.** Neighbouring days share weather and neighbouring cells
   share the same ~9 km ERA5 pixel, so a random split leaks.
2. **The test season is never touched during training.** Early stopping uses the
   latest *training* season (`inner_split`, tested in `test_leakage.py`).
3. **Calibration is fitted on out-of-fold predictions only** (D5).
4. Every model goes through the same harness and the same folds.

## 3. What we measure

| Metric | Question it answers | How to read it |
|---|---|---|
| **PR-AUC** (primary) | Can we rank risky cells? | Random = positive rate (~0.003), not 0.5. Always report the lift: PR-AUC ÷ positive rate |
| **Brier score** | Are the probabilities right? | Lower is better. Only compare models on the same data |
| **Brier skill score** | Better than always guessing the base rate? | 0 = no skill, above 0 = useful, below 0 = worse than guessing |
| **Reliability curve** (10 bins) | Does "20%" mean 20%? | Points on the diagonal = well calibrated |
| Precision@k / Recall@k | Of the top k flagged, how many burned? | Operational view for DFES |
| ROC-AUC | Comparison with published papers only | Looks high on imbalanced data; never the headline |
| ~~Accuracy~~ | Banned | "Never fire" scores 99.7% and catches nothing (D2) |

## 4. What counts as success

1. **Beat the climatology baseline** (`baseline_climatology.py`) on mean
   LOSO PR-AUC. Report the ratio, e.g. "1.75x baseline".
2. Beat the baseline in **most individual seasons**, not just on average.
   Report per-season scores, the mean and the standard deviation.
3. **Brier skill above 0 after calibration.** Raw weighted models can have
   negative skill (D5), so always report raw and calibrated.
4. Reliability curve close to the diagonal after calibration.
5. Forward-chaining scores in the same range as LOSO. A big drop means LOSO
   was flattered by training on future seasons.

## 5. How results must be reported

- Label every number **real** or **synthetic**. Synthetic results show the
  pipeline works; they say nothing about Perth fires.
- Re-run before quoting. No results files are saved in the repo.
- Report per season, not just the mean. Seasons with very few fires give noisy
  PR-AUC; say how many positives each season had.
- Name the baseline next to every model score.
- Say "one day ahead".

## 6. Known limits to state in the report

- **Label noise.** With the current 24-hour clustering window, a fire that
  spreads ~1 km a day can be counted as a new ignition each day (see
  `docs/fs7-grid-labels-leakage-check.md`). This inflates positives and mixes
  spread into the label until the window is widened.
- **Precision@k is pooled.** `train_lgbm.py` ranks all cell-days from all
  seasons together. A DFES planner ranks cells within one day, so a per-day
  top-k (e.g. top 20 cells each day, averaged) would be the fairer operational
  number. Suggested follow-up, not yet implemented.
- Satellites miss small or cloud-covered fires, so some true ignitions are
  labelled 0.
- No road or powerline features in the real data yet.
