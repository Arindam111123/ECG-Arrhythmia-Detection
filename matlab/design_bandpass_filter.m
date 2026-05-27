function [b, info] = design_bandpass_filter(Fs)
% DESIGN_BANDPASS_FILTER  FIR bandpass filter for ECG (0.5 - 40 Hz)
%
%   [B, INFO] = DESIGN_BANDPASS_FILTER(Fs) returns the FIR coefficients B
%   (numerator only; denominator is 1 for FIR) of a linear-phase
%   Hamming-windowed bandpass filter targeting the diagnostic ECG band.
%
%   Why linear-phase FIR (not a lower-order IIR)?
%   -----------------------------------------------
%   ECG morphology is judged by the *shape* and *timing* of the P-QRS-T
%   complex. IIR filters introduce frequency-dependent group delay that
%   distorts the QRS shape and shifts P/T waves by different amounts -
%   a clinical no-no. FIR keeps phase linear so all components are
%   delayed by exactly N/2 samples (a fixed offset, easy to compensate).
%
%   The order is kept at 100 to give ~1 Hz transition band at 250 Hz Fs
%   without overwhelming the ESP32 (101 MAC ops/sample ~ 25k ops/sec).

    % --- Design parameters --------------------------------------------
    Fc_low  = 0.5;   % Lower cutoff (Hz) - kills baseline wander
    Fc_high = 40;    % Upper cutoff (Hz) - kills EMG/HF noise
    N       = 100;   % Filter order (=> 101 taps)

    % --- Normalize cutoffs to Nyquist ---------------------------------
    Wn = [Fc_low, Fc_high] / (Fs / 2);

    % --- Hamming-windowed FIR (fir1) ----------------------------------
    % fir1 uses the windowed-sinc design method; Hamming gives ~53 dB
    % stopband attenuation which is plenty for ECG.
    b = fir1(N, Wn, 'bandpass', hamming(N + 1));

    % --- Metadata -----------------------------------------------------
    info.order      = N;
    info.taps       = N + 1;
    info.Fc_low_hz  = Fc_low;
    info.Fc_high_hz = Fc_high;
    info.window     = 'hamming';
    info.group_delay_samples = N / 2;
    info.group_delay_ms      = (N / 2) / Fs * 1000;
end
