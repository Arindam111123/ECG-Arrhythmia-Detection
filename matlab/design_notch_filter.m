function [b, a] = design_notch_filter(Fs, F0, Q)
% DESIGN_NOTCH_FILTER  Second-order IIR notch for powerline removal.
%
%   [B, A] = DESIGN_NOTCH_FILTER(Fs, F0, Q) returns numerator B and
%   denominator A of a biquad notch tuned to F0 Hz with quality factor Q.
%   Typical use is to kill 50 Hz (India / EU) or 60 Hz (US) mains hum.
%
%   Why IIR (not FIR) for the notch?
%   --------------------------------
%   A sharp narrowband notch built as FIR would need thousands of taps
%   (a 50 Hz notch at 250 Hz Fs requires very fine frequency resolution).
%   A second-order IIR biquad achieves the same notch depth with only
%   5 multiplies/sample. Phase distortion is localized to a narrow band
%   right around F0, well outside any ECG morphological information,
%   so the clinical waveform is preserved.
%
%   Inputs
%     Fs : sampling frequency (Hz)
%     F0 : notch center frequency (Hz). 50 for India, 60 for US.
%     Q  : quality factor. Higher Q = narrower notch. 30 is a good default;
%          tight enough to leave the 40 Hz upper band of ECG untouched,
%          wide enough to catch small mains drift.
%
%   Outputs
%     b  : numerator coefficients [b0 b1 b2]
%     a  : denominator coefficients [1  a1 a2]

    if nargin < 2, F0 = 50; end
    if nargin < 3, Q  = 30; end

    % Normalized notch frequency (Nyquist = 1)
    Wn = F0 / (Fs / 2);

    % Bandwidth at -3 dB (used by iirnotch as relative BW)
    BW = Wn / Q;

    % Use Signal Processing Toolbox iirnotch if available, otherwise
    % synthesize the biquad coefficients manually.
    if exist('iirnotch', 'file') == 2
        [b, a] = iirnotch(Wn, BW);
    else
        % Manual biquad notch (RBJ audio EQ cookbook formulas)
        w0    = 2 * pi * F0 / Fs;
        alpha = sin(w0) / (2 * Q);

        b0 =  1;
        b1 = -2 * cos(w0);
        b2 =  1;
        a0 =  1 + alpha;
        a1 = -2 * cos(w0);
        a2 =  1 - alpha;

        b = [b0, b1, b2] / a0;
        a = [1,  a1, a2] / a0;
    end
end
