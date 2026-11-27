# RoomClimate v0.3 — coupled thermal and humidity simulation

Python 3.10+; NumPy and SciPy. All physical quantities are in SI, except user-facing nominal capacity in BTU/h and clock hours. Run:

```sh
python -m pip install -r requirements.txt
python roomclimate.py
python roomclimate_transient.py --out results_v02
python roomclimate_humidity.py --out results_v03
python coil_sensitivity.py --out results_v03
```

## Model

The v0.1 steady-state and v0.2 sensible transient modules are preserved. The new module inherits the thermal network and time integration. The state is (air temperature, effective solid temperature, indoor humidity ratio w [kg/kg dry air]). A constant dry-air mass M=rho V and pressure 101325 Pa are assumed. Vapor balance: M dw/dt = m_inf(w_out-w) + Q_int,lat/h_fg - Q_AC,lat/h_fg. The sensible balance removes only Q_AC,sens; solid-air exchange cancels in the aggregate balance. The infiltration conductance from v0.2 is in W/K and is divided by cp to recover mass flow. Relative humidity follows from vapor partial pressure p*w/(0.62198+w) and the Magnus saturation pressure. Exterior humidity ratio is held at the design-day scenario value except for a 99% RH cap at low outdoor temperatures.

The coil is represented by an effective apparatus dew point T_c (default 10 C), with sensible and latent enthalpy drops approximated as cp*(T_air-T_c) and h_fg*max(0,w-w_sat(T_c)). Their ratio gives a variable sensible heat ratio. Total cooling is limited by nominal capacity and modulated by the existing temperature controller. This is an idealized model assuming sufficient recirculation airflow, not a manufacturer performance map. There is no independent humidity controller, condensate re-evaporation, moisture buffering, surface condensation, or variation of capacity with outdoor temperature. Supersaturation is flagged, not resolved. No electricity consumption is estimated.

## Experiment

Three synthetic weather scenarios for the 3 x 4 x 2.9 m office. The same free-running periodic initial state is used for each candidate in a given scenario. AC operates 10–18h; occupancy 9–18h; evaluation 13–18h; temperature target 21 C plus 0.5 C tolerance. Maximum RH 65% is an illustrative additional upper bound, not a claim of standards compliance or a complete comfort metric. Peaks are sampled at 5-minute intervals. Sensitivity study varies coil ADP from 8 to 14 C in steps of 2 C. The 12,000 BTU/h case in the intermediate scenario is marginal (21.498 C at ADP 10 C); its apparent pass is not robust to uncertainty. The 18,000 BTU/h case meets both criteria in the intermediate scenario at ADP 8, 10 and 12 C, but misses the RH limit at 14 C. The 24,000 BTU/h case passes the adverse baseline scenario. The same free-running peaks as v0.2 (37, 43 and 49 C) exceed the reported office temperatures; this model is not validated or calibrated and these results are not guarantees of equipment performance.

## Verification

The module tests psychrometric round-trip conversion, sensible energy conservation, vapor mass conservation, capacity saturation, dry-coil and thermostat limits, nonnegative humidity and integration refinement. In the intermediate 18,000 BTU/h case, refinement (rtol 1e-7 to 1e-9, max step 120 to 30 s) changed temperatures by ~4e-6 C and humidity ratio by ~4.8e-9 kg/kg. The CSV output contains 18 baseline simulations and 36 sensitivity simulations. No experimental validation performed.
