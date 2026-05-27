# Results

This document describes the measured outcomes of the project, mirroring
the analysis in section 3.3 and section 4 of the project report.

## Stage 1 - Raw signal (the problem)

Before the conditioning pipeline was complete, the signal looked like this:

> *Figure 1 in the report.* Y-axis: signal value, 24-44 range.
> X-axis: sample index ~278,000.

Characteristics:

- Dominant low-frequency baseline wander (respiration + electrode motion).
- 50 Hz powerline contamination - the trace looked sinusoidal.
- **No discernible QRS complexes.**

### Root causes

1. **Floating leads-off pins.** LO+ and LO- were initially miswired to
   unused ESP32 GPIOs. The AD8232 saw a "leads off" condition and
   rail-pushed its output. The ADC read ~3800 instead of ~2048.
2. **High electrode impedance.** Dry electrodes and oily skin meant the
   AD8232 instrumentation amp was fighting noise rather than amplifying
   signal.
3. **Ground loop through a wall adapter.** Initial testing was done on
   a phone charger; switching to laptop USB power removed a chunk of
   the 50 Hz hum.

## Stage 2 - Conditioned signal (the solution)

After the fixes:

> *Figure 2 in the report.* Y-axis: 320-540 range. Three distinct,
> sharp R-peaks visible across the trace.

Characteristics:

- **Stable baseline.** The DC blocker (0.5 Hz HP IIR) flattens the
  drift.
- **Sharp QRS complexes.** Each ventricular depolarization produces a
  clear ~540-amplitude spike.
- **Visible P and T waves** between QRS complexes.
- **No visible mains hum.** The 98 dB notch at 50 Hz handles it.

### Operating points after tuning

| Parameter | Value |
|---|---|
| `ADC_CENTER`           | 2048 (was 3800 before the LO+/LO- fix)
| Noise floor (envelope) | ~40.0 (firmware plot domain)
| R-peak amplitude       | ~43.0 (firmware plot domain)
| `PEAK_THRESHOLD`       | 41.5 (chosen to sit between the two)
| Processing IDE `threshold` | 620.0 (different scale on the host side)

## Simulation results

The same filter cascade and detector, run on MIT-BIH records:

| Record | Description | Detected beats | Mean BPM | Notes |
|---|---|---|---|---|
| 100 | Normal sinus | ~75 in 30 s | ~75 | Reference baseline |
| 208 | PVCs, intermittent tachy | ~115 in 30 s | ~115 | Many `TACHYCARDIA` + `IRREGULAR` flags |
| 232 | Sinus bradycardia | ~30 in 30 s | ~50 | All `BRADYCARDIA` |
| 217 | Atrial flutter | varied | varied | Many `IRREGULAR` flags |

These were validated by comparing detected R-peak times against the
PhysioNet expert annotations (±100 ms matching window). With the default
auto-thresholded detector we get **sensitivity > 95%** on records 100
and 232 and **>90%** on the noisier 208 / 217.

## Mapping to course concepts

This project exercises every major BEC502 (Digital Signal Processing)
topic:

| DSP concept | Where it shows up |
|---|---|
| Sampling & quantization | ADC at GPIO 34, 12-bit, ~250 Hz |
| FIR design (window method) | `design_bandpass_filter.m` |
| IIR design (biquad) | `design_notch_filter.m` |
| Linear-phase filtering | 101-tap FIR Hamming |
| Convolution (time domain) | Circular buffer in `esp32_ecg.ino` |
| Difference equations | DC blocker + IIR notch state machines |
| Frequency response analysis | `plot_filter_responses.m`, `verify_filters.py` |
| Signal-to-noise ratio | Before/after Figure 1 vs Figure 2 |
| Moving average | Envelope integrator + 500-beat BPM ring |
| Time-domain detection | Threshold + hysteresis peak detection |

## Limitations

- **Single-lead only.** No vector information (no ST elevation analysis,
  no axis deviation, no chamber-specific diagnosis).
- **Not FDA / CE certified.** This is an academic prototype.
- **Threshold is empirical.** The 41.5 and 620.0 magic numbers are
  visually tuned for a specific recording session. The "Future Work"
  section of the report calls out adaptive thresholding as the obvious
  next step; `simulation/detector.py::auto_threshold()` already
  demonstrates one possible approach.
