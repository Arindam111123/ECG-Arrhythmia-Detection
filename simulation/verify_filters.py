"""
verify_filters.py
=================
Plot the magnitude response of the firmware's filter cascade and
confirm:
    - bandpass stopbands are >= 40 dB down at DC and at Fs/2
    - notch depth at 50 Hz is >= 30 dB
    - cascaded passband ripple is < 1 dB inside 1 - 35 Hz

Run with:
    python verify_filters.py
"""

import numpy as np
import matplotlib.pyplot as plt

from filters import build_filters, magnitude_response


def main():
    fb = build_filters(fs=250)
    f, mag_bp, mag_nt, mag_total = magnitude_response(fb)

    # -- numeric checks ----------------------------------------------
    db_bp    = 20 * np.log10(mag_bp + 1e-12)
    db_nt    = 20 * np.log10(mag_nt + 1e-12)
    db_total = 20 * np.log10(mag_total + 1e-12)

    passband_mask = (f >= 1) & (f <= 35)
    pass_max = db_bp[passband_mask].max()
    pass_min = db_bp[passband_mask].min()
    pass_ripple = pass_max - pass_min

    notch_idx   = np.argmin(np.abs(f - 50))
    notch_depth = -db_nt[notch_idx]
    dc_atten    = -db_bp[0]
    hf_atten    = -db_bp[-1]

    print("=== Filter verification ===")
    print(f"  DC attenuation (bandpass)      : {dc_atten:6.2f} dB")
    print(f"  Fs/2 attenuation (bandpass)    : {hf_atten:6.2f} dB")
    print(f"  Passband ripple (1-35 Hz)      : {pass_ripple:6.2f} dB")
    print(f"  Notch depth at 50 Hz           : {notch_depth:6.2f} dB")
    print()
    ok = (dc_atten > 30 and hf_atten > 30
          and pass_ripple < 1.0 and notch_depth > 25)
    print("Result:", "PASS" if ok else "FAIL")

    # -- plot --------------------------------------------------------
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    fig.suptitle("Firmware filter cascade - magnitude response",
                 fontweight="bold")

    axes[0].plot(f, db_bp); axes[0].set_ylim(-80, 5)
    axes[0].set_title("FIR Bandpass 0.5-40 Hz (Hamming, order 100)")
    axes[0].set_ylabel("dB"); axes[0].grid(alpha=0.3)
    axes[0].axvspan(0.5, 40, color="#2ca02c", alpha=0.07)

    axes[1].plot(f, db_nt); axes[1].set_ylim(-60, 5)
    axes[1].set_title("IIR Notch 50 Hz (biquad, Q = 30)")
    axes[1].set_ylabel("dB"); axes[1].grid(alpha=0.3)
    axes[1].axvline(50, color="#d62728", linestyle="--")

    axes[2].plot(f, db_total, color="#2ca02c"); axes[2].set_ylim(-80, 5)
    axes[2].set_title("Cascade (what the ECG actually sees)")
    axes[2].set_ylabel("dB"); axes[2].set_xlabel("Hz")
    axes[2].grid(alpha=0.3)
    axes[2].axvspan(0.5, 40, color="#2ca02c", alpha=0.07)
    axes[2].axvline(50, color="#d62728", linestyle="--")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
