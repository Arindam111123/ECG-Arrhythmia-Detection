"""
make_docs_figures.py
====================
Generate the static PNG figures referenced by `docs/dsp_pipeline.md`
and `docs/results.md` so README readers can see plots without running
the live tooling.

Outputs (saved to ../docs/images/):
    - filter_response.png       (cascaded magnitude response)
    - synthetic_pipeline.png    (clean -> noisy -> filtered ECG)
    - detection_demo.png        (envelope + detected R-peaks)

Run from the project root:
    python scripts/make_docs_figures.py
"""

from __future__ import annotations
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")             # headless
import matplotlib.pyplot as plt

# Make `simulation/` importable regardless of where we're invoked from.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "simulation"))

from filters  import build_filters, apply_pipeline, envelope, magnitude_response
from detector import detect_peaks, auto_threshold


OUT = HERE.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# 1. Filter response
# ---------------------------------------------------------------------
def fig_filter_response():
    fb = build_filters(fs=250)
    f, mag_dc, mag_bp, mag_nt, mag_total = magnitude_response(fb)

    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    fig.suptitle("ECG Filter Pipeline - Magnitude Response (Fs = 250 Hz)",
                 fontweight="bold")

    axes[0].plot(f, 20*np.log10(mag_bp + 1e-12), color="#1f77b4")
    axes[0].set_ylim(-80, 5); axes[0].grid(alpha=0.3)
    axes[0].set_title("FIR Bandpass 0.5 - 40 Hz (Hamming, order 100)")
    axes[0].set_ylabel("dB")
    axes[0].axvspan(0.5, 40, color="#2ca02c", alpha=0.08)

    axes[1].plot(f, 20*np.log10(mag_nt + 1e-12), color="#d62728")
    axes[1].set_ylim(-60, 5); axes[1].grid(alpha=0.3)
    axes[1].set_title("IIR Notch 50 Hz (biquad, Q = 30)")
    axes[1].set_ylabel("dB")
    axes[1].axvline(50, color="#d62728", linestyle="--", linewidth=1)

    axes[2].plot(f, 20*np.log10(mag_total + 1e-12), color="#2ca02c")
    axes[2].set_ylim(-100, 5); axes[2].grid(alpha=0.3)
    axes[2].set_title("Cascade: DC blocker + FIR + Notch")
    axes[2].set_xlabel("Hz"); axes[2].set_ylabel("dB")
    axes[2].axvspan(0.5, 40, color="#2ca02c", alpha=0.08)
    axes[2].axvline(50, color="#d62728", linestyle="--", linewidth=1)

    plt.tight_layout()
    plt.savefig(OUT / "filter_response.png", dpi=120)
    plt.close(fig)
    print(f"  wrote {OUT / 'filter_response.png'}")


# ---------------------------------------------------------------------
# 2. Synthetic ECG pipeline
# ---------------------------------------------------------------------
def _synth_ecg(fs=250, duration=6.0, bpm=75, seed=0):
    rr = 60.0 / bpm
    t = np.arange(0, duration, 1/fs)
    n = len(t)
    ecg = np.zeros(n)
    waves = [(0.10, -0.20, 0.025), (-0.15, -0.05, 0.010),
             ( 1.00,  0.00, 0.012), (-0.30,  0.05, 0.012),
             ( 0.30,  0.30, 0.040)]
    for k in range(int(duration / rr) + 1):
        c = k * rr
        for A, mu, sd in waves:
            ecg += A * np.exp(-((t - (c + mu))**2) / (2 * sd**2))
    rng = np.random.default_rng(seed)
    noisy = ecg + 0.4*np.sin(2*np.pi*0.3*t) \
                + 0.5*np.sin(2*np.pi*50*t) \
                + 0.05*rng.standard_normal(n)
    return t, ecg, noisy


def fig_synthetic_pipeline():
    fs = 250
    t, clean, noisy = _synth_ecg(fs=fs)
    fb = build_filters(fs=fs)
    filtered = apply_pipeline(noisy * 500.0, fb)

    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    fig.suptitle("Synthetic ECG through the firmware pipeline",
                 fontweight="bold")

    axes[0].plot(t, clean, color="#222"); axes[0].grid(alpha=0.3)
    axes[0].set_title("Ground truth (clean Gaussian-summed ECG)")
    axes[0].set_ylabel("mV")

    axes[1].plot(t, noisy, color="#d62728"); axes[1].grid(alpha=0.3)
    axes[1].set_title("Contaminated: + baseline wander + 50 Hz hum + EMG")
    axes[1].set_ylabel("mV")

    axes[2].plot(t, filtered, color="#2ca02c"); axes[2].grid(alpha=0.3)
    axes[2].set_title("After DC blocker + IIR notch + FIR bandpass")
    axes[2].set_xlabel("time (s)"); axes[2].set_ylabel("amplitude")

    plt.tight_layout()
    plt.savefig(OUT / "synthetic_pipeline.png", dpi=120)
    plt.close(fig)
    print(f"  wrote {OUT / 'synthetic_pipeline.png'}")


# ---------------------------------------------------------------------
# 3. Detection demo
# ---------------------------------------------------------------------
def fig_detection_demo():
    fs = 250
    t, _, noisy = _synth_ecg(fs=fs, duration=12)
    fb = build_filters(fs=fs)
    filtered = apply_pipeline(noisy * 500.0, fb)
    env = envelope(filtered, window=16)

    thr = auto_threshold(env)
    res = detect_peaks(env, fs=fs, threshold=thr)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(t, env, color="#2ca02c", linewidth=1, label="envelope")
    ax.axhline(thr, color="#d62728", linestyle="--", linewidth=1,
               label=f"threshold {thr:.2f}")
    for b in res.beats:
        c = {"NORMAL": "#1a9850", "TACHYCARDIA": "#d73027",
             "BRADYCARDIA": "#fdae61"}.get(b.label, "#888")
        ax.plot(b.time_s, env[b.sample], "o", color=c,
                markersize=7, markeredgecolor="k", markeredgewidth=0.5)

    ax.set_title(f"R-peak detection (avg {res.mean_bpm:.0f} BPM, "
                 f"{len(res.beats)} beats)")
    ax.set_xlabel("time (s)"); ax.set_ylabel("envelope value")
    ax.grid(alpha=0.3); ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(OUT / "detection_demo.png", dpi=120)
    plt.close(fig)
    print(f"  wrote {OUT / 'detection_demo.png'}")


if __name__ == "__main__":
    print("Generating documentation figures...")
    fig_filter_response()
    fig_synthetic_pipeline()
    fig_detection_demo()
    print("Done.")
