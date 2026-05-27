# Hardware Setup

This guide covers the physical assembly: wiring the AD8232 front end to
the ESP32, attaching electrodes, and the bring-up gotchas we hit.

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | ESP32 DOIT DevKit V1 | Any ESP32 board with a brought-out ADC pin works |
| 1 | AD8232 ECG breakout (SparkFun, RobotDyn, generic) | The "3-pin output" or "4-pin output" variants both work |
| 3 | Disposable ECG electrodes (Ag/AgCl) | The wet-gel type. Dry electrodes give very poor SNR |
| 1 | AD8232 lead cable (3.5 mm stereo jack to snap connectors) | Comes with most breakouts |
| 1 | USB cable (micro-USB or USB-C depending on board) | For power + Serial |
| ~ | Jumper wires | Female-to-female for breakout-to-DevKit |
| 1 | Breadboard | Optional; the AD8232 has 0.1" pin headers |

## Pin map

```
+---------+                              +---------+
| AD8232  |                              | ESP32   |
|         |                              | DevKit  |
|  OUTPUT +------------------------------> GPIO 34 |   (ADC1_CH6)
|                                        |         |
|     LO+ +------------------------------> GPIO 32 |
|     LO- +------------------------------> GPIO 33 |
|                                        |         |
|     3.3V+------------------------------> 3V3     |
|     GND +------------------------------> GND     |
+---------+                              +---------+
```

> **Important:** GPIO 34 on the ESP32 is **input-only** and has no internal
> pull-up. That's exactly what we want for a clean ADC input.

## Electrode placement

The AD8232 is a **single-lead** monitor, so we use a modified Lead I
configuration:

| Electrode | Lead label | Position |
|---|---|---|
| Red    | RA (right arm) | Right shoulder, just under the collarbone |
| Yellow | LA (left arm)  | Left shoulder, just under the collarbone |
| Green  | RL (right leg, "reference") | Right hip, just above the iliac crest |

Tips for good signal quality:

- **Shave** electrode sites if hairy. Hair = high impedance = noise.
- **Wipe** the skin with isopropyl alcohol; let it dry. Removes oils that
  block the wet gel from making contact.
- Use **fresh** electrodes. The wet gel dries out within a couple of hours
  of opening the packet.
- **Keep still** during recording. EMG (muscle electrical activity) shows
  up as 20-300 Hz garbage that even our notch can't kill.

## Power & ground

- Power the ESP32 from a **laptop USB port**, *not* a wall charger.
  Cheap switch-mode supplies inject 50 Hz mains hum through the ground
  reference and dominate the ECG signal.
- A **single ground reference** between AD8232 GND and ESP32 GND is
  mandatory. Multiple ground paths create loops that pick up everything.

## Bring-up gotchas (what bit us)

### 1. ADC saturating at ~3800 instead of ~2048

**Symptom:** The signal looked like Figure 1 of the report - a slow
50 Hz-like sinusoid with no QRS, centered way above mid-rail.

**Root cause:** The LO+ / LO- "leads-off" lines were miswired (we had
them on the wrong ESP32 pins). The AD8232 saw a floating reference and
the output rail-pushed.

**Fix:** Triple-check that LO+ goes to a digital-capable pin and that
the firmware reads it as `INPUT` (no pull-up). Once the lines are right,
the ADC centers on 2048 = mid-rail. The `ADC_CENTER` macro in
`firmware/esp32_ecg/config.h` was updated from 3800 to 2048 after this fix.

### 2. Choppy serial output

**Symptom:** Visible gaps in the Processing IDE plot at high signal rates.

**Root cause:** Without any delay in the Arduino loop, `Serial.println`
saturates the USB CDC buffer and `analogRead` returns stale values.

**Fix:** A single `delay(1)` per loop iteration provides ~200-300 Hz
sustained sample rate - more than enough for ECG (we only need ~125 Hz
per Nyquist to capture our 40 Hz upper bandpass edge).

### 3. 50 Hz hum is still visible

**Symptom:** Even after the IIR notch, the waveform has a fast wobble.

**Likely causes:**
- The notch is at 50 Hz but your local mains is actually 49.8 Hz or
  50.2 Hz. The Q = 30 design has only a ~1.6 Hz -3 dB bandwidth.
  &rarr; Lower the Q (e.g. to 20) for a wider notch.
- The 50 Hz coupling is coming through a different path (laptop fan,
  nearby fluorescent light, wall wart). Move further away from RF noise
  sources.
- One of your electrodes has a dried-out gel patch. Replace it.
