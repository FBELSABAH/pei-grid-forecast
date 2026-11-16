# PEI Grid Forecast - professor review brief

**Faris Elsabah | Independent educational research | Revised 16 November 2026 | Frozen source through 2026-11-13 07:44:00 Atlantic wall time**

## Research question
At 18:00 Atlantic, predict the following local day's hourly mean sampled PEI load using historical load, calendar information and archived fixed-48h GFS temperature forecasts. This is a forecasting/regression study, not causal inference or a utility operating tool.

## Fair benchmark comparison
All methods use the same 8,400 eligible 2025 hours (95.89% of the year). Fixed candidate selection used January-June 2024. The original quarterly method remains the reference; the new monthly method is an exploratory retrospective revision after the original test results were inspected.

| Method | 2025 MAE (MW) | RMSE (MW) |
|---|---:|---:|
| Original quarterly gradient boosting | 11.98 | 15.89 |
| Ridge linear regression, alpha=100 | 13.50 | 17.68 |
| Mean of two-/seven-day profiles | 18.18 | 24.48 |
| Two-day naive | 20.57 | 27.60 |
| Weekly naive | 21.84 | 29.88 |
| Monthly boosting revision (exploratory) | 11.49 | 15.37 |

Ridge is a regularized linear benchmark, with training-only scaling and the same features, quarterly training windows and target hours as the original boosting method. It is not ordinary least squares or an inferential coefficient analysis. Original boosting has 11.2% lower MAE than ridge and 34.1% lower than the strongest simple baseline.

## Winter investigation: improved, not solved
The original model left the most recent 180 days out of point-model fitting to reserve a calibration window. The revision refits monthly using recent available labels; intervals use signed errors from earlier monthly forecasts, restricted to the prior 365 days. This jointly changes refit frequency, training recency and calibration, so the comparison cannot isolate their individual effects.

January-March 2025: MAE 16.85 -> 15.76 MW; nominal-90% interval coverage 68.1% -> 80.9%; mean width 43.51 -> 47.75 MW; interval score 101.88 -> 81.14 MW (lower is better). Annual revised coverage is 89.6% versus 86.9%, with narrower average width (48.65 versus 50.45 MW). Winter undercoverage remains; do not claim calibration is fixed. In the 2026 January-March extension, revised MAE improves slightly but RMSE and high-load recall worsen; all monthly results are retained.

## Corrections and uncertainty
A raw-data flatline rule previously used a run's future end to reject earlier readings. It now flags a reading only after four hours of observed repetition, resets across gaps over 30 minutes, and never backdates rejection. An end-to-end raw-future-mutation test verifies input-prefix invariance. Correcting this defect did not change the original 2025/26 scored predictions in this snapshot. The first four hours of a freeze remain undetectable by this rule.

February 2025 has only 377/672 hours (56.1%) eligible. Excluded periods are not imputed or represented by these scores. Error autocorrelation at lag 1 is 0.924; hours are not independent trials. Seven-, 14- and 28-day block bootstrap sensitivity is reported for unweighted daily MAE gains, not the hourly percentage improvement. No naive regression p-values are reported.

## Review request and next step
Review the linear benchmark's specification, temporal validation and treatment of seasonal uncertainty/missingness. The revision is a candidate for future validation, not evidence from a newly untouched holdout. Record forecasts before outcomes arrive before making operational claims. Historical publication vintages and timezone are not fully verified; one-hour load latency is assumed; Charlottetown weather is a single-point proxy. No measured savings, deployment, endorsement or causal attribution is claimed.

## Sources and reproducibility
Electricity: Peter Rukavina / Reinvented, https://energy.reinvented.net/ (provincial indicators). Weather: Open-Meteo GFS, https://open-meteo.com/en/docs/previous-runs-api (CC BY 4.0; API terms separate). Raw snapshots remain out of Git. Protocol v2, archived v1, every prediction, monthly eligibility, revision fold cutoffs and source/output hashes accompany the repository: https://github.com/FBELSABAH/pei-grid-forecast.
