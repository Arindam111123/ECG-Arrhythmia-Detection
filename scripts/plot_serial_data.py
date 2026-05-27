"""
plot_serial_data.py
===================
Log live data from the ESP32 over USB Serial to a CSV file and
optionally plot a rolling 10-second window in real time.

Usage:
    python plot_serial_data.py --port /dev/ttyUSB0 --out ecg.csv
    python plot_serial_data.py --port COM4 --no-plot

Requires:
    pip install pyserial matplotlib
"""

import argparse
import csv
import sys
import time
from collections import deque

import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0",
                    help="Serial port (e.g. /dev/ttyUSB0, COM4).")
    ap.add_argument("--baud", type=int, default=9600,
                    help="Baud rate (must match firmware).")
    ap.add_argument("--out", default="ecg_log.csv",
                    help="Where to write the CSV log.")
    ap.add_argument("--window-s", type=float, default=10.0,
                    help="Plot window length in seconds.")
    ap.add_argument("--fs", type=int, default=250,
                    help="Effective ESP32 sample rate.")
    ap.add_argument("--no-plot", action="store_true",
                    help="Just log to CSV, skip the plot.")
    args = ap.parse_args()

    try:
        port = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Could not open {args.port}: {e}", file=sys.stderr)
        return 1

    print(f"Logging to {args.out} (Ctrl+C to stop).")
    csv_f = open(args.out, "w", newline="")
    writer = csv.writer(csv_f)
    writer.writerow(["t_s", "value", "tag"])

    t0 = time.time()
    buf_n = int(args.window_s * args.fs)
    times  = deque(maxlen=buf_n)
    values = deque(maxlen=buf_n)

    fig, ax = None, None
    line = None
    if not args.no_plot:
        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 4))
        line, = ax.plot([], [], color="#2ca02c", linewidth=1)
        ax.set_xlim(-args.window_s, 0)
        ax.grid(alpha=0.3)
        ax.set_xlabel("time (s, relative)")
        ax.set_ylabel("envelope value")
        ax.set_title("ESP32 ECG live")

    try:
        while True:
            raw = port.readline().decode(errors="replace").strip()
            if not raw:
                continue
            now = time.time() - t0

            if raw.startswith("#"):
                writer.writerow([f"{now:.3f}", "", raw])
                print(raw)
                continue

            if raw == "!":
                writer.writerow([f"{now:.3f}", "", "LEADS_OFF"])
                continue

            try:
                v = float(raw)
            except ValueError:
                continue

            times.append(now)
            values.append(v)
            writer.writerow([f"{now:.3f}", v, ""])

            if line is not None and len(times) > 1:
                t_rel = [t - times[-1] for t in times]
                line.set_data(t_rel, list(values))
                ax.set_ylim(min(values) - 1, max(values) + 1)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        csv_f.close()
        port.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
