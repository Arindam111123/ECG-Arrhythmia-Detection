# DSP Pipeline

This document covers the math behind every stage between
"ADC sample" and "BPM displayed on screen". It assumes you've taken a
standard undergraduate DSP course (z-transforms, transfer functions,
windowed-sinc FIR design).

## 1. Acquisition

| Quantity | Value |
|---|---|
| ADC resolution | 12 bits (0..4095) |
| ADC attenuation | 11 dB (full-scale ~3.3 V) |
| Effective sample rate | ~250 Hz (one `analogRead` + `Serial.println` + `delay(1)`) |
| Channel | GPIO 34 (ADC1_CH6) |

We assume Fs = 250 Hz throughout the rest of this document.

After acquisition we subtract `ADC_CENTER = 2048` to center the signal
around zero. The raw ECG amplitude after the AD8232 gain stage typically
swings ±100 to ±500 LSB; the exact value depends on skin impedance and
electrode placement.

## 2. DC blocker (stage A of bandpass)

The first conditioning stage is a one-pole IIR high-pass:

```
        y[n] = x[n] - x[n-1] + α · y[n-1]
```

Transfer function:

```
              1 - z^-1
    H(z) = ----------------
            1 - α · z^-1
```

The -3 dB cutoff frequency is approximately:

```
    fc ≈ Fs · (1 - α) / (2π)
```

With `α = 0.9874` and `Fs = 250 Hz`:

```
    fc ≈ 250 · (1 - 0.9874) / (2π) ≈ 0.50 Hz
```

This kills baseline wander (respiration, electrode motion) without the
thousand-tap FIR that would be needed to achieve the same result with
linear phase.

## 3. IIR notch (50 Hz mains)

A second-order biquad notch:

```
              1 - 2·cos(ω₀)·z^-1 + z^-2
    H(z) = ─────────────────────────────────
            1 - 2·r·cos(ω₀)·z^-1 + r²·z^-2
```

where ω₀ = 2π · F₀ / Fs and r = (something close to 1) controls the
notch sharpness via Q ≈ ω₀ / (2 · (1 - r)).

For F₀ = 50 Hz, Q = 30 at Fs = 250 Hz, scipy's `iirnotch` yields:

```
    b = [+0.9794828, -0.6053536, +0.9794828]
    a = [+1.0000000, -0.6053536, +0.9589655]
```

Notch depth at 50 Hz is **~98 dB**, more than enough to remove powerline
hum. Phase distortion is confined to a narrow band around 50 Hz, which
is outside any ECG morphological information.

> **For US mains (60 Hz):** change `MAINS_FREQ_HZ` to 60 in
> `firmware/esp32_ecg/config.h` and re-run the MATLAB script (or call
> `build_filters(notch_f0=60)` in Python). The notch coefficients
> change; nothing else does.

## 4. FIR bandpass (stage B of bandpass)

A 101-tap linear-phase FIR designed with the window method:

```
    b[k] = w_hamming[k] · h_ideal[k - N/2]
```

where `h_ideal` is the impulse response of the ideal bandpass (a
difference of two sinc functions) and `w_hamming` is the standard
Hamming window:

```
    w[k] = 0.54 - 0.46 · cos(2π · k / N)
```

Specs:

| Spec | Value |
|---|---|
| Order N | 100 |
| Taps | 101 |
| Lower cutoff | 0.5 Hz (gentle, since DC blocker has already done the heavy lifting) |
| Upper cutoff | 40 Hz |
| Stopband at Fs/2 | -93 dB |
| Group delay | N/2 = 50 samples (200 ms) - constant across all frequencies |

The 200 ms latency is acceptable for visualization (it's barely noticeable
to a human watching the trace) and it does *not* affect BPM accuracy
because every R-peak is delayed by the same amount.

## 5. Envelope (rectify + integrate)

```
    env[n] = (1 / W) · Σ |y[n - k]|     for k = 0..W-1
```

with W = 16 samples (~64 ms at Fs = 250 Hz). This is the simplest
possible envelope detector; it converts the bandpass-filtered ECG into
a signal with a small positive baseline and sharp "bumps" at each QRS
complex.

The 16-sample window length is chosen to be:

- Long enough to bridge the small dip between Q and R (~10 ms wide)
- Short enough to keep separate QRS complexes distinct (RR > 300 ms)

## 6. Peak detection

Rising-edge threshold cross with hysteresis:

```
    if NOT armed and env[n] > THRESH:
        armed = false
        record peak at time n
    elif armed and env[n] < THRESH - HYST:
        armed = true
```

Additionally a **refractory period** of 300 ms rejects double-detections
(equivalent to capping the maximum BPM at 200, which is well above any
sustainable human heart rate).

## 7. Classification

```
    if BPM > 100   :  TACHYCARDIA
    if BPM <  60   :  BRADYCARDIA
    otherwise      :  NORMAL

    if |ΔRR / RR_prev| > 0.20  :  flag as IRREGULAR
```

These thresholds come from standard clinical definitions:

| Condition | Resting heart rate |
|---|---|
| Bradycardia | < 60 BPM |
| Normal | 60-100 BPM |
| Tachycardia | > 100 BPM |
| Irregular (RR variation) | > 20% beat-to-beat change |

A 500-sample moving average smooths the displayed BPM to remove
single-beat jitter.

## Frequency-response figures

Generate the magnitude-response plots:

```bash
# Python
cd simulation
python verify_filters.py

# MATLAB
cd matlab
generate_coefficients
```

Expected behavior at Fs = 250 Hz:

| Frequency | Cascade attenuation |
|---|---|
| 0 Hz (DC) | ∞ (240 dB practically) |
| 0.5 Hz | -5.1 dB |
| 1 Hz | -2.7 dB |
| 10 Hz | -0.0 dB |
| 50 Hz | -98 dB |
| 60 Hz | -66 dB |
| 125 Hz (Fs/2) | -93 dB |
