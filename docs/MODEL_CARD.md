# Model card

**Purpose:** independent educational forecasting study, supporting discussion with PEI energy/software practitioners. Not a utility operating tool.

**Target:** hourly mean accepted instantaneous on-island load (MW), using public provincial readings archived by Reinvented. No claim of settlement-grade energy measurement.

**Issue:** preceding local date at 18:00 Atlantic. Horizon varies with target hour and DST (roughly 6-30 hours). Buffered source intervals end by 17:00. Actual historical publication times were not recorded.

**Inputs:** calendar cyclic features; 48-/168-hour elapsed load lags; pre-cutoff recent load level/range; archived GFS 48-hour-lead temperature, derived heating/cooling degrees and hour interaction. No future observed weather or future target load as inputs. Forecast-weather metadata are lead-time proxies, not exact run/vintage reconstruction.

**Selection:** four fixed candidates evaluated January-June 2024. Winner: histogram gradient boosting, 31 leaves, 220 iterations, 0.065 learning rate, minimum leaf size 40, L2 10, seed 2027, random early-stopping validation disabled. Selected on validation MAE only. Normalization/imputation for the ridge comparison are fit on its training set only.

**Refits:** quarterly; up to three years of training followed by a separate trailing 180-day calibration window. See reports/folds.csv for actual cutoffs and sample counts. Separate nominal-90% residual intervals; test coverage is reported rather than assumed.

**Findings:** 2025 MAE 11.98 MW vs 18.18 MW strongest simple baseline (34.1% reduction). 2026 extension MAE 11.81 MW. Primary bias -5.26 MW; 90% nominal intervals achieve 86.9% empirical coverage; peak recall 68.0%. Report all folds, including winter deterioration, instead of selecting favourable weeks.

**Limits:** selection conditioned on acceptable data and available weather/lags; current timezone evidence does not establish historical clock settings; possible source revisions and unknown publication latency; one weather location; grid/population/electrification drift; statistical alert thresholds are not grid capacities; no savings or external validation. The scenario tool assumes flexible capacity, constant elapsed-hour durations and lossless shifting, with no device/network constraints.

**Before operational use:** obtain source-definition and latency confirmation, secure appropriate data/API rights, log forecasts prospectively, test against a practitioner's actual baseline, review extreme weather/outages and calibrate intervals under new conditions. Keep human review for any consequential decision.
