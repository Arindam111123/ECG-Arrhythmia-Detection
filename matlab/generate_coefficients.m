%% generate_coefficients.m
% ------------------------------------------------------------------
% Master script: designs the FIR bandpass and IIR notch filters used
% by the ESP32 firmware and exports their coefficients to a C header.
%
% This is the "Recipe" stage of the pipeline. The C++ firmware on the
% ESP32 is the "Chef" that consumes these coefficients.
%
% Project: Heart Signals and Arrhythmia Detection (BEC502, 2025-26)
% ------------------------------------------------------------------

clc; clear; close all;

%% Global sampling parameters
% The ESP32 main loop uses delay(1) (~1 ms) plus Serial.write overhead.
% Effective sample rate measured on hardware was ~250 Hz, which is the
% de-facto standard for low-cost ambulatory ECG.
Fs = 250;                    % Sampling frequency (Hz)

fprintf('=========================================================\n');
fprintf('  ECG Filter Coefficient Generator\n');
fprintf('  Target: ESP32 / Arduino C++ firmware\n');
fprintf('  Fs = %d Hz\n', Fs);
fprintf('=========================================================\n\n');

%% 1. FIR Bandpass Filter (0.5 Hz - 40 Hz)
% Removes:
%   - Baseline wander (respiration, electrode motion) below 0.5 Hz
%   - High-frequency EMG / thermal noise above 40 Hz
% Preserves:
%   - P, QRS, T components (the diagnostic ECG band)
fprintf('[1/2] Designing FIR bandpass (0.5 Hz - 40 Hz)...\n');
[b_bp, fir_info] = design_bandpass_filter(Fs);
fprintf('      Order : %d (%d taps)\n', fir_info.order, length(b_bp));
fprintf('      Type  : Linear-phase FIR, Hamming window\n\n');

%% 2. IIR Notch Filter (50 Hz - India mains)
% Removes powerline interference (50 Hz in India / EU, 60 Hz in US).
% Change F0 below if deploying in a 60 Hz region.
fprintf('[2/2] Designing IIR notch (50 Hz, Q = 30)...\n');
F0_mains = 50;
Q_notch  = 30;
[b_notch, a_notch] = design_notch_filter(Fs, F0_mains, Q_notch);
fprintf('      Topology: Second-order biquad (Direct Form II)\n');
fprintf('      -3 dB BW: %.2f Hz\n\n', F0_mains / Q_notch);

%% 3. Plot magnitude responses for the report figures
plot_filter_responses(b_bp, b_notch, a_notch, Fs);

%% 4. Export to C header that the ESP32 firmware includes directly
out_path = fullfile('..', 'firmware', 'esp32_ecg', 'filter_coefficients.h');
export_coefficients_to_c(b_bp, b_notch, a_notch, Fs, F0_mains, out_path);
fprintf('Coefficients written to:\n  %s\n\n', out_path);

%% 5. Verify with a synthetic ECG-like signal
verify_filters_synthetic(b_bp, b_notch, a_notch, Fs);

fprintf('Done.\n');
