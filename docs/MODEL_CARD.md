# Model card - audited revision, 16 November 2026

**Purpose:** independent educational forecasting/regression study of PEI load. Not utility control, causal inference or a promise of savings.

**Target and timing:** next local day's hourly mean of accepted instantaneous PEI on-island load readings (MW), issued at 18:00 Atlantic the preceding day. Roughly 6-30 hour horizons; DST days have 23/25 elapsed hours. Source intervals end at least one hour before issue. Actual electricity publication vintages are unavailable, so latency and historical timezone remain assumptions. Archived forecast weather is GFS fixed-48h temperature at Charlottetown, not realized future weather or exact latest weather-run reconstruction.

**Inputs:** load lags 48/168 elapsed hours; recent historical level/range; calendar cycles; temperature/heating/cooling variables and interaction. No target interpolation. Missing lag, target, weather or insufficient history blocks scoring. Full-year 2025 coverage is 95.89%, but February only 56.1%; excluded periods are not represented.

**Selection/reference:** four fixed candidates selected on January-June 2024 only. Original winner: HistGradientBoostingRegressor, 31 leaves, 220 iterations, learning rate .065, leaf size 40, L2 10, seed 2027, no random early-stopping split. Original quarterly fits use up to three years before a separate trailing 180-day calibration set. Fixed ridge alpha=100 uses identical features/train windows and training-only scaling; no inferential coefficient claims.

**Reference results:** 2025 original MAE 11.98 MW, ridge 13.50, strongest simple baseline 18.18. Bias -5.26 MW; high-load recall 68.0%; nominal-90% interval coverage 86.9%. January-March coverage only 68.1%. Original scored outputs are unchanged by the corrected causal filter in this snapshot.

**Exploratory monthly revision:** same boosting configuration, monthly refits on recent available labels. Trailing 365-day earlier monthly out-of-sample signed errors supply asymmetric empirical 5th/95th limits. Calibration warmup begins 2023; evaluation 2025 onward. Earlier labels are used only when hour end <= issue minus one hour. Several design changes are combined; no causal attribution to an individual change. No new 2025/26 hyperparameter search. 2025/26 were already inspected, so this is not a new untouched holdout.

**Revision results:** 2025 MAE 11.49 MW; interval coverage 89.6%, mean width 48.65 MW vs original 50.45. January-March MAE 15.76 vs 16.85; coverage 80.9% vs 68.1%, width 47.75 vs 43.51. Winter remains undercovered. January-March 2026 has slightly lower MAE but worse RMSE and high-load recall. See all folds rather than selecting favourable months. Empirical time-series interval coverage is not guaranteed.

**Audit fix:** flatline quality labels are now causal: flag after four hours of already-observed repetition, reset after gaps >30 minutes, never reject earlier readings from a future endpoint. First four hours can remain stale; genuine flat signals can still be flagged. A raw-future-mutation test verifies completed hourly inputs and next-day features.

**Uncertainty:** errors are serially dependent (lag-1 .924). Block bootstrap estimates unweighted daily MAE gain conditional on these data/models, not an interval for hourly percentage improvement. Seven-, 14- and 28-day block sensitivities retained. No independent-hour standard errors, naive p-values or causal coefficients.

**Before use:** have a practitioner confirm load definitions, latency, licensing and relevant operational baseline; record forecasts before outcomes arrive. Secure input vintages and assess extremes/omitted periods. No stakeholder validation or endorsement has occurred. Simulator flexibility is assumed; no real load is controlled. The current browser forecast view uses the original quarterly reference; monthly revision results are separate.
