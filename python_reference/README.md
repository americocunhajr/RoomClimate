# RoomClimate v0.4.3 — Uncertainty in explicit roof model

This version extends v0.4.2 with Monte Carlo for the four-state thermal/humidity model (air, internal solids, roof and humidity ratio). It preserves the original solver, model and tests. This public repository includes selected result summaries; full sample tables, time series and archived verification logs remain in the original development package and can be regenerated. Prior results folders, where available, are historical and do not describe this version.

## Reproduce

Python 3.10+; install NumPy and SciPy from requirements.txt. In this directory:

```sh
python -m pip install -r requirements.txt
python -m unittest test_roof_mc test_roof test_v041 test_mc
python roof_mc.py --n 256 --seed 20261126 --workers 4 --climates 1 0 2 --out results_roof_mc_256
```

Climate codes 0/1/2: favorable/intermediate/unfavorable synthetic design days. All samples are independent within each climate (common random numbers across capacities and climates). No probabilities are assigned to climate scenarios. Output `samples.csv` records inputs and responses for every sample; `summary.csv` records counts, Wilson marginal 95% intervals and quantiles; `convergence.csv` reports nested sample prefixes. The seed and sample size are in `settings.txt`. The initial 64-sample run is kept in `results_roof_mc/` for comparison; it is a subset of the 256-sample run, not independent evidence.

## Distributions

| Input | Distribution | Parameters |
|---|---|---|
| Roof U [W/(m² K)] | Uniform | 0.8, 3.5 |
| Effective solar factor | Triangular | 0.35, 0.45, 0.55 |
| Infiltration [1/h] | Log-uniform | 0.2, 2 |
| Other effective thermal capacity [J/K] | Log-uniform | 600000, 2400000 |
| Internal sensible heat [W] | Triangular | 445, 545, 695 |
| Coil temperature [°C] | Uniform | 8, 14 |
| Concrete thickness [m] | Uniform | 0.10, 0.20 |
| Concrete density [kg/m³] | Triangular | 2200, 2300, 2500 |
| Concrete specific heat [J/(kg K)] | Triangular | 800, 880, 1000 |
| Concrete conductivity [W/(m K)] | Triangular | 1.4, 1.7, 2.1 |

Triangular parameters are minimum, mode, maximum. Independent primitive variables are an exploratory assumption. The remaining exterior resistance is a derived quantity: R_add = 1/U - 0.10 - 0.04 - d/k (m² K/W). Its support is positive because 1/3.5 - 0.14 - 0.20/1.4 > 0. R_add is assigned to the exterior side of the roof lump, as are the external film and half of the slab resistance. The roof thermal capacity is C = area*density*specific_heat*thickness. No Gaussian or artificially truncated Gaussian inputs. The new ranges are engineering assumptions, not estimates from measurements. A single U prior is retained in every climate scenario; this intentionally mixes the original construction-specific scenarios into a common uncertain construction and distinct fixed weather/adjacent-temperature profiles.

## Numerical method

The uncooled system is affine with constant Jacobian A, so its one-day map is x(24h)=exp(A*86400)x(0)+b. We obtain b with LSODA starting from the zero state and solve the periodic fixed-point equation for each sample. Each cooling simulation begins from that same free-running periodic initial state. LSODA rtol=1e-6, atol=1e-8, max_step=300 s, sample output every 5 min; schedule jumps and forcing knots are split. The periodic closure and integration refinement were tested on selected draws. The max temperature and RH refer to sampled values on 13–18h, not certified continuous maxima. This tests a first day of cooling after prior free-running days, not consecutive days of AC operation.

## Criteria

Setpoint 21 °C, tolerance 0.5 °C, maximum RH 65% over 13–18h; cooling allowed 10–18h. A joint success must meet both limits and have no simulated supersaturation during the day. Nominal capacity is an idealized total cooling bound, not a manufacturer's performance curve. RH and temperature constraints may be affected by model discrepancy. No direct condensation on surfaces, air distribution or equipment cycling physics. Wilson intervals are marginal sampling intervals, not bounds on modeling error and not a guarantee of performance. A 100% observed success fraction does not imply true probability 1. Real weather has not been downloaded; the preceding historical module remains available but has not been coupled to this MC run. Uncooled temperatures continue to exceed the owner's informal estimate. No validation or calibrated probability of comfort is claimed. Verify properties and real weather before a purchase decision.

## Executed run

256 samples x 3 synthetic climates x 6 capacities = 4608 response simulations, plus periodic initialization solves. Joint successes (of 256):

| BTU/h | Favorable | Intermediate | Unfavorable |
|---:|---:|---:|---:|
| 7500 | 0 | 0 | 0 |
| 9000 | 61 | 0 | 0 |
| 12000 | 254 | 110 | 0 |
| 18000 | 254 | 254 | 252 |
| 24000 | 254 | 254 | 254 |

The 18000 BTU/h capacity missed the temperature limit twice and the humidity limit twice in the unfavorable climate. Both humidity failures persisted at 24000 BTU/h. 17 unit tests passed; finer sampling (1 min instead of 5 min and stricter tolerances) on 24 selected cases near the thresholds changed no joint classifications. The original development package contains `verification_v043.txt` and `verification_sampling.txt`. The maximum temperature difference for those selected cases was 0.00188 °C. These tests do not constitute a rigorous bound for every realization.
