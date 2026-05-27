function verify_filters_synthetic(b_bp, b_notch, a_notch, Fs)
% VERIFY_FILTERS_SYNTHETIC  Builds a synthetic ECG-like signal plus
% baseline drift and 50 Hz mains hum, then runs it through the same
% filter cascade the ESP32 uses. Plots before/after so we can sanity
% check the design without touching real hardware.

    duration = 6;                          % seconds
    t = (0 : 1/Fs : duration - 1/Fs).';
    N = length(t);

    % --- Synthetic ECG (sum of Gaussians) -----------------------------
    % Heart rate 75 bpm => RR = 0.8 s. Each beat is a P-Q-R-S-T cluster.
    hr_bpm = 75;
    rr     = 60 / hr_bpm;
    beats  = floor(duration / rr);
    ecg    = zeros(N, 1);

    % Gaussian (amplitude, center offset, width) for each wave
    waves = [ ...
        0.10, -0.20, 0.025;   % P
       -0.15, -0.05, 0.010;   % Q
        1.00,  0.00, 0.012;   % R
       -0.30,  0.05, 0.012;   % S
        0.30,  0.30, 0.040];  % T

    for k = 0:beats
        c = k * rr;
        for w = 1:size(waves, 1)
            A  = waves(w, 1);
            mu = c + waves(w, 2);
            s  = waves(w, 3);
            ecg = ecg + A * exp(-((t - mu).^2) / (2 * s^2));
        end
    end

    % --- Contaminate with realistic noise ----------------------------
    baseline = 0.4 * sin(2 * pi * 0.3 * t);          % respiratory drift
    mains    = 0.5 * sin(2 * pi * 50  * t);          % powerline hum
    emg      = 0.05 * randn(N, 1);                   % muscle / thermal

    noisy = ecg + baseline + mains + emg;

    % --- Run the firmware filter chain in MATLAB ---------------------
    notched  = filter(b_notch, a_notch, noisy);
    filtered = filter(b_bp,    1,       notched);

    % --- Plot --------------------------------------------------------
    figure('Name', 'Filter Verification on Synthetic ECG', 'Color', 'w', ...
           'Position', [120, 120, 1100, 700]);

    subplot(3, 1, 1);
    plot(t, ecg, 'LineWidth', 1.2); grid on; xlim([0, 4]);
    title('Clean synthetic ECG (ground truth)');
    ylabel('Amplitude (mV)');

    subplot(3, 1, 2);
    plot(t, noisy, 'Color', [0.7 0.2 0.2], 'LineWidth', 1.0); grid on; xlim([0, 4]);
    title('Noisy input: ECG + baseline drift + 50 Hz hum + EMG');
    ylabel('Amplitude (mV)');

    subplot(3, 1, 3);
    plot(t, filtered, 'Color', [0.1 0.5 0.2], 'LineWidth', 1.2); grid on; xlim([0, 4]);
    title('Output after IIR notch + FIR bandpass cascade');
    xlabel('Time (s)'); ylabel('Amplitude (mV)');
end
