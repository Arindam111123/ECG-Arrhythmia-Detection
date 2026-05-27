"""
run_demo.py
===========
End-to-end "Simulate-then-Deploy" demo described in the project report.

Loads a MIT-BIH record, runs the same filter cascade and detector that
the ESP32 firmware uses, and prints / plots the result.

Run with:
    python run_demo.py                # uses record 100 (normal sinus)
    python run_demo.py 208            # PVC-rich record
    python run_demo.py 232 --duration 60

Outputs:
    - Console: per-beat classification, summary stats.
    - Plot   : raw / filtered / envelope traces with detected R-peaks
               and annotated arrhythmia labels.
"""

from __future__ import annotations
import argparse
import sys

import matplotlib.pyplot as plt
import numpy as np

from mitbih_loader import load_record, resample_to, RECOMMENDED_RECORDS
from filters       import build_filters, apply_pipeline, envelope
from detector      import detect_peaks, auto_threshold


def main() -> int:
    ap = argparse.ArgumentParser(description="ECG simulation pipeline.")
    ap.add_argument("record", nargs="?", default="100",
                    help="MIT-BIH record id (e.g. 100, 208, 232).")
    ap.add_argument("--duration", type=float, default=30.0,
                    help="Seconds of signal to process.")
    ap.add_argument("--fs-target", type=int, default=250,
                    help="Resample to this rate (ESP32 firmware uses 250 Hz).")
    ap.add_argument("--no-plot", action="store_true",
                    help="Skip the matplotlib figure.")
    args = ap.parse_args()

    # ----- 1. Fetch record ----------------------------------------
    print(f"[1] Loading MIT-BIH record '{args.record}' "
          f"({args.duration:.0f} s)...")
    raw, fs_in, ann = load_record(args.record, duration_s=args.duration)
    print(f"    Native fs = {fs_in} Hz, samples = {len(raw)}, "
          f"annotations = {len(ann.sample)}")

    # ----- 2. Resample to firmware rate ---------------------------
    sig = resample_to(raw, fs_in, args.fs_target)
    fs  = args.fs_target
    print(f"[2] Resampled to {fs} Hz, samples = {len(sig)}")

    # ----- 3. Build the same filters as firmware ------------------
    fb = build_filters(fs=fs)
    print(f"[3] Built FIR bandpass ({len(fb.b_bp)} taps) "
          f"+ IIR notch (2nd-order) @ 50 Hz")

    # ----- 4. Run the cascade -------------------------------------
    filtered = apply_pipeline(sig, fb)
    env      = envelope(filtered, window=16)

    # ----- 5. Pick a threshold and detect -------------------------
    thr = auto_threshold(env)
    print(f"[4] Adaptive threshold = {thr:.4f}")

    result = detect_peaks(env, fs=fs, threshold=thr)
    print(f"[5] Detection complete.")
    print(f"    Beats     : {len(result.beats)}")
    print(f"    Mean BPM  : {result.mean_bpm:.1f}")
    print(f"    Normal    : {result.n_normal}")
    print(f"    Tachy.    : {result.n_tachy}")
    print(f"    Brady.    : {result.n_brady}")
    print(f"    Irregular : {result.n_irregular}")

    # ----- 6. Compare against PhysioNet annotations ---------------
    # MIT-BIH annotation symbols: 'N' = normal, 'V' = PVC, 'A' = APC,
    # '/' = pacemaker, etc. We match on time proximity (within 100 ms).
    if len(ann.sample) > 0:
        ann_times = ann.sample / fs_in
        ann_times = ann_times[ann_times < args.duration]
        det_times = np.array([b.time_s for b in result.beats])

        if len(det_times) > 0:
            tol = 0.10
            matched = 0
            for at in ann_times:
                if np.any(np.abs(det_times - at) < tol):
                    matched += 1
            sens = matched / max(len(ann_times), 1) * 100
            ppv  = matched / max(len(det_times), 1) * 100
            print(f"    Sensitivity vs PhysioNet : {sens:.1f}% "
                  f"({matched}/{len(ann_times)})")
            print(f"    Positive predictive value: {ppv:.1f}% "
                  f"({matched}/{len(det_times)})")

    # ----- 7. Plot -------------------------------------------------
    if not args.no_plot:
        plot_results(sig, filtered, env, result, thr, fs)

    return 0


def plot_results(raw_sig, filtered, env_sig, result, thr, fs):
    t = np.arange(len(raw_sig)) / fs

    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
    fig.suptitle("MIT-BIH simulation - same pipeline as ESP32 firmware",
                 fontweight="bold")

    axes[0].plot(t, raw_sig, color="#222", linewidth=0.8)
    axes[0].set_title("1. Raw ECG (after resample to 250 Hz)")
    axes[0].set_ylabel("mV"); axes[0].grid(alpha=0.3)

    axes[1].plot(t, filtered, color="#1f77b4", linewidth=0.9)
    axes[1].set_title("2. After IIR notch + FIR bandpass")
    axes[1].set_ylabel("mV"); axes[1].grid(alpha=0.3)

    axes[2].plot(t, env_sig, color="#2ca02c", linewidth=1.0,
                 label="envelope")
    axes[2].axhline(thr, color="#d62728", linestyle="--",
                    linewidth=1, label=f"threshold {thr:.3f}")

    # Mark detected peaks colored by label.
    color_map = {"NORMAL": "#2ca02c", "TACHYCARDIA": "#d62728",
                 "BRADYCARDIA": "#ff7f0e"}
    for b in result.beats:
        c = color_map.get(b.label, "#888")
        axes[2].plot(b.time_s, env_sig[b.sample], "o",
                     color=c, markersize=6, markeredgecolor="k",
                     markeredgewidth=0.5)
        if b.irregular:
            axes[2].plot(b.time_s, env_sig[b.sample], "x",
                         color="black", markersize=10)

    axes[2].set_title("3. Envelope + detected R-peaks")
    axes[2].set_ylabel("envelope"); axes[2].set_xlabel("time (s)")
    axes[2].grid(alpha=0.3); axes[2].legend(loc="upper right")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    sys.exit(main())
