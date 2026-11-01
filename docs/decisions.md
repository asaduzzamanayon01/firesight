# Decision log

Every non-obvious choice, with the reasoning. When a marker asks "why did you
do it that way?", the answer is here rather than in someone's memory.

Format: what we decided, why, what we rejected, and who owns it.

---

## D1. Label = first detection per fire event, not every detection
**Owner:** Ayon · **Date:** 2026-09-03 · **Status:** Accepted

FIRMS returns one row per satellite *detection*. A fire burning three days
across six cells generates dozens of rows.

**Decision.** Cluster detections with DBSCAN over (x, y, t) and keep only the
earliest detection per cluster as the ignition label.

**Why.** Labelling every detection would train the model on fire *spread*.
The research question is where fires *start*. Without this step the positive
rate inflates roughly tenfold and the model learns the wrong thing.

**Rejected.** Using all detections (wrong target); using official incident
reports (not openly available for the full period).

---

## D2. PR-AUC and Brier as primary metrics; accuracy banned
**Owner:** Ayon · **Date:** 2026-09-03 · **Status:** Accepted

Positive rate is ~0.3%, so the negative class dominates.

**Decision.** Report PR-AUC (discrimination) and Brier score plus reliability
curves (calibration). ROC-AUC is reported only for comparability with
published work. Accuracy is never reported.

**Why.** A model predicting "no fire" everywhere scores 99.7% accuracy and
catches nothing. PR-AUC has no true-negative term so it cannot be flattered by
the majority class. Its random baseline is the positive rate itself (~0.003),
not 0.5. Encoded as an executable assertion in `tests/test_metrics.py::test_accuracy_trap`.

---

## D3. Leave-one-season-out, not random k-fold
**Owner:** Ayon, with Saad · **Date:** 2026-09-03 · **Status:** Accepted

**Decision.** Hold out entire fire seasons. Additionally report a spatial
block holdout.

**Why.** Two leakage paths. Temporally, adjacent days share weather systems,
so a random split effectively shows the model its test conditions. Spatially,
neighbouring 3 km cells share the same ~9 km ERA5 weather pixel. LOSO also
mirrors the real deployment question: trained on history, how does it do next
summer?

**Also available.** `forward_chaining()` trains only on *earlier* seasons,
which is stricter still. Use it if a marker challenges LOSO as optimistic.

---

## D4. Gradient boosting is the starting point, not the committed model
**Owner:** Ayon · **Date:** 2026-09-13 · **Status:** Accepted
**Supersedes:** an earlier draft that named LightGBM as the committed model.

**Decision.** Evaluate logistic regression, random forest, gradient boosting
and (conditionally) ConvLSTM through one shared harness. The highest held-out
PR-AUC wins. See `src/models/compare_models.py`.

**Why.** Committing to an algorithm before seeing results is not defensible.
Gradient boosting is *first* because it trains in minutes rather than hours,
accepts a class-weighting term, and gives exact SHAP values. Those are reasons
to start there, not reasons to stop there.

**Evidence.** On synthetic data generated from a logistic process, logistic
regression wins the comparison. That is a feature: it shows the harness is not
rigged toward the model we happened to write first.

---

## D5. Isotonic calibration fitted on out-of-fold predictions
**Owner:** Ayon · **Date:** 2026-09-13 · **Status:** Accepted

**Decision.** Fit isotonic regression on out-of-fold predictions only.

**Why.** `scale_pos_weight` fixes ranking but destroys probability meaning.
Measured on synthetic data: raw Brier 0.369 (Brier skill **-108**), after
isotonic 0.0034 (skill +0.004). PR-AUC changed by -0.0001, because isotonic
is monotonic and therefore preserves ranking exactly. Fitting on in-sample
predictions gives a calibrator that is itself overfitted.

**Use this in Q&A.** "Doesn't calibration hurt PR-AUC?" — no, and we measured
it.

---

## D6. MLflow on SQLite, not the file store
**Owner:** Ayon · **Date:** 2026-09-13 · **Status:** Accepted

**Decision.** `sqlite:///mlflow.db`, overridable via `MLFLOW_TRACKING_URI`.

**Why.** MLflow 3.x refuses the `./mlruns` file store. SQLite also fails on
network drives ("disk I/O error"), hence the environment override.

---

## D7. Synthetic data generator for development
**Owner:** Ayon · **Date:** 2026-09-13 · **Status:** Accepted

**Decision.** `scripts/make_synthetic.py` produces a cell-day table with the
real schema and a ~0.3% positive rate, from a *known* generating process.

**Why.** Unblocks the modelling and CI work before the real downloads land.
Because the true relationship is known, it doubles as a correctness check: the
pipeline must recover the features that were planted. It does — SHAP ranks
temperature, humidity and powerline distance highest.

**Rule.** Never report synthetic results as real. Label every figure.

---

## D8. Spatial and recent-activity features on real data
**Owner:** Ayon · **Status:** Accepted

On real data LightGBM trained on weather and season alone scored PR-AUC 0.0021,
below the climatology baseline (0.0043). The weather lattice is about 20 km wide,
so neighbouring 3 km cells receive almost the same weather and the model cannot
tell them apart, whereas the baseline knows which cells burn.

**Decision.** Add cell location, ignitions in the last 1 and 7 days nearby and in
the region, and historical ignition rates of the cell and its neighbours
(`src/features/spatial_priors.py`).

**Leakage rules.** Recent activity uses only earlier days of the same season
(shifted one day). Historical rates use training seasons only; a training row's
rate comes from the other training seasons, and a test row's from all training
seasons. `tests/test_spatial_priors.py` checks each rule.

**Result.** PR-AUC 0.0102 against 0.0043 for the baseline, better in 6 of 6
seasons. The top 5% of cells per day contain 32% of ignitions (random: 5%).
Skill falls in later seasons (PR-AUC 0.0227 in 2019-20, 0.0038 in 2024-25).

---

## D9. Remove permanent heat-source cells
**Owner:** Ayon · **Status:** Accepted

Two cells (570 and 571) had 99 and 39 ignition days, far above any other cell.
They are persistent heat sources, not repeated ignitions.

**Decision.** Exclude cells with 35 or more ignition days from the cell-day table
(`drop_static_sources`, tested in `tests/test_static_sources.py`). The excluded
cells are written to `data/processed/static_cells.csv` and `results_real/static_cells.csv`.

**Why.** They would dominate the positive class and let the model look good by
memorising two locations.
