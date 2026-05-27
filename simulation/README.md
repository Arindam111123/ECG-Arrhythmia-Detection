# Simulation

Validates the same DSP pipeline against the **MIT-BIH Arrhythmia
Database** so we can prove the algorithm works without touching real
hardware. This is the "Simulate" half of the project's
*Simulate-then-Deploy* methodology.

## Install

```bash
pip install -r requirements.txt
```

## Quick demos

```bash
# Record 100 - normal sinus rhythm (great first sanity check)
python run_demo.py 100 --duration 30

# Record 208 - many PVCs, intermittent tachycardia
python run_demo.py 208 --duration 60

# Record 232 - sinus bradycardia
python run_demo.py 232

# Verify filters meet the design targets
python verify_filters.py
```

The first run downloads the requested record from PhysioNet and caches
it locally; subsequent runs are instant.

## What each module does

| File | Purpose |
|---|---|
| `mitbih_loader.py` | Downloads and resamples MIT-BIH records via `wfdb`. |
| `filters.py`       | Python implementations of the firmware's DC-blocker + notch + FIR bandpass cascade. |
| `detector.py`      | R-peak detection, R-R intervals, Tachy/Brady/Irregular classification. |
| `run_demo.py`      | End-to-end CLI demo: load → filter → detect → plot. |
| `verify_filters.py`| Print pass/fail report on cascade magnitude response. |

## Useful records

| Record ID | What's in it |
|---|---|
| 100  | Normal sinus rhythm. Reference baseline. |
| 105  | Noisy recording. Good for stress-testing the detector. |
| 208  | Frequent PVCs and tachycardia bursts. |
| 217  | Atrial flutter, very irregular rhythm. |
| 232  | Sinus bradycardia. |

Full record list: <https://physionet.org/content/mitdb/1.0.0/>
