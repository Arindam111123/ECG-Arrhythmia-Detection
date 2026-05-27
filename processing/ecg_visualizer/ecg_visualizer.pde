/* ============================================================
 *  ecg_visualizer.pde   (Processing 4.x)
 *
 *  Real-time ECG waveform plot + BPM display, fed over USB Serial
 *  from the ESP32 running esp32_ecg.ino.
 *
 *  Threshold = 620.0 (set during signal conditioning, see Section
 *  3.3 of the project report - this value sits comfortably above
 *  the noise floor but below R-peak amplitude on the raw scale
 *  this sketch receives.)
 *
 *  Baud rate = 9600 to match the firmware.
 * ============================================================ */

import processing.serial.*;

Serial port;

// ---- Configuration ------------------------------------------
final int   BAUD       = 9600;
final float THRESHOLD  = 620.0;   // R-peak detection level (Processing scale)
final int   BEATS_LEN  = 500;     // moving-average window for BPM
final int   PLOT_PAD   = 60;      // pixels of margin around the plot

// Plot Y-range matches Figure 2 in the report (320..540 region).
final float Y_MIN = 300.0;
final float Y_MAX = 560.0;

// ---- State --------------------------------------------------
float[] samples;        // ring buffer of plot points
int     writeIdx = 0;

// BPM tracking
float[] beats = new float[BEATS_LEN];
int     beatIdx = 0;
int     beatCount = 0;

float lastValue = 0;
boolean armed = true;          // for rising-edge threshold cross
int     lastBeatTimeMs = 0;
float   displayedBpm = 0;
String  status = "WAITING...";

// =====================================================================
//  setup
// =====================================================================
void setup() {
    size(1200, 600);
    smooth();
    background(20);

    samples = new float[width - 2 * PLOT_PAD];
    for (int i = 0; i < samples.length; i++) samples[i] = (Y_MIN + Y_MAX) / 2.0;

    // List serial ports and try to open the first one. On a real
    // setup you'd pick the one matching your ESP32 ("/dev/ttyUSB0",
    // "COM4", etc.). Adjust the index if needed.
    println("Available serial ports:");
    println(Serial.list());

    if (Serial.list().length > 0) {
        port = new Serial(this, Serial.list()[0], BAUD);
        port.bufferUntil('\n');
    } else {
        println("No serial ports found - running in demo (no data).");
    }

    textFont(createFont("Menlo", 14));
}

// =====================================================================
//  draw  - called ~60 fps
// =====================================================================
void draw() {
    background(18);

    drawGrid();
    drawThresholdLine();
    drawWaveform();
    drawHud();
}

// =====================================================================
//  serialEvent  - one line of CSV per ECG sample from the ESP32
// =====================================================================
void serialEvent(Serial p) {
    String line = p.readStringUntil('\n');
    if (line == null) return;
    line = trim(line);
    if (line.length() == 0) return;

    // Diagnostic / banner lines from the firmware start with '#'.
    if (line.charAt(0) == '#') {
        // Parse out BPM if present
        int idx = line.indexOf("BPM=");
        if (idx >= 0) {
            String rest = line.substring(idx + 4);
            // pull leading float
            int end = 0;
            while (end < rest.length() && (Character.isDigit(rest.charAt(end)) || rest.charAt(end) == '.')) end++;
            if (end > 0) {
                try { displayedBpm = Float.parseFloat(rest.substring(0, end)); }
                catch (Exception e) { /* ignore */ }
            }
        }
        return;
    }

    // Leads-off sentinel
    if (line.equals("!")) {
        status = "LEADS OFF";
        return;
    }

    float v;
    try {
        v = Float.parseFloat(line);
    } catch (Exception e) {
        return;
    }

    // Map firmware envelope domain (~40 baseline, peaks ~43) into the
    // 300..560 plot domain so Figure 2 of the report is reproduced.
    // (gain of 50 + offset 100.)
    float plotV = (v - 40.0) * 50.0 + 400.0;

    samples[writeIdx] = plotV;
    writeIdx = (writeIdx + 1) % samples.length;

    // R-peak detection (rising-edge threshold cross with debounce).
    int now = millis();
    if (armed && plotV > THRESHOLD) {
        armed = false;
        if (lastBeatTimeMs > 0) {
            int rr = now - lastBeatTimeMs;
            if (rr > 300 && rr < 2000) {
                float bpm = 60000.0 / rr;
                pushBeat(bpm);
                updateStatus(bpm);
            }
        }
        lastBeatTimeMs = now;
    } else if (!armed && plotV < THRESHOLD - 10) {
        armed = true;   // re-arm once safely below threshold
    }

    lastValue = plotV;
}

// =====================================================================
//  pushBeat - circular buffer + running average
// =====================================================================
void pushBeat(float bpm) {
    beats[beatIdx] = bpm;
    beatIdx = (beatIdx + 1) % BEATS_LEN;
    if (beatCount < BEATS_LEN) beatCount++;

    float s = 0;
    for (int i = 0; i < beatCount; i++) s += beats[i];
    displayedBpm = s / beatCount;
}

// =====================================================================
//  updateStatus - classify the most recent rate
// =====================================================================
void updateStatus(float bpm) {
    if (bpm > 100)      status = "TACHYCARDIA  (>100 BPM)";
    else if (bpm < 60)  status = "BRADYCARDIA  (<60 BPM)";
    else                status = "NORMAL";
}

// =====================================================================
//  drawGrid - light medical-paper style grid
// =====================================================================
void drawGrid() {
    stroke(40, 80, 40);
    strokeWeight(1);
    // vertical lines every 40 px
    for (int x = PLOT_PAD; x < width - PLOT_PAD; x += 40) {
        line(x, PLOT_PAD, x, height - PLOT_PAD);
    }
    // horizontal lines every 40 px
    for (int y = PLOT_PAD; y < height - PLOT_PAD; y += 40) {
        line(PLOT_PAD, y, width - PLOT_PAD, y);
    }
    noFill();
    stroke(80, 200, 80);
    strokeWeight(1);
    rect(PLOT_PAD, PLOT_PAD, width - 2 * PLOT_PAD, height - 2 * PLOT_PAD);
}

// =====================================================================
//  drawThresholdLine
// =====================================================================
void drawThresholdLine() {
    float y = map(THRESHOLD, Y_MIN, Y_MAX, height - PLOT_PAD, PLOT_PAD);
    stroke(255, 80, 80, 200);
    strokeWeight(1);
    line(PLOT_PAD, y, width - PLOT_PAD, y);
    fill(255, 80, 80);
    noStroke();
    text("R-peak threshold (" + nf(THRESHOLD, 0, 1) + ")", width - PLOT_PAD - 220, y - 6);
}

// =====================================================================
//  drawWaveform
// =====================================================================
void drawWaveform() {
    stroke(80, 230, 120);
    strokeWeight(1.6);
    noFill();
    beginShape();
    for (int i = 0; i < samples.length; i++) {
        int idx = (writeIdx + i) % samples.length;
        float x = PLOT_PAD + i;
        float y = map(samples[idx], Y_MIN, Y_MAX, height - PLOT_PAD, PLOT_PAD);
        y = constrain(y, PLOT_PAD, height - PLOT_PAD);
        vertex(x, y);
    }
    endShape();
}

// =====================================================================
//  drawHud - BPM + status overlay
// =====================================================================
void drawHud() {
    noStroke();
    fill(20, 220);
    rect(PLOT_PAD + 4, PLOT_PAD + 4, 280, 90);

    fill(220);
    textSize(14);
    text("HEART SIGNALS & ARRHYTHMIA DETECTION", PLOT_PAD + 14, PLOT_PAD + 22);

    textSize(32);
    if (status.equals("NORMAL"))            fill(120, 230, 140);
    else if (status.equals("LEADS OFF"))    fill(220, 220, 80);
    else if (status.equals("WAITING..."))   fill(180);
    else                                    fill(230, 100, 100);
    text(nf(displayedBpm, 0, 0) + " BPM", PLOT_PAD + 14, PLOT_PAD + 60);

    textSize(13);
    text(status, PLOT_PAD + 14, PLOT_PAD + 82);
}
