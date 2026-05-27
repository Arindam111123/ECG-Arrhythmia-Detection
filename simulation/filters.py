"""
filters.py
==========
Python implementations of the *exact* filter cascade running on the
ESP32 firmware. Lets us:

1. Sanity-check the MATLAB-generated coefficients against scipy.
2. Plot the cascaded magnitude response for the report figures.
3. Pre-process MIT-BIH recordings the same way the firmware does
   before feeding them to the detector.
"""

from __future__ import annotations
from dataclasses import dataclass
import math

import numpy as np
from scipy.signal import firwin, iirnotch, lfilter, freqz


# -----------------------------------------------------------------
# Coefficient design
# -----------------------------------------------------------------
@dataclass
class FilterBank:
    fs: int
    dc_alpha: float             # 1st-order IIR DC-blocker coefficient
    b_bp: np.ndarray            # FIR bandpass numerator
    b_notch: np.ndarray         # IIR notch numerator
    a_notch: np.ndarray         # IIR notch denominator


def build_filters(fs: int = 250,
                  fc_low: float = 0.5,
                  fc_high: float = 40.0,
                  fir_order: int = 100,
                  notch_f0: float = 50.0,
                  notch_q: float = 30.0) -> FilterBank:
    """
    Build the firmware's two-stage bandpass cascade plus the IIR notch.

    Why two stages?
    ---------------
    An FIR with a 0.5 Hz lower cutoff would need >1000 taps at
    Fs = 250 Hz to meaningfully reject baseline wander. That's too
    expensive for the ESP32 inner loop. We split the work:

        Stage A: 1st-order IIR DC-blocker  -> handles the 0.5 Hz HP edge
        Stage B: 100-tap FIR bandpass      -> enforces the 40 Hz LP edge
                                              with linear phase across
                                              the diagnostic 1-40 Hz band

    The cascade is functionally the "Bandpass 0.5 - 40 Hz" block
    described in section 2.3 of the report; we just factored the
    design across two cheap stages.
    """
    # 1st-order IIR HP: y[n] = x[n] - x[n-1] + alpha * y[n-1].
    # 3 dB cutoff ~= fs * (1 - alpha) / (2 * pi).
    alpha = 1.0 - 2.0 * math.pi * fc_low / fs

    # FIR is designed as a bandpass for graceful overlap with stage A,
    # but its primary action is the 40 Hz upper roll-off.
    b_bp = firwin(fir_order + 1,
                  [fc_low, fc_high],
                  pass_zero=False,
                  fs=fs,
                  window="hamming")

    b_n, a_n = iirnotch(notch_f0, notch_q, fs=fs)

    return FilterBank(fs=fs, dc_alpha=alpha,
                      b_bp=b_bp, b_notch=b_n, a_notch=a_n)


# -----------------------------------------------------------------
# Application
# -----------------------------------------------------------------
def apply_dc_blocker(sig: np.ndarray, alpha: float) -> np.ndarray:
    """1st-order IIR high-pass: y[n] = x[n] - x[n-1] + alpha * y[n-1]."""
    return lfilter([1.0, -1.0], [1.0, -alpha], sig)


def apply_pipeline(sig: np.ndarray, fb: FilterBank) -> np.ndarray:
    """
    Run the full firmware cascade: DC-blocker -> notch -> FIR bandpass.
    """
    y = apply_dc_blocker(sig, fb.dc_alpha)
    y = lfilter(fb.b_notch, fb.a_notch, y)
    y = lfilter(fb.b_bp,    [1.0],      y)
    return y


def envelope(sig: np.ndarray, window: int = 16) -> np.ndarray:
    """
    Short-window absolute-value moving average. Mirrors the firmware's
    ``env_buf`` integrator. Output sits at a small positive baseline
    with sharp QRS-shaped bumps - the morphology shown in Figure 1
    of the project report.
    """
    rect = np.abs(sig)
    kernel = np.ones(window) / window
    return np.convolve(rect, kernel, mode="same")


def magnitude_response(fb: FilterBank, n: int = 4096):
    """
    Return (frequencies_hz, |H_dc|, |H_bp|, |H_notch|, |H_cascade|)
    for the full firmware pipeline.
    """
    w,  h_bp = freqz(fb.b_bp,         [1.0],            n)
    _,  h_nt = freqz(fb.b_notch,      fb.a_notch,       n)
    _,  h_dc = freqz([1.0, -1.0],     [1.0, -fb.dc_alpha], n)
    f = w * fb.fs / (2 * np.pi)
    return f, np.abs(h_dc), np.abs(h_bp), np.abs(h_nt), np.abs(h_dc * h_bp * h_nt)
