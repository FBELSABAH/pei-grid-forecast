# Statistical revision audit - 16 November 2026

## What changed and why

1. **Causal raw-data cleaning.** Whole-run duration previously used a future endpoint to reject earlier equal readings. The new quality rule uses elapsed duration at each reading and resets when a gap exceeds 30 minutes. It never backdates flags. This fixes a real general leakage path, not evidence that the original 2025/26 result was inflated: all original scored predictions are unchanged in the frozen snapshot. Synthetic future mutation tests would fail under the old rule.
2. **Matched linear comparison.** The fixed original ridge-weather candidate (alpha=100) is refit using the original boosting's quarterly training windows and features. All methods score exactly the same target rows. Training-only scaling avoids using evaluation information. Ridge is a regularized linear benchmark; no ordinary least-squares inference or coefficient p-values are claimed.
3. **Winter experiment.** Before fitting the revision, protocol v2 specified monthly refits, recent-label training and trailing-365-day signed prequential-error intervals. The original 2025/26 results had already been inspected. This is an exploratory retrospective improvement, not a new holdout or third-party preregistration. Only one revised policy was tried; no test-year hyperparameter search. Parameters are in protocol.json.
4. **Missingness and dependence.** Monthly eligibility denominators include blocked origins, not only surviving rows. Missing causes overlap. Lag correlations are aligned by calendar hour; 7/14/28-day block sensitivity is reported for the unweighted mean of daily MAE gains, not the percentage hourly metric.

## Why winter might suffer

The original method reserves 180 recent days for calibration, leaving point fitting slow to learn recent load levels. Monthly refits can reduce this staleness. Signed past forecast errors can represent asymmetry in observed underprediction. These are plausible motivations, not established causes: this experiment changes frequency, recency and interval construction together. It cannot separate their individual contributions. Past-model residuals may mismatch a new model, especially during drift.

## Results, including unfavourable ones

| Metric | Original | Monthly revision |
|---|---:|---:|
| 2025 MAE, MW | 11.98 | 11.49 |
| 2025 90%-nominal coverage | 86.9% | 89.6% |
| 2025 mean interval width, MW | 50.45 | 48.65 |
| Jan-Mar 2025 MAE, MW | 16.85 | 15.76 |
| Jan-Mar 2025 interval coverage | 68.1% | 80.9% |
| Jan-Mar 2025 interval width, MW | 43.51 | 47.75 |
| Jan-Mar 2025 interval score, MW (lower better) | 101.88 | 81.14 |
| Jan-Mar 2026 MAE, MW | 16.09 | 15.94 |
| Jan-Mar 2026 RMSE, MW | 20.22 | 20.47 |
| Jan-Mar 2026 high-load recall | 74.5% | 73.3% |

Winter calibration is improved but still inadequate. Wider winter intervals contribute to improved coverage; annual intervals are narrower on average, and the proper interval score improves in winter. Retain both coverage and width/score rather than treating wider intervals as free improvement. Statistical peak thresholds remain the original quarterly training percentiles to keep alert comparisons paired.

February 2025 eligibility is 377/672 hours (56.1%); it cannot be repaired merely by filling missing targets. Performance during these omitted periods is unknown. No claim of improved data coverage is made.

## Reproduce and inspect

`python run.py` uses the frozen cached source, rebuilds both methods and all comparisons. `python make_brief.py` creates the one-page PDF. `pytest -q` checks raw-prefix invariance, gap handling, calibration chronology, paired artifacts and numerical outputs; `node tests/check_ui.cjs` checks dashboard integration. Source hashes, protocol hash and both prediction hashes are in reports/run_manifest.json. See reports/repeatability.json for two-run verification. Rebuilding from a newer live source is a different snapshot, not a reproduction of these exact numbers.

Exact original/revised results, all months, predictions and cutoffs are retained in reports/results.json, winter_revision.json, backtest_predictions.csv, revision_predictions.csv and revision_folds.csv. Original v1 artifacts are archived under reports/original_v1/. The browser's day-level profile remains the original method, with the revision separately labeled in Results.

## Verification outcome

27 Python tests passed, including raw-prefix invariance and monthly/annual denominator reconciliation. Two full cached v2 rebuilds match byte-for-byte on features, original/revised predictions, results and eligibility; original v1 predictions differ by exactly 0 MW. The updated Results and Data & Method views and HTML brief were inspected in Chrome at desktop width. The one-page PDF was rendered and visually inspected. Mobile layout and full accessibility were not audited.

## Remaining limits

No historical publication vintages, verified island-wide weather or settlement-grade load; timezone and one-hour latency assumptions; source changes; dependence; selected eligible hours; only one retrospective data history. No causal attribution, external validation, guaranteed future accuracy, savings or utility endorsement. Next step is professor/practitioner critique and prospectively logged forecasts, not further fishing in the already-inspected test years.

## Method references

- Scikit-learn, lagged-feature forecasting example (chronological evaluation): https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html
- Forecasting: Principles and Practice, forecasting toolbox (accuracy, residuals and time-series validation): https://otexts.com/fpp3/toolbox.html
- Open-Meteo previous-runs documentation (fixed-lead forecast source): https://open-meteo.com/en/docs/previous-runs-api
