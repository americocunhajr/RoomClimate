# RoomClimate v0.4.1

Research prototype for thermal and humidity dynamics, stationary sizing, uncertainty propagation and global sensitivity analysis. **Not a validated HVAC sizing tool.** Python 3.10+, NumPy >= 2.0 and SciPy >= 1.11. No Gaussian variables are introduced.

## New modules

- `sensitivity.py`: independent scrambled Sobol designs, inverse CDFs, Jansen first and total effects, replicate diagnostics, complete model evaluations.
- `historical.py`: fetch and cache hourly ERA5 weather from Open-Meteo; import continuous hourly CSV; sample complete summer days with preceding warmup days; common random numbers across equipment capacities. No synthetic fallback on download failure.
- `test_v041.py`: analytic additive sensitivity test, zero variance, design and support, mocked HTTP transport, continuous synthetic weather fixture, physical coupling, temporal refinement and missing-hour detection. `test_mc.py` remains from v0.4.

## Reproduce the actual pilot

```sh
pip install -r requirements.txt
python -m unittest test_mc test_v041
python sensitivity.py --m 5 --replicates 2 --seed 20261126 --capacity 12000 --climate 1 --workers 4
```

`results_sobol/` contains 512 actual solver evaluations at 12,000 BTU/h for the synthetic intermediate day. Each of the 2 independent scrambles has N=32 and 8 blocks (A, B, and six A_Bi matrices). First order estimates are noisy, and can exceed total indices; do not clip or interpret them as converged. The total indices for peak temperature are ~0.404 for roof U and ~0.373 for ACH (sample SD across just two scrambles ~0.286 and ~0.110). The coil temperature total index for peak RH is ~0.915. The pilot indicates priorities, not robust ranks. For a substantive analysis increase `--m` to 8 or higher, use at least 8 scrambles, check convergence, and repeat over relevant weather conditions. This is a recommendation, not a completed run. For nearly constant response the indices may be poorly conditioned; zero variance yields NaN.

### Estimators

For independent inputs, use `AB_i` = A with column i taken from B. Pooled sample variance V from Y(A) and Y(B). S_i = 1 - mean[(Y(B)-Y(AB_i))^2]/(2V); ST_i = mean[(Y(A)-Y(AB_i))^2]/(2V). Replicate SD is reported, not a confidence interval. Outputs: max internal temperature, degree-hours above 21.5 C, max RH, all 13:00–18:00. Existing v0.4 distributions retained; independent epistemic priors, not fitted statistics. Classical Sobol indices require independent factors; climate was fixed, not randomized here.

## Actual weather (network needed for fetch)

```sh
python historical.py fetch --csv climate/rio_2020_2025.csv --start 2020-01-01 --end 2025-12-31 --latitude -22.91 --longitude -43.17 --azimuth 270
python historical.py run --csv climate/rio_2020_2025.csv --n 128 --warmup 3 --workers 4
# conditional hot days instead of all summer days:
python historical.py run --csv climate/rio_2020_2025.csv --n 128 --warmup 3 --min-peak-outdoor 34 --out results_hot
```

Dates and coordinates are proposed city-level settings, not measured site coordinates; window azimuth is assumed west. Rio standard time UTC-03:00 is used explicitly (not a generic time-zone converter). Use a custom CSV for other locations or measured weather. API requests retrieve instantaneous dry-bulb T, dew point, horizontal global irradiance and vertical plane global tilted irradiance (GTI, azimuth transformed from north-clockwise to the provider's south-zero convention). These are hourly samples, linearly interpolated, not exact radiation integrals. GTI uses an isotropic sky and fixed ground albedo 0.2 per provider documentation. API docs: https://open-meteo.com/en/docs/historical-weather-api ; weather data by Open-Meteo.com; ERA5, Copernicus Climate Change Service. Metadata with request, returned coordinates, units and attribution is saved beside CSV. Check provider terms before redistributing climate data. Network access to this API failed with DNS error in development environment; real historical download and end-to-end real-data simulation are **not verified**. Mocked response and synthetic fixture tested; no historical results shipped.

CSV header: `timestamp,temperature_c,dewpoint_c,ghi_wm2,facade_wm2`. Timestamp naive local standard time ISO-8601 at integer hours, consecutive, unique; temperature Celsius and irradiance instantaneous W/m². Requires a following midnight for each target day. `fetch` supplies extra UTC coverage. For best warmup availability fetch dates before target period. Archive days uniformly sampled with replacement among eligible months (default December, January, February) and optional daily peak outdoor T threshold. Previous consecutive 3 days (configurable) free-running, then operate AC on target day. Thus models a start after unconditioned days, not continuous daily operation. Check warmup length convergence (including adjacent boundary filter) before quantitative use. The target date and all physical parameters are identical across capacities. The archive is treated as fixed empirical data; Wilson intervals quantify Monte Carlo uncertainty conditional on the archive and assumptions, not uncertainty in historical climate or annual reliability. Settings save input CSV SHA-256. ERA5 is gridded reanalysis, not a site weather station.

## Boundary physics and limitations

`T_sol = T_ext + alpha I / h_ext` (roof and opaque facade use GHI and vertical GTI respectively). Defaults alpha=0.6 for both and h_ext=20 W/(m² K); longwave exchange neglected. Unmeasured adjacent room and floor temperatures modeled with low-pass filters of outdoor temperature (24 h and 48 h time constants), optional additive offsets (0 C default). These are **new provisional assumptions**, not observations. No uncertainty model on these additional boundary parameters yet. Humidity computed from outdoor dew point at fixed 101325 Pa. Surface condensation and sorption, airflow obstruction, solar shading beyond the effective factor, radiative comfort, and actual capacity/airflow curves are not resolved. Supersaturation is flagged, not physically resolved. The preceding synthetic model significantly overpredicts the reported free-running temperatures of the office; changing weather alone does not validate the model. A separate roof mass node and independent opaque paths may be needed. Do not use the pilot to establish an equipment purchase or guaranteed comfort.

Older module descriptions and results retained in README_v04.md, README_v03.md, results_mc and results_mc_128. No changes to the prior synthetic physics except routing forcing via overridable methods. No public GitHub repository created in this version.
