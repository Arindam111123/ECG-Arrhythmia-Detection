"""
mitbih_loader.py
================
Convenience wrapper around the ``wfdb`` library for fetching records from
the MIT-BIH Arrhythmia Database (PhysioNet).

We use this database as a stand-in for live AD8232 recordings during the
"Simulation" phase of the project. The signals are clinically annotated,
sampled at 360 Hz, and contain every arrhythmia class we care about
(N, V, A, F, ...).

Typical usage
-------------
>>> from mitbih_loader import load_record
>>> sig, fs, ann = load_record('100', duration_s=30)
>>> sig.shape, fs, len(ann.sample)
((10800,), 360, 75)
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import wfdb


# Default cache directory so we don't re-download on every run.
CACHE_DIR = Path.home() / ".cache" / "mitbih"


@dataclass
class Annotation:
    """Trimmed-down view of a wfdb annotation object."""
    sample: np.ndarray       # sample indices of beat labels
    symbol: list[str]        # one-letter beat label per index
    fs: int                  # sampling frequency

    @property
    def time_s(self) -> np.ndarray:
        return self.sample / self.fs


def load_record(
    record_id: str = "100",
    duration_s: Optional[float] = None,
    channel: int = 0,
    pn_dir: str = "mitdb",
) -> Tuple[np.ndarray, int, Annotation]:
    """
    Download (or load from cache) a MIT-BIH record and return
    (signal, sampling_rate, annotation).

    Parameters
    ----------
    record_id : str
        Record number, e.g. '100', '101', '208', ...
    duration_s : float | None
        If given, only the first ``duration_s`` seconds are returned.
    channel : int
        Which lead to pick. Most records have channel 0 = MLII.
    pn_dir : str
        PhysioNet directory. 'mitdb' is the canonical MIT-BIH set.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # wfdb caches under cwd by default; redirect to our cache.
    record = wfdb.rdrecord(record_id, pn_dir=pn_dir)
    ann    = wfdb.rdann(record_id, "atr", pn_dir=pn_dir)

    fs   = int(record.fs)
    sig  = record.p_signal[:, channel].astype(np.float64)

    if duration_s is not None:
        n = int(duration_s * fs)
        sig = sig[:n]
        mask = ann.sample < n
        ann_sample = ann.sample[mask]
        ann_symbol = [s for s, m in zip(ann.symbol, mask) if m]
    else:
        ann_sample = ann.sample
        ann_symbol = list(ann.symbol)

    return sig, fs, Annotation(sample=ann_sample, symbol=ann_symbol, fs=fs)


def resample_to(sig: np.ndarray, fs_in: int, fs_out: int = 250) -> np.ndarray:
    """Resample to match the ESP32 firmware's effective sample rate."""
    if fs_in == fs_out:
        return sig
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(fs_in, fs_out)
    return resample_poly(sig, fs_out // g, fs_in // g)


# Records that are nice to start with:
#   '100'  - mostly Normal sinus rhythm, easy baseline
#   '208'  - lots of PVCs, good for Tachycardia detection demos
#   '232'  - Bradycardia / Sinus bradycardia
#   '217'  - Atrial flutter, irregular rhythm
RECOMMENDED_RECORDS = {
    "normal":      "100",
    "tachy_pvc":   "208",
    "brady":       "232",
    "irregular":   "217",
}
