"""
VASI — Jarvis UI Overlay v3.0
3D Plasma Orb — glowing sphere with surface texture and pulsing energy
"""

import tkinter as tk
import math
import os
import threading
import time
import random

# =============================================================================
# CONFIGURATION
# =============================================================================

STATE_FILE  = "vasi_state.txt"
UPDATE_MS   = 16
CANVAS_SIZE = 160
CENTER      = CANVAS_SIZE // 2
RADIUS      = 52

COLORS = {
    "passive": {
        "outer_glow": ["#001133", "#002255", "#003377"],
        "rim":        "#1155aa",
        "surface":    "#0a2a6e",
        "bubble":     "#1a4499",
        "core":       "#050d2a",
        "text":       "#1a3a77",
    },
    "listening": {
        "outer_glow": ["#001a44", "#0033aa", "#0055dd"],
        "rim":        "#2277ff",
        "surface":    "#0a40cc",
        "bubble":     "#3388ff",
        "core":       "#020a33",
        "text":       "#2277ff",
    },
    "speaking": {
        "outer_glow": ["#002255", "#0044cc", "#00aaff"],
        "rim":        "#00ccff",
        "surface":    "#0055cc",
        "bubble":     "#00eeff",
        "core":       "#001122",
        "text":       "#00ddff",
    },
}

PULSE_SPEED = {
    "passive":   0.02,
    "listening": 0.05,
    "speaking":  0.12,
}


# =============================================================================
# STATE READER
# =============================================================================

class StateReader:
    def __init__(self) -> None:
        self._state   = "passive"
        self._lock    = threading.Lock()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while self._running:
            try:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE, "r") as f:
                        raw = f.read().strip().lower()
                    if raw in COLORS:
                        with self._lock:
                            self._state = raw
            except Exception:
                pass
            time.sleep(0.08)

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def stop(self) -> None:
        self._running = False


# =============================================================================
# BUBBLE
# =============================================================================

class Bubble:
    def __init__(self) -> None:
        self.theta = 0.0
        self.phi   = 0.0
        self.size  = 2.0
        self.life  = 0.0
        self.speed = 0.01
        self.drift = 0.0
        self.reset()

    def reset(self) -> None:
        self.theta = random.uniform(0, 2 * math.pi)
        self.phi   = random.uniform(0.1, math.pi - 0.1)
        self.size  = random.uniform(2, 6)
        self.life  = random.uniform(0, 1)
        self.speed = random.uniform(0.005, 0.02)
        self.drift = random.uniform(-0.01, 0.01)

    def update(self) -> None:
        self.life  += self.speed
        self.theta += self.drift
        if self.life >= 1.0:
            self.reset()
            self.life = 0.0

    def brightness(self) -> float:
        return math.sin(self.life * math.pi)

    def screen_pos(self, cx: int, cy: int, r: float) -> tuple:
        x     = cx + r * math.sin(self.phi) * math.cos(self.theta)
        y     = cy + r * math.sin(self.phi) * math.sin(self.theta) * 0.5
        depth = 0.3 + 0.7 * (0.5 + 0.5 * math.cos(self.phi))
        return x, y, depth


# =============================================================================
# EDGE PARTICLE
# =============================================================================

class EdgeParticle:
    def __init__(self, index: int, total: int) -> None:
        self.base_angle  = (2 * math.pi * index) / total
        self.wave_offset = random.uniform(0, 2 * math.pi)
        self.wave_speed  = random.uniform(0.6, 1.4)
        self.size        = random.uniform(1.5, 4.0)

    def position(self, t: float, r: float, amp: float,
                 spin: float) -> tuple:
        angle  = self.base_angle + spin
        wave   = math.sin(t * self.wave_speed + self.wave_offset)
        radius = r + amp * wave
        x      = CENTER + radius * math.cos(angle)
        y      = CENTER + radius * math.sin(angle) * 0.55
        bright = 0.4 + 0.5 * (0.5 + 0.5 * math.cos(angle - spin))
        return x, y, bright


# =============================================================================
# OVERLAY
# =============================================================================

class VASIOverlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root    = root
        self.reader  = StateReader()
        self.t       = 0.0
        self.spin    = 0.0
        self.pulse   = 0.0
        self._drag_x = 0
        self._drag_y = 0

        self.bubbles = [Bubble() for _ in range(35)]
        for b in self.bubbles:
            b.life = random.uniform(0, 1)

        self.edge_particles = [EdgeParticle(i, 120) for i in range(120)]

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#010101")
        self.root.configure(bg="#010101")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = sw - CANVAS_SIZE - 20
        y  = sh - CANVAS_SIZE - 60
        self.root.geometry(f"{CANVAS_SIZE}x{CANVAS_SIZE}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_SIZE, height=CANVAS_SIZE,
            bg="#010101", highlightthickness=0
        )
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>",     self._drag_move)

        self._animate()

    def _drag_start(self, event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_move(self, event) -> None:
        self.root.geometry(
            f"+{event.x_root - self._drag_x}"
            f"+{event.y_root - self._drag_y}")

    def _scale_color(self, hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        if r == 0 and g == 0 and b == 0:
            return "#010101"
        return f"#{r:02x}{g:02x}{b:02x}"

    def _blend(self, c1: str, c2: str, t: float) -> str:
        c1 = c1.lstrip("#")
        c2 = c2.lstrip("#")
        r  = int(int(c1[0:2], 16) * (1-t) + int(c2[0:2], 16) * t)
        g  = int(int(c1[2:4], 16) * (1-t) + int(c2[2:4], 16) * t)
        b  = int(int(c1[4:6], 16) * (1-t) + int(c2[4:6], 16) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animate(self) -> None:
        state = self.reader.state
        col   = COLORS[state]
        spd   = PULSE_SPEED[state]

        self.t     += spd * 2
        self.spin  += spd * 0.4
        self.pulse += spd

        c  = self.canvas
        cx = CENTER
        cy = CENTER
        c.delete("all")

        # ── Outer atmosphere glow ─────────────────────────────────────────
        for i, glow_col in enumerate(reversed(col["outer_glow"])):
            r = RADIUS + 30 - i * 8
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          fill=glow_col, outline="")

        # ── Main sphere gradient ──────────────────────────────────────────
        steps = 28
        for i in range(steps):
            frac = i / steps
            r    = int(RADIUS * (1 - frac * 0.95))
            if frac < 0.3:
                blend_t = frac / 0.3
                color   = self._blend(col["rim"], col["surface"], blend_t)
                bright  = 1.0 - frac * 0.5
            elif frac < 0.7:
                blend_t = (frac - 0.3) / 0.4
                color   = self._blend(col["surface"], col["core"], blend_t)
                bright  = 0.85 - frac * 0.6
            else:
                color  = col["core"]
                bright = 0.2
            color = self._scale_color(color, bright)
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          fill=color, outline="")

        # ── Wavy rim distortion ───────────────────────────────────────────
        num_rim = 300
        rim_amp = 7 + 4 * math.sin(self.pulse)
        for i in range(num_rim):
            angle   = (2 * math.pi * i) / num_rim
            wave    = math.sin(angle * 3 + self.t)       * rim_amp * 0.5
            wave   += math.sin(angle * 5 + self.t * 1.5) * rim_amp * 0.35
            wave   += math.sin(angle * 8 + self.t * 0.7) * rim_amp * 0.2
            r       = RADIUS + wave
            px      = cx + r * math.cos(angle)
            py      = cy + r * math.sin(angle) * 0.92
            bright  = 0.6 + 0.4 * math.sin(angle * 3 + self.t)
            rim_col = self._scale_color(col["rim"], bright)
            sz      = 2.2 + 1.2 * bright
            c.create_oval(px-sz, py-sz, px+sz, py+sz,
                          fill=rim_col, outline="")

        # ── Second outer wave layer ───────────────────────────────────────
        for i in range(150):
            angle   = (2 * math.pi * i) / 150
            wave    = math.sin(angle * 4 + self.t * 1.2 + 1.0) * (rim_amp * 0.6)
            wave   += math.sin(angle * 6 + self.t * 0.9)        * (rim_amp * 0.3)
            r       = RADIUS + 4 + wave
            px      = cx + r * math.cos(angle)
            py      = cy + r * math.sin(angle) * 0.92
            bright  = 0.3 + 0.3 * math.sin(angle * 4 + self.t * 1.1)
            rim_col = self._scale_color(col["bubble"], bright)
            sz      = 1.5
            c.create_oval(px-sz, py-sz, px+sz, py+sz,
                          fill=rim_col, outline="")

        # ── Surface bubbles ───────────────────────────────────────────────
        for b in self.bubbles:
            b.update()
            bx, by, depth = b.screen_pos(cx, cy, RADIUS * 0.75)
            bright = b.brightness() * depth
            if bright < 0.05:
                continue
            bub_col = self._scale_color(col["bubble"], bright)
            sz      = b.size * depth
            c.create_oval(bx-sz, by-sz, bx+sz, by+sz,
                          fill=bub_col, outline="")

        # ── Edge particle ring ────────────────────────────────────────────
        edge_amp = 8 + 5 * math.sin(self.pulse * 1.5)
        for p in self.edge_particles:
            px, py, bright = p.position(
                self.t, RADIUS + 4, edge_amp, self.spin)
            if bright < 0.1:
                continue
            pcol = self._scale_color(col["bubble"], bright)
            sz   = p.size * bright * 0.8
            c.create_oval(px-sz, py-sz, px+sz, py+sz,
                          fill=pcol, outline="")

        # ── Inner hollow core ─────────────────────────────────────────────
        inner_r = int(16 + 2 * math.sin(self.pulse * 2))
        c.create_oval(cx-inner_r, cy-inner_r,
                      cx+inner_r, cy+inner_r,
                      fill=col["core"], outline="")

        # ── Specular highlights ───────────────────────────────────────────
        hl1_x   = cx - RADIUS * 0.28
        hl1_y   = cy - RADIUS * 0.32
        hl1_r   = int(12 + 2 * math.sin(self.pulse))
        hl1_col = self._scale_color(col["bubble"], 0.7)
        c.create_oval(hl1_x-hl1_r, hl1_y-hl1_r,
                      hl1_x+hl1_r, hl1_y+hl1_r,
                      fill=hl1_col, outline="")

        hl2_r   = int(hl1_r * 0.5)
        hl2_col = self._scale_color(col["bubble"], 0.95)
        c.create_oval(hl1_x-hl2_r, hl1_y-hl2_r,
                      hl1_x+hl2_r, hl1_y+hl2_r,
                      fill=hl2_col, outline="")

        hl3_x   = cx + RADIUS * 0.3
        hl3_y   = cy + RADIUS * 0.25
        hl3_r   = 5
        hl3_col = self._scale_color(col["rim"], 0.4)
        c.create_oval(hl3_x-hl3_r, hl3_y-hl3_r,
                      hl3_x+hl3_r, hl3_y+hl3_r,
                      fill=hl3_col, outline="")

        # ── State label ───────────────────────────────────────────────────
        label = {"passive":   "STANDBY",
                 "listening": "LISTENING",
                 "speaking":  "SPEAKING"}[state]
        c.create_text(cx, cy + RADIUS + 22,
                      text=label,
                      fill=col["text"],
                      font=("Courier", 9, "bold"))

        self.root.after(UPDATE_MS, self._animate)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    root = tk.Tk()
    app  = VASIOverlay(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.reader.stop()


if __name__ == "__main__":
    main()