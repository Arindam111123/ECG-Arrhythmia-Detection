// ============================================================
//  config.h
//  Pinout, sample rate, and tuning constants for the ESP32
//  ECG firmware. All "magic numbers" referenced in the report
//  live here so they're easy to find and tune.
// ============================================================
#ifndef ECG_CONFIG_H
#define ECG_CONFIG_H

// ---------- Pinout ------------------------------------------
// AD8232  ----  ESP32 DevKit V1
// OUTPUT  ---->  GPIO 34   (ADC1_CH6, input-only - perfect for analog)
// LO+     ---->  GPIO 32
// LO-     ---->  GPIO 33
// 3.3V    ---->  3V3
// GND     ---->  GND
#define PIN_ECG       34
#define PIN_LO_PLUS   32
#define PIN_LO_MINUS  33

// ---------- Serial ------------------------------------------
// 9600 baud per the project spec. Higher rates work too, but
// 9600 is what the Processing sketch is configured for.
#define SERIAL_BAUD   9600

// ---------- Sampling ----------------------------------------
// delay(1) + analogRead + Serial.println gives ~200..300 Hz
// in practice on the ESP32 at 240 MHz with the default core.
#define LOOP_DELAY_MS 1

// ---------- ADC offset --------------------------------------
// 12-bit ADC mid-rail. The very first bring-up had this set to
// 3800 by accident because the leads-off lines were miswired
// and the front-end was floating at the high rail. After the
// fix the correct value is 2048.
#define ADC_CENTER    2048

// ---------- DC blocker --------------------------------------
// 1st-order IIR high-pass coefficient. Cutoff:
//   fc = Fs * (1 - alpha) / (2*pi)
// At Fs = 250 Hz and alpha = 0.9874, fc ~= 0.5 Hz (the report's
// lower bandpass edge). Closer to 1.0 = lower cutoff, sharper
// but slower transient settling.
#define DC_BLOCK_ALPHA 0.9874f

// ---------- Display scaling ---------------------------------
// The envelope can take large numeric values depending on
// electrode contact quality. We divide by SIG_SCALE and add
// ENV_BASELINE so the plotted waveform sits in the same
// 40..43 range observed in the project's Serial Plotter
// captures (see Figure 1 in the report).
#define SIG_SCALE     50.0f
#define ENV_BASELINE  40.0f

// ---------- Peak detection ----------------------------------
// PEAK_THRESHOLD = 41.5 was chosen by visual inspection of the
// noise floor (~40.0) versus R-peak amplitude (~43.0). The
// hysteresis below it stops a single noisy QRS being counted
// as multiple beats.
#define PEAK_THRESHOLD  41.5f
#define HYSTERESIS      0.5f

// ---------- Physiological gates -----------------------------
// 200 BPM upper bound rejects double-detection of the same QRS.
//  30 BPM lower bound rejects motion-induced misses.
#define RR_MIN_MS      300     // -> 200 BPM
#define RR_MAX_MS     2000     // ->  30 BPM

#endif // ECG_CONFIG_H
