function plot_filter_responses(b_bp, b_notch, a_notch, Fs)
% PLOT_FILTER_RESPONSES  Visualize the magnitude/phase response of both
% the FIR bandpass and the IIR notch on the same figure for the report.

    Npoints = 4096;

    % --- Bandpass response -------------------------------------------
    [H_bp, f_bp] = freqz(b_bp, 1, Npoints, Fs);

    % --- Notch response ----------------------------------------------
    [H_nt, f_nt] = freqz(b_notch, a_notch, Npoints, Fs);

    % --- Combined cascade --------------------------------------------
    % This is what the signal actually sees on the ESP32.
    H_total = H_bp .* H_nt;

    figure('Name', 'ECG Filter Pipeline Response', 'Color', 'w', ...
           'Position', [100, 100, 1000, 700]);

    % FIR bandpass magnitude
    subplot(3, 1, 1);
    plot(f_bp, 20*log10(abs(H_bp) + eps), 'LineWidth', 1.4);
    grid on; xlim([0, Fs/2]); ylim([-80, 5]);
    xlabel('Frequency (Hz)'); ylabel('Magnitude (dB)');
    title('FIR Bandpass 0.5 - 40 Hz (Hamming, order 100)');
    xline(0.5, '--r'); xline(40, '--r');

    % IIR notch magnitude
    subplot(3, 1, 2);
    plot(f_nt, 20*log10(abs(H_nt) + eps), 'LineWidth', 1.4);
    grid on; xlim([0, Fs/2]); ylim([-60, 5]);
    xlabel('Frequency (Hz)'); ylabel('Magnitude (dB)');
    title('IIR Notch 50 Hz (Q = 30)');
    xline(50, '--r');

    % Cascaded response
    subplot(3, 1, 3);
    plot(f_bp, 20*log10(abs(H_total) + eps), 'LineWidth', 1.4, 'Color', [0.2 0.6 0.2]);
    grid on; xlim([0, Fs/2]); ylim([-80, 5]);
    xlabel('Frequency (Hz)'); ylabel('Magnitude (dB)');
    title('Cascaded Response (what the ECG signal actually experiences)');
    xline(0.5, '--r'); xline(40, '--r'); xline(50, '--r');

    sgtitle('ECG Signal Conditioning Filter Pipeline', 'FontWeight', 'bold');
end
