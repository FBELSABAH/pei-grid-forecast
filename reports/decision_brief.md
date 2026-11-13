# PEI Grid Forecast - decision brief

**Independent educational research | Faris Elsabah | Snapshot: 2026-11-13 07:44:00 Atlantic source wall time**

## Decision and recommendation

The model is a promising candidate for a small, prospectively logged forecasting pilot. It is not ready to control electricity equipment or support cost-saving claims. Start by having a utility or energy-software practitioner review the target definition, data latency and failure periods.

## What was measured

At 18:00 Atlantic, predict the following local day's hourly mean sampled on-island load. The electricity archive contains 508,848 observations from November 2012 onward. Feature development starts in 2021 to match the weather archive. Select among four candidates using January-June 2024 only; calibrate uncertainty on separate earlier observations; refit quarterly without tuning on the 2025-26 test.

## Main result: locked 2025 test

- 8,400 identical scored hours across all methods: 95.9% of the calendar year.
- Model MAE: **11.98 MW**, versus **18.18 MW** for the strongest simple baseline (mean of two- and seven-day profiles): **34.1% lower error**.
- Weekly-naive MAE: 21.84 MW. RMSE: 15.89 MW. Weighted absolute percentage error: 5.81%. Bias: -5.26 MW (underprediction).
- Nominal 90% intervals covered **86.9%**, below their nominal target.
- High-load precision: 94.4%; recall: 68.0%. Thresholds use training-load percentiles, not utility capacity.
- Separate 2026 extension: 6,765 hours, **11.81 MW MAE**; 89.2% calendar coverage.

## Where to investigate

Inspect underprediction, interval undercoverage, high-load misses and the largest-error days before a pilot. Compare prospective performance with the same baselines. Ask a practitioner whether the chosen issue time and province-wide signal match an actual planning decision. The load-shifting tool illustrates energy-conserving scenarios only; flexible capacity is assumed.

## What the data cannot establish

The archive is community-maintained, not settlement-meter data. Source wall time is assumed historically Atlantic; the current Unix timestamp supports this but does not prove every historical timestamp. We quarantine ambiguous DST observations, nonpositive values and four-hour flat runs; require three samples spanning 30 minutes per hour; never interpolate targets. Electricity release vintages are unavailable, so the assumed one-hour latency buffer cannot establish historical publication availability. Weather uses older fixed-48h GFS forecasts, not future observed weather or exact latest issue runs. No stakeholder adoption, actual savings, emissions reduction, operating-limit prediction or utility endorsement has been demonstrated.

## Sources and reproducibility

- Peter Rukavina / Reinvented electricity archive: https://energy.reinvented.net/
- Government of PEI indicator definitions: https://www.princeedwardisland.ca/en/feature/renewable-energy-indicators
- Open-Meteo GFS forecast archive: https://open-meteo.com/en/docs/previous-runs-api (weather data CC BY 4.0; API terms apply separately).
- See protocol.json, reports/results.json, reports/backtest_predictions.csv and reports/run_manifest.json for exact methods, all predictions and fingerprints. Raw source snapshots are not redistributed in Git; electricity archive reuse terms were not explicitly stated on the source landing page.
