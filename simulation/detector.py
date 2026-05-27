"""
detector.py
===========
R-peak detection and arrhythmia classification, mirroring the logic
that runs on the ESP32 firmware (esp32_ecg.ino).

The detector is intentionally simple:

  1. Find samples where the envelope crosses an amplitude threshold
     (rising edge only, with hysteresis to avoid double-counting).
  2. Reject crossings closer than a refractory period (300 ms = 200 BPM).
  3. Convert R-R intervals to instantaneous BPM.
  4. Classify each beat as Tachy / Brady / Normal and flag any beat
     whose RR differs from the previous one by more than 20%.

This isn't a Pan-Tompkins-grade detector, but it matches what the
report describes and is easy to port one-to-one to ESP32 C++.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

import numpy as np


# -----------------------------------------------------------------
@dataclass
class Beat:
    sample:  int        # sample index of the R-peak
    time_s:  float      # time of the R-peak (s)
    rr_ms:   float      # interval to previous R (ms)
    bpm:     float      # instantaneous BPM
    label:   str        # NORMAL / TACHYCARDIA / BRADYCARDIA
    irregular: bool     # True if |dRR/RR_prev| > 0.2


@dataclass
class DetectionResult:
    beats: List[Beat] = field(default_factory=list)
    fs: int = 250

    @property
    def mean_bpm(self) -> float:
        if not self.beats: return 0.0
        bpms = [b.bpm for b in self.beats]
        return float(np.mean(bpms))

    @property
    def n_normal(self) -> int:
        return sum(1 for b in self.beats if b.label == "NORMAL")

    @property
    def n_tachy(self) -> int:
        return sum(1 for b in self.beats if b.label == "TACHYCARDIA")

    @property
    def n_brady(self) -> int:
        return sum(1 for b in self.beats if b.label == "BRADYCARDIA")

    @property
    def n_irregular(self) -> int:
        return sum(1 for b in self.beats if b.irregular)


# -----------------------------------------------------------------
def detect_peaks(envelope_sig: np.ndarray,
                 fs: int,
                 threshold: float,
                 hysteresis: float = 0.5,
                 rr_min_ms: int = 300,
                 rr_max_ms: int = 2000) -> DetectionResult:
    """
    Detect R-peaks on the envelope signal and classify each beat.

    Parameters
    ----------
    envelope_sig
        Output of ``filters.envelope(...)``. Should sit at a small
        positive baseline with sharp upward QRS bumps.
    fs
        Sampling rate of the signal.
    threshold
        Amplitude above which a sample is "in" a peak. The project
        report's value of 41.5 corresponds to the firmware's plot
        domain; in the simulation we recompute it per-record from
        the signal's own statistics.
    hysteresis
        How far below ``threshold`` the signal must fall before we
        re-arm for the next rising edge.
    rr_min_ms, rr_max_ms
        Physiological gate. Beats closer than ``rr_min_ms`` or further
        than ``rr_max_ms`` are rejected as spurious.
    """
    result = DetectionResult(fs=fs)

    armed = True
    last_peak_idx = -1
    last_rr_ms    = 0.0

    for i, v in enumerate(envelope_sig):
        if armed and v > threshold:
            armed = False
            if last_peak_idx >= 0:
                rr_samples = i - last_peak_idx
                rr_ms = rr_samples / fs * 1000.0
                if rr_min_ms < rr_ms < rr_max_ms:
                    bpm = 60000.0 / rr_ms

                    if bpm > 100:   label = "TACHYCARDIA"
                    elif bpm < 60:  label = "BRADYCARDIA"
                    else:           label = "NORMAL"

                    irregular = False
                    if last_rr_ms > 0:
                        drr = abs(rr_ms - last_rr_ms) / last_rr_ms
                        irregular = drr > 0.20

                    result.beats.append(Beat(
                        sample=i,
                        time_s=i / fs,
                        rr_ms=rr_ms,
                        bpm=bpm,
                        label=label,
                        irregular=irregular,
                    ))
                    last_rr_ms = rr_ms
            last_peak_idx = i

        elif not armed and v < (threshold - hysteresis):
            armed = True

    return result


def auto_threshold(envelope_sig: np.ndarray,
                   noise_percentile: float = 60.0,
                   peak_percentile:  float = 99.0,
                   weight: float = 0.4) -> float:
    """
    Crude but effective adaptive threshold.

    Real R-peaks live well above the bulk of the envelope distribution,
    so we take a high percentile (e.g. 99%) as the peak amplitude
    estimate and a middling percentile (60%) as the noise floor, then
    place the threshold between them.

    This mimics what the report's "Future Work" calls "an adaptive
    threshold algorithm that automatically adjusts to the signal
    baseline, removing the need for hard-coded magic numbers."
    """
    noise = np.percentile(envelope_sig, noise_percentile)
    peak  = np.percentile(envelope_sig, peak_percentile)
    return float(noise + weight * (peak - noise))
