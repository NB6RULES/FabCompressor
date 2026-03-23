"""
Fab Compressor v2.0 — Liquid Glass Edition
by NB6
Compresses images → JPG (≤100 KB, ≤1600 px) and videos → MP4 (≤1 MB/min, chosen res/fps)
Compatible with Python 3.8 – 3.14
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess
import shutil
from pathlib import Path
import json
import math
import webbrowser

# ── CustomTkinter ─────────────────────────────────────────────────────────────
try:
    import customtkinter as ctk
    CTK_OK = True
except ImportError:
    CTK_OK = False

# ── Optional image / video deps ───────────────────────────────────────────────
try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_OK = True
except ImportError:
    HEIF_OK = False

# ── Windows blur (pywinstyles) ────────────────────────────────────────────────
try:
    import pywinstyles
    PWS_OK = True
except ImportError:
    PWS_OK = False

# ─────────────────────────────────────────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp",
              ".tiff", ".tif", ".webp", ".heic", ".heif", ".avif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv",
              ".webm", ".m4v", ".3gp", ".mpeg", ".mpg",
              ".ts", ".mts", ".m2ts"}

MAX_IMG_BYTES  = 100 * 1024
MAX_IMG_DIM    = 1600

# ══════════════════════════════════════════════════════════════════════════════
# Liquid Glass & Tonal Depth — Design System (Stitch/fabcompressor spec)
# ══════════════════════════════════════════════════════════════════════════════

# ── Surface Hierarchy (No-Line Rule: boundaries via tonal shifts only) ────────
GLASS_BG               = "#0e0e10"   # surface — base layer
GLASS_SURFACE          = "#19191c"   # surface-container — raised cards
GLASS_ELEVATED         = "#1f1f22"   # surface-container-high — modals/hovers
GLASS_HIGHLIGHT        = "#252528"   # surface-container-highest — focus/active
GLASS_BORDER           = "#252528"   # surface-variant — ghost border at low opacity
GLASS_INSET            = "#000000"   # surface-container-lowest — inset/recessed

# ── Accent Palette ────────────────────────────────────────────────────────────
ACCENT_BLUE     = "#7fafff"   # primary
ACCENT_BLUE_DIM = "#4593ff"   # primary-fixed-dim (pressed)
ACCENT_PURPLE   = "#9392ff"   # secondary
ACCENT_TERTIARY = "#d277ff"   # tertiary
ACCENT_CYAN     = "#9392ff"   # alias → secondary for info/links
ACCENT_GREEN    = "#32D74B"   # success (keep vibrant)
ACCENT_YELLOW   = "#FFD60A"   # warning
ACCENT_ORANGE   = "#FF9F0A"   # alert
ACCENT_RED      = "#ff716c"   # error (Stitch spec)
ACCENT_PINK     = "#d57fff"   # tertiary-fixed-dim

# ── Text Hierarchy ────────────────────────────────────────────────────────────
TEXT_PRIMARY    = "#fefbfe"   # on-surface
TEXT_SECONDARY  = "#acaaad"   # on-surface-variant
TEXT_TERTIARY   = "#767577"   # outline
TEXT_QUATERNARY = "#48474a"   # outline-variant (disabled/placeholder)

SUCCESS = ACCENT_GREEN
WARNING = ACCENT_YELLOW
ERROR   = ACCENT_RED
INFO    = ACCENT_PURPLE

# ── Typography — Manrope headlines, Inter/Segoe body ─────────────────────────
_FF      = "Segoe UI"
_FF_DISP = "Segoe UI Variable Display"   # closest headline stand-in for Manrope
_FF_BOLD = "Segoe UI Semibold"
FONT_DISPLAY  = (_FF_DISP, 32, "bold")
FONT_TITLE    = (_FF_DISP, 22, "normal")
FONT_HEADLINE = (_FF_DISP, 15, "bold")
FONT_BODY     = (_FF, 13, "normal")
FONT_BODY_MED = (_FF, 13, "bold")
FONT_CAPTION  = (_FF, 11, "normal")
FONT_CAPTION_MED = (_FF, 11, "bold")
FONT_OVERLINE = (_FF, 9, "bold")
FONT_MONO     = ("Cascadia Code", 11)
FONT_MONO_ALT = ("Consolas", 11)

# ── Spacing (8pt base grid, 2× scale per Stitch spec) ────────────────────────
XXS =  2
XS  =  4
SM  =  8
MD  = 12
LG  = 16
XL  = 24
XXL = 32
XXXL = 48

# ── Corner Radii — cards xl (24px), interactive md (8px per ROUND_EIGHT) ─────
RADIUS_SM =  4
RADIUS_MD =  8
RADIUS_LG = 12
RADIUS_XL = 20

# ── Shadows — diffused ambient (40-60px blur simulated via layering) ──────────
SHADOW_COLOR = "#0e0e10"   # tinted on-surface, never pure black

SOCIALS = [
    ("🎓", "Fab Academy", "https://fabacademy.org/2026/labs/kochi/students/nadec-biju/"),
    ("📷", "Instagram",   "https://www.instagram.com/nb6_rules/"),
    ("💼", "LinkedIn",    "https://www.linkedin.com/in/nadec-biju/"),
    ("🐱", "GitHub",      "https://github.com/NB6RULES"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Compression logic (pure functions, no GUI)
# ─────────────────────────────────────────────────────────────────────────────

def find_ffmpeg():
    # 1. Bundled inside the PyInstaller package (highest priority)
    if hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
        if os.path.isfile(bundled):
            return bundled
    # 2. System PATH
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    # 3. Common install locations
    for c in [r"C:\ffmpeg\bin\ffmpeg.exe",
              r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
              r"C:\Tools\ffmpeg\bin\ffmpeg.exe"]:
        if os.path.isfile(c):
            return c
    return None


def ffprobe_duration(path, ffmpeg_path):
    # Prefer bundled ffprobe sitting alongside ffmpeg
    probe = os.path.join(os.path.dirname(ffmpeg_path),
                         "ffprobe.exe" if sys.platform == "win32" else "ffprobe")
    if not os.path.isfile(probe):
        # Also check _MEIPASS root when ffmpeg path was resolved elsewhere
        if hasattr(sys, '_MEIPASS'):
            probe = os.path.join(sys._MEIPASS, 'ffprobe.exe')
        if not os.path.isfile(probe):
            probe = shutil.which("ffprobe") or "ffprobe"
    try:
        r = subprocess.run(
            [probe, "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=30)
        return float(json.loads(r.stdout)["format"].get("duration", 60))
    except Exception:
        return 60.0


def scan_folder(folder):
    images, videos = [], []
    for root, _, files in os.walk(folder):
        for f in files:
            ext = Path(f).suffix.lower()
            fp  = os.path.join(root, f)
            if ext in IMAGE_EXTS:
                images.append(fp)
            elif ext in VIDEO_EXTS:
                videos.append(fp)
    return images, videos


def compress_image(src, dst_folder, log_cb):
    if not PIL_OK:
        log_cb(f"  [SKIP] Pillow not installed – {os.path.basename(src)}", "error")
        return False
    try:
        dst = os.path.join(dst_folder, Path(src).stem + ".jpg")
        os.makedirs(dst_folder, exist_ok=True)
        with Image.open(src) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > MAX_IMG_DIM:
                ratio = MAX_IMG_DIM / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            lo, hi, quality = 10, 95, 85
            for _ in range(14):
                img.save(dst, "JPEG", quality=quality, optimize=True)
                if os.path.getsize(dst) <= MAX_IMG_BYTES:
                    break
                hi = quality
                quality = (lo + hi) // 2
            else:
                while os.path.getsize(dst) > MAX_IMG_BYTES and min(img.size) > 80:
                    img = img.resize(
                        (int(img.size[0] * 0.8), int(img.size[1] * 0.8)), Image.LANCZOS)
                    img.save(dst, "JPEG", quality=quality, optimize=True)
        kb = os.path.getsize(dst) / 1024
        log_cb(f"  ✓  {os.path.basename(src)}  →  {kb:.1f} KB", "success")
        return True
    except Exception as e:
        log_cb(f"  ✗  {os.path.basename(src)}: {e}", "error")
        return False


def compress_video(src, dst_folder, ffmpeg_path, log_cb, max_height=720, max_fps=30):
    try:
        dst       = os.path.join(dst_folder, Path(src).stem + ".mp4")
        os.makedirs(dst_folder, exist_ok=True)
        dur       = ffprobe_duration(src, ffmpeg_path)
        vid_kbits = int((dur / 60) * 8000 * 0.9)
        cmd = [
            ffmpeg_path, "-y", "-i", src,
            "-vf", f"scale=-2:'min({max_height},ih)',fps=fps='min({max_fps},source_fps)'",
            "-c:v", "libx264", "-preset", "slow", "-crf", "23",
            "-maxrate", f"{vid_kbits}k", "-bufsize", f"{vid_kbits*2}k",
            "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", dst,
        ]
        log_cb(f"  ⏳  Encoding {os.path.basename(src)} …", "accent")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            log_cb(f"  ✗  ffmpeg error:\n{r.stderr[-400:]}", "error")
            return False
        mb = os.path.getsize(dst) / (1024 * 1024)
        log_cb(f"  ✓  {os.path.basename(src)}  →  {mb:.2f} MB", "success")
        return True
    except Exception as e:
        log_cb(f"  ✗  {os.path.basename(src)}: {e}", "error")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Animated Ambient Background with Floating Orbs
# ══════════════════════════════════════════════════════════════════════════════

class AmbientBackground(tk.Canvas):
    """Subtle animated gradient orbs creating depth and ambient movement."""
    def __init__(self, parent):
        super().__init__(parent, highlightthickness=0, bd=0, bg=GLASS_BG)
        self._t = 0
        self._orbs = [
            {"cx": 0.15, "cy": 0.15, "r": 500, "col": "#0d0f16", "spd": 0.0004, "ph": 0.0},   # primary tint
            {"cx": 0.85, "cy": 0.80, "r": 450, "col": "#0f0d16", "spd": 0.0003, "ph": 1.5},   # secondary tint
            {"cx": 0.50, "cy": 0.50, "r": 350, "col": "#0a0a12", "spd": 0.0005, "ph": 3.0},   # neutral deep
            {"cx": 0.20, "cy": 0.85, "r": 280, "col": "#100812", "spd": 0.00035, "ph": 4.5},  # tertiary tint
            {"cx": 0.75, "cy": 0.25, "r": 320, "col": "#0c0d15", "spd": 0.00045, "ph": 2.0},  # primary-dim tint
        ]
        self.bind("<Configure>", lambda e: self._draw())
        self._animate()

    def _draw(self):
        self.delete("orb")
        w = self.winfo_width() or 1000
        h = self.winfo_height() or 900
        for o in self._orbs:
            ox = math.sin(self._t * o["spd"] + o["ph"]) * 0.06
            oy = math.cos(self._t * o["spd"] * 0.8 + o["ph"]) * 0.04
            cx = (o["cx"] + ox) * w
            cy = (o["cy"] + oy) * h
            r = o["r"]
            self.create_oval(cx-r, cy-r, cx+r, cy+r,
                             fill=o["col"], outline="", tags="orb")

    def _animate(self):
        self._t += 1
        self._draw()
        self.after(33, self._animate)  # ~30 fps for smoother feel


# ══════════════════════════════════════════════════════════════════════════════
# Polished Glass UI Components
# ══════════════════════════════════════════════════════════════════════════════

class GlassCard(tk.Canvas):
    """
    Frosted glass card with subtle gradient border and inner glow.
    Uses canvas for smooth rounded corners.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, highlightthickness=0, bd=0, bg=GLASS_BG, **kw)
        self._content_frame = None
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event=None):
        self.delete("bg")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        r = RADIUS_LG
        # Outer subtle glow/shadow
        # Shadow layer omitted (Tk doesn't support alpha)
        # Border
        self._rounded_rect(0, 0, w-1, h-2, r, fill=GLASS_BORDER, tags="bg")
        # Inner fill
        self._rounded_rect(1, 1, w-2, h-3, r-1, fill=GLASS_SURFACE, tags="bg")
        # Top highlight line (glass effect)
        self._rounded_rect(2, 2, w-3, 4, 2, fill="#232328", tags="bg")
        
        if self._content_frame:
            self.tag_raise(self._content_frame_id)

    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1+r, y1,
            x2-r, y1,
            x2, y1,
            x2, y1+r,
            x2, y2-r,
            x2, y2,
            x2-r, y2,
            x1+r, y2,
            x1, y2,
            x1, y2-r,
            x1, y1+r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    @property
    def body(self):
        """Returns a frame inside the card for adding content."""
        if self._content_frame is None:
            self._content_frame = tk.Frame(self, bg=GLASS_SURFACE)
            self._content_frame_id = self.create_window(
                RADIUS_MD, RADIUS_MD, window=self._content_frame, anchor="nw"
            )
            self.bind("<Configure>", self._update_content_size, add="+")
        return self._content_frame

    def _update_content_size(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w > RADIUS_MD*2 and h > RADIUS_MD*2:
            self._content_frame.configure(width=w-RADIUS_MD*2-4, height=h-RADIUS_MD*2-6)


class GlassCardSimple(tk.Frame):
    """
    Frosted glass card — Liquid Glass spec.
    Elevation via surface-container tier; no explicit 1px borders (No-Line Rule).
    Ghost border: surface-variant (#252528) as 2px outer frame at full opacity
    gives a subtle lift without a hairline.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=GLASS_BG, **kw)

        # Ghost-border layer: surface-container-highest at 2px gives tactile edge
        self._ghost = tk.Frame(self, bg=GLASS_HIGHLIGHT)
        self._ghost.pack(fill="both", expand=True)

        # Card surface: surface-container — one tier above base
        self.body = tk.Frame(self._ghost, bg=GLASS_SURFACE)
        self.body.pack(fill="both", expand=True, padx=2, pady=2)

        # Subtle top-edge shimmer (liquid highlight, not a divider)
        tk.Frame(self.body, bg="#232328", height=1).pack(fill="x", padx=RADIUS_MD, pady=(2, 0))


class GlassEntry(tk.Frame):
    """
    Modern input field with inset styling and focus glow.
    """
    def __init__(self, parent, textvariable=None, placeholder="", width=None, **kw):
        super().__init__(parent, bg=GLASS_BG)
        
        # Ghost border — surface-container-highest, not a hairline
        self.border_frame = tk.Frame(self, bg=GLASS_HIGHLIGHT)
        self.border_frame.pack(fill="both", expand=True)

        # Inset/hollowed look — surface-container-lowest (#000000)
        self.inner = tk.Frame(self.border_frame, bg=GLASS_INSET)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Entry widget
        entry_config = {
            "textvariable": textvariable,
            "font": FONT_BODY,
            "bg": GLASS_INSET,
            "fg": TEXT_PRIMARY,
            "insertbackground": ACCENT_BLUE,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 0,
        }
        if width:
            entry_config["width"] = width
            
        self.entry = tk.Entry(self.inner, **entry_config)
        self.entry.pack(fill="x", padx=LG, pady=SM+2)
        
        # Focus animations
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, e=None):
        self.border_frame.configure(bg="#3a5a80")   # primary at ~40% opacity approximation

    def _on_focus_out(self, e=None):
        self.border_frame.configure(bg=GLASS_HIGHLIGHT)

    def get(self):
        return self.entry.get()
    
    def insert(self, index, text):
        self.entry.insert(index, text)
        
    def delete(self, first, last):
        self.entry.delete(first, last)


class GlassButton(tk.Canvas):
    """
    Pill-shaped button with smooth hover/press states.
    Styles: "primary" (blue), "secondary" (glass), "danger" (red outline)
    """
    STYLES = {
        # Primary: vibrant gradient from primary → primary-fixed-dim (135°, simulated as mid-blend)
        "primary": {
            "bg": "#6ba2f0", "fg": "#002e60",
            "hover_bg": ACCENT_BLUE, "press_bg": ACCENT_BLUE_DIM,
            "border": ACCENT_BLUE,
        },
        # Secondary: glass-filled surface-container-high, ghost border (surface-variant)
        "secondary": {
            "bg": GLASS_ELEVATED, "fg": TEXT_PRIMARY,
            "hover_bg": GLASS_HIGHLIGHT, "press_bg": GLASS_BORDER,
            "border": GLASS_HIGHLIGHT,
        },
        # Danger: no background, error text with subtle hover tint
        "danger": {
            "bg": GLASS_SURFACE, "fg": ACCENT_RED,
            "hover_bg": "#1a1015", "press_bg": "#150a0a",
            "border": GLASS_HIGHLIGHT,
        },
        # Ghost: no background, muted text, tertiary glow on hover
        "ghost": {
            "bg": "transparent", "fg": TEXT_SECONDARY,
            "hover_bg": GLASS_ELEVATED, "press_bg": GLASS_HIGHLIGHT,
            "border": "transparent",
        },
    }

    def __init__(self, parent, text, command, style="secondary", icon=None, **kw):
        self._style_name = style
        self._s = self.STYLES.get(style, self.STYLES["secondary"])
        self._text = text
        self._cmd = command
        self._icon = icon
        self._active = True
        self._hover = False
        self._pressed = False
        
        # Calculate size
        temp_font = FONT_BODY
        # Estimate width
        text_width = len(text) * 8 + 40
        if icon:
            text_width += 20
        height = 36
        
        super().__init__(parent, width=text_width, height=height,
                         bg=GLASS_BG if style != "ghost" else parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        r = h // 2  # Full pill shape
        
        # Determine colors based on state
        if not self._active:
            bg = GLASS_BORDER
            fg = TEXT_QUATERNARY
            border = GLASS_BORDER
        elif self._pressed:
            bg = self._s["press_bg"]
            fg = self._s["fg"]
            border = self._s["border"]
        elif self._hover:
            bg = self._s["hover_bg"]
            fg = self._s["fg"]
            border = self._s["border"]
        else:
            bg = self._s["bg"]
            fg = self._s["fg"]
            border = self._s["border"]
        
        # Draw button shape
        if bg != "transparent":
            self._pill(2, 2, w-2, h-2, r-2, fill=bg, outline="")
        
        # Draw text
        display_text = self._text
        if self._icon:
            display_text = f"{self._icon}  {self._text}"
        self.create_text(w//2, h//2, text=display_text, font=FONT_BODY, fill=fg)

    def _pill(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1+r, y1,
            x2-r, y1,
            x2, y1,
            x2, y1+r,
            x2, y2-r,
            x2, y2,
            x2-r, y2,
            x1+r, y2,
            x1, y2,
            x1, y2-r,
            x1, y1+r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _on_enter(self, e=None):
        if self._active:
            self._hover = True
            self._draw()

    def _on_leave(self, e=None):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, e=None):
        if self._active:
            self._pressed = True
            self._draw()

    def _on_release(self, e=None):
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if was_pressed and self._active and self._cmd:
            self._cmd()

    def set_text(self, text):
        self._text = text
        self._draw()

    def set_style(self, style):
        self._style_name = style
        self._s = self.STYLES.get(style, self.STYLES["secondary"])
        self._draw()

    def set_active(self, on: bool):
        self._active = on
        self.configure(cursor="hand2" if on else "arrow")
        self._draw()


class GlassToggle(tk.Canvas):
    """macOS-style animated toggle switch with smooth spring animation."""
    W, H = 48, 28
    KNOB_R = 10
    PADDING = 4

    def __init__(self, parent, variable, command=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=GLASS_SURFACE, highlightthickness=0, bd=0,
                         cursor="hand2", **kw)
        self.var = variable
        self._cmd = command
        self._anim_progress = 1.0 if variable.get() else 0.0
        self._animating = False
        
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *_: self._start_animation())
        self._draw()

    def _start_animation(self):
        if not self._animating:
            self._animating = True
            self._animate()

    def _animate(self):
        target = 1.0 if self.var.get() else 0.0
        diff = target - self._anim_progress
        
        if abs(diff) < 0.01:
            self._anim_progress = target
            self._animating = False
            self._draw()
            return
        
        # Spring-like easing
        self._anim_progress += diff * 0.25
        self._draw()
        self.after(16, self._animate)

    def _draw(self):
        self.delete("all")
        p = self._anim_progress
        
        # Track color: secondary (#9392ff) for active per Stitch spec
        off_color = GLASS_HIGHLIGHT
        on_color = ACCENT_PURPLE
        
        # Simple color blend (approximate)
        track_color = on_color if p > 0.5 else off_color
        
        # Draw track (pill shape)
        self._pill(2, 2, self.W-2, self.H-2, self.H//2-2, fill=track_color)
        
        # Knob position
        knob_x = self.PADDING + self.KNOB_R + p * (self.W - 2*self.PADDING - 2*self.KNOB_R)
        knob_y = self.H // 2
        
        # Knob shadow
        self.create_oval(
            knob_x - self.KNOB_R, knob_y - self.KNOB_R + 1,
            knob_x + self.KNOB_R, knob_y + self.KNOB_R + 1,
            fill="#0a0a0c", outline=""
        )
        
        # Knob
        self.create_oval(
            knob_x - self.KNOB_R, knob_y - self.KNOB_R,
            knob_x + self.KNOB_R, knob_y + self.KNOB_R,
            fill="#ffffff", outline=""
        )

    def _pill(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _toggle(self, e=None):
        self.var.set(not self.var.get())
        if self._cmd:
            self._cmd()


class GlassProgress(tk.Canvas):
    """Sleek progress bar with animated gradient."""
    def __init__(self, parent, height=6, **kw):
        super().__init__(parent, height=height, bg=GLASS_BG,
                         highlightthickness=0, bd=0, **kw)
        self._value = 0
        self._target = 0
        self._animating = False
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, val, animate=True):
        self._target = max(0, min(100, val))
        if animate and not self._animating:
            self._animating = True
            self._animate()
        elif not animate:
            self._value = self._target
            self._draw()

    def _animate(self):
        diff = self._target - self._value
        if abs(diff) < 0.5:
            self._value = self._target
            self._animating = False
            self._draw()
            return
        
        self._value += diff * 0.15
        self._draw()
        self.after(16, self._animate)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 1
        h = self.winfo_height() or 6
        r = h // 2

        # Track: surface-container-highest
        self._pill(0, 0, w, h, r, fill=GLASS_HIGHLIGHT)

        pw = max(h, int(w * self._value / 100))
        if self._value > 0:
            # Simulate primary→tertiary gradient: draw two overlapping fills
            # Left segment: primary (#7fafff)
            mid = int(pw * 0.55)
            if mid > h:
                self._pill(0, 0, mid, h, r, fill=ACCENT_BLUE)
            # Right segment: blend toward tertiary (#d277ff) — use mid-blend color
            if pw > mid:
                self._pill(max(0, mid - r), 0, pw, h, r, fill="#a88aff")
            # Shimmer highlight (liquid glass top edge)
            if pw > r * 2:
                self._pill(2, 1, pw - 2, h // 2, r // 2, fill="#9ab8ff")

    def _pill(self, x1, y1, x2, y2, r, **kw):
        if x2 - x1 < r * 2:
            r = (x2 - x1) // 2
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)


class TrafficLights(tk.Frame):
    """macOS window controls with hover symbols."""
    def __init__(self, parent, close_cmd, minimize_cmd, maximize_cmd=None):
        super().__init__(parent, bg=GLASS_BG)
        
        self._buttons = []
        colors = [
            ("#FF605C", "#FF3B30", "×", close_cmd),      # Close
            ("#FFBD44", "#FF9500", "−", minimize_cmd),   # Minimize
            ("#00CA4E", "#28CD41", "+", maximize_cmd or (lambda: None)),  # Maximize
        ]
        
        for i, (color, hover_color, symbol, cmd) in enumerate(colors):
            btn = tk.Canvas(self, width=14, height=14, bg=GLASS_BG,
                           highlightthickness=0, cursor="hand2")
            btn.pack(side="left", padx=(0 if i == 0 else 6, 0))
            btn.create_oval(1, 1, 13, 13, fill=color, outline="", tags="dot")
            btn._color = color
            btn._hover_color = hover_color
            btn._symbol = symbol
            btn._cmd = cmd
            
            btn.bind("<Enter>", lambda e, b=btn: self._show_symbols(b))
            btn.bind("<Leave>", lambda e, b=btn: self._hide_symbols(b))
            btn.bind("<Button-1>", lambda e, b=btn: b._cmd())
            self._buttons.append(btn)

    def _show_symbols(self, btn):
        for b in self._buttons:
            b.delete("all")
            b.create_oval(1, 1, 13, 13, fill=b._hover_color, outline="")
            b.create_text(7, 6, text=b._symbol, font=(_FF, 9, "bold"), fill="#401010")

    def _hide_symbols(self, btn):
        for b in self._buttons:
            b.delete("all")
            b.create_oval(1, 1, 13, 13, fill=b._color, outline="")


# ══════════════════════════════════════════════════════════════════════════════
# Styled Dropdown (ttk.Combobox with glass styling)
# ══════════════════════════════════════════════════════════════════════════════

def make_glass_combo(parent, var, values, width=7):
    import tkinter.ttk as ttk
    style = ttk.Style()
    
    # Configure the combobox style
    style.configure("Glass.TCombobox",
        fieldbackground=GLASS_ELEVATED,
        background=GLASS_ELEVATED,
        foreground=TEXT_PRIMARY,
        selectbackground=GLASS_HIGHLIGHT,
        selectforeground=TEXT_PRIMARY,
        arrowcolor=TEXT_SECONDARY,
        bordercolor=GLASS_BORDER,
        lightcolor=GLASS_BORDER,
        darkcolor=GLASS_BORDER,
        insertcolor=ACCENT_BLUE,
        padding=(8, 4),
    )
    
    style.map("Glass.TCombobox",
        fieldbackground=[("readonly", GLASS_ELEVATED), ("focus", GLASS_ELEVATED)],
        foreground=[("readonly", TEXT_PRIMARY), ("focus", TEXT_PRIMARY)],
        background=[("readonly", GLASS_ELEVATED), ("active", GLASS_HIGHLIGHT)],
        bordercolor=[("focus", ACCENT_BLUE)],
    )
    
    cb = ttk.Combobox(parent, textvariable=var, values=values,
                      state="readonly", width=width,
                      style="Glass.TCombobox",
                      font=FONT_BODY)
    return cb


# ══════════════════════════════════════════════════════════════════════════════
# Minimal macOS-style Scrollbar
# ══════════════════════════════════════════════════════════════════════════════

class GlassScrollbar(tk.Canvas):
    """Minimal overlay scrollbar like macOS."""
    def __init__(self, parent, command=None, **kw):
        super().__init__(parent, width=8, highlightthickness=0, bd=0,
                         bg=GLASS_BG, **kw)
        self._command = command
        self._thumb_top = 0.0
        self._thumb_bottom = 1.0
        self._hover = False
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_top = 0
        
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, first, last):
        self._thumb_top = float(first)
        self._thumb_bottom = float(last)
        self._draw()

    def _set_hover(self, val):
        self._hover = val
        self._draw()

    def _draw(self):
        self.delete("all")
        h = self.winfo_height()
        if h < 1:
            return
        
        # Only show if needed
        if self._thumb_bottom - self._thumb_top >= 0.99:
            return
        
        w = self.winfo_width()
        thumb_h = max(30, (self._thumb_bottom - self._thumb_top) * h)
        thumb_y = self._thumb_top * h
        
        color = TEXT_QUATERNARY if self._hover or self._dragging else "#333336"
        
        # Draw rounded thumb
        r = 3
        x1, y1 = 1, thumb_y + 2
        x2, y2 = w - 1, thumb_y + thumb_h - 2
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=color, outline="")

    def _on_click(self, event):
        h = self.winfo_height()
        thumb_h = (self._thumb_bottom - self._thumb_top) * h
        thumb_y = self._thumb_top * h
        
        if thumb_y <= event.y <= thumb_y + thumb_h:
            self._dragging = True
            self._drag_start_y = event.y
            self._drag_start_top = self._thumb_top
        else:
            # Click outside thumb - jump to position
            click_pos = event.y / h
            if self._command:
                self._command("moveto", str(click_pos))

    def _on_drag(self, event):
        if not self._dragging:
            return
        h = self.winfo_height()
        delta = (event.y - self._drag_start_y) / h
        new_top = max(0, min(1 - (self._thumb_bottom - self._thumb_top),
                             self._drag_start_top + delta))
        if self._command:
            self._command("moveto", str(new_top))


# ══════════════════════════════════════════════════════════════════════════════
# Main Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fab Compressor")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        self.configure(bg=GLASS_BG)
        
        # Remove default window decorations on Windows for custom titlebar
        # self.overrideredirect(True)  # Uncomment for borderless
        
        # Try Windows Mica/Acrylic blur
        if sys.platform == "win32" and PWS_OK:
            try:
                self.update()
                pywinstyles.apply_style(self, "acrylic")
            except Exception:
                pass

        # State
        self.v_src      = tk.StringVar()
        self.v_dst      = tk.StringVar()
        self.v_img      = tk.BooleanVar(value=True)
        self.v_vid      = tk.BooleanVar(value=True)
        self.v_out_mode = tk.StringVar(value="subfolder")
        self.v_res      = tk.StringVar(value="720")
        self.v_fps      = tk.StringVar(value="30")
        self.ffmpeg     = find_ffmpeg()
        self.running    = False

        self._build_ui()
        self.after(100, self._show_dep_notice)

    # ══════════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Animated ambient background
        self.bg_canvas = AmbientBackground(self)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Main container
        main = tk.Frame(self, bg=GLASS_BG)
        main.place(x=0, y=0, relwidth=1, relheight=1)
        main.lift()

        # ── Custom Titlebar ───────────────────────────────────────────────────
        titlebar = tk.Frame(main, bg=GLASS_BG, height=52)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        
        # Traffic lights
        TrafficLights(titlebar, self.destroy, self.iconify).pack(
            side="left", padx=(LG, 0), pady=LG)
        
        # Title
        title_label = tk.Label(titlebar, text="Fab Compressor",
                              font=FONT_CAPTION_MED, fg=TEXT_TERTIARY, bg=GLASS_BG)
        title_label.pack(expand=True)
        
        # Make titlebar draggable
        for widget in [titlebar, title_label]:
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)

        # ══════════════════════════════════════════════════════════════════════
        # HORIZONTAL TWO-COLUMN LAYOUT
        # ══════════════════════════════════════════════════════════════════════
        
        content_area = tk.Frame(main, bg=GLASS_BG)
        content_area.pack(fill="both", expand=True, padx=XL, pady=(0, XL))
        
        # Configure grid columns (left: settings wider, right: log narrower)
        content_area.grid_columnconfigure(0, weight=3, minsize=800)
        content_area.grid_columnconfigure(1, weight=2, minsize=120)
        content_area.grid_rowconfigure(0, weight=1)

        # ══════════════════════════════════════════════════════════════════════
        # LEFT COLUMN - Settings
        # ══════════════════════════════════════════════════════════════════════
        
        left_col = tk.Frame(content_area, bg=GLASS_BG)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, MD))
        
        # Scrollable left panel
        left_canvas = tk.Canvas(left_col, bg=GLASS_BG, highlightthickness=0, bd=0)
        left_scroll = GlassScrollbar(left_col, command=left_canvas.yview)
        left_inner = tk.Frame(left_canvas, bg=GLASS_BG)
        
        left_inner.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=left_inner, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)
        
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")
        
        # Mouse wheel for left panel
        def _scroll_left(event):
            left_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        left_canvas.bind("<Enter>", lambda e: left_canvas.bind_all("<MouseWheel>", _scroll_left))

        p = left_inner

        # ── Hero ──────────────────────────────────────────────────────────────
        hero = tk.Frame(p, bg=GLASS_BG)
        hero.pack(fill="x", pady=(SM, LG))
        
        icon_canvas = tk.Canvas(hero, width=48, height=48, bg=GLASS_BG, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, MD))
        icon_canvas.create_oval(2, 2, 46, 46, fill="#3a5a80", outline="")  # primary container tint
        icon_canvas.create_oval(6, 6, 42, 42, fill=ACCENT_BLUE, outline="")
        icon_canvas.create_text(24, 24, text="⚡", font=(_FF, 18), fill="#002e60")  # on-primary
        
        text_col = tk.Frame(hero, bg=GLASS_BG)
        text_col.pack(side="left", fill="x")
        tk.Label(text_col, text="Fab Compressor", font=FONT_HEADLINE, fg=TEXT_PRIMARY, bg=GLASS_BG).pack(anchor="w")
        tk.Label(text_col, text="Smart media compression", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_BG).pack(anchor="w")

        # ── Source Folder Card ────────────────────────────────────────────────
        self._section_header(p, "SOURCE FOLDER", "📁")
        
        src_card = GlassCardSimple(p)
        src_card.pack(fill="x", pady=(0, MD))
        
        src_row = tk.Frame(src_card.body, bg=GLASS_SURFACE)
        src_row.pack(fill="x", padx=MD, pady=MD)
        
        self.ent_src = GlassEntry(src_row, textvariable=self.v_src)
        self.ent_src.pack(side="left", fill="x", expand=True, padx=(0, SM))
        GlassButton(src_row, "Browse", self._browse_src, style="secondary").pack(side="right")

        # ── Output Card ───────────────────────────────────────────────────────
        self._section_header(p, "OUTPUT", "📤")
        
        out_card = GlassCardSimple(p)
        out_card.pack(fill="x", pady=(0, MD))
        
        mode_row = tk.Frame(out_card.body, bg=GLASS_SURFACE)
        mode_row.pack(fill="x", padx=MD, pady=(MD, SM))
        
        for label, value, warn in [("Save to folder", "subfolder", False), ("Replace originals ⚠", "inplace", True)]:
            rb = tk.Radiobutton(mode_row, text=label, variable=self.v_out_mode, value=value,
                               command=self._toggle_output_mode, font=FONT_CAPTION,
                               bg=GLASS_SURFACE, fg=ACCENT_YELLOW if warn else TEXT_SECONDARY,
                               selectcolor=GLASS_ELEVATED, activebackground=GLASS_SURFACE,
                               activeforeground=TEXT_PRIMARY,
                               highlightthickness=0, cursor="hand2")
            rb.pack(side="left", padx=(0, LG))

        self.frm_dst = tk.Frame(out_card.body, bg=GLASS_SURFACE)
        self.frm_dst.pack(fill="x", padx=MD, pady=(0, MD))
        self.ent_dst = GlassEntry(self.frm_dst, textvariable=self.v_dst)
        self.ent_dst.pack(side="left", fill="x", expand=True, padx=(0, SM))
        GlassButton(self.frm_dst, "Browse", self._browse_dst, style="secondary").pack(side="right")

        # ── Compression Settings Card ─────────────────────────────────────────
        self._section_header(p, "COMPRESSION", "⚙️")
        
        settings_card = GlassCardSimple(p)
        settings_card.pack(fill="x", pady=(0, MD))
        sb = settings_card.body

        # Images toggle
        img_row = tk.Frame(sb, bg=GLASS_SURFACE)
        img_row.pack(fill="x", padx=MD, pady=(MD, XS))
        GlassToggle(img_row, self.v_img).pack(side="left", padx=(0, MD))
        img_info = tk.Frame(img_row, bg=GLASS_SURFACE)
        img_info.pack(side="left", fill="x")
        tk.Label(img_info, text="🖼️ Images → JPG", font=FONT_BODY_MED, fg=TEXT_PRIMARY, bg=GLASS_SURFACE).pack(anchor="w")
        tk.Label(img_info, text="≤100KB • ≤1600px", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE).pack(anchor="w")

        # Videos toggle
        vid_row = tk.Frame(sb, bg=GLASS_SURFACE)
        vid_row.pack(fill="x", padx=MD, pady=(XS, SM))
        GlassToggle(vid_row, self.v_vid).pack(side="left", padx=(0, MD))
        vid_info = tk.Frame(vid_row, bg=GLASS_SURFACE)
        vid_info.pack(side="left", fill="x")
        tk.Label(vid_info, text="🎬 Videos → MP4", font=FONT_BODY_MED, fg=TEXT_PRIMARY, bg=GLASS_SURFACE).pack(anchor="w")
        tk.Label(vid_info, text="≤1MB/min", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE).pack(anchor="w")

        # Resolution + FPS in a compact row
        opts_row = tk.Frame(sb, bg=GLASS_SURFACE)
        opts_row.pack(fill="x", padx=MD, pady=(0, MD))
        
        tk.Label(opts_row, text="Resolution", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE).pack(side="left")
        make_glass_combo(opts_row, self.v_res, ["1080", "720", "540", "480", "360"], 5).pack(side="left", padx=(SM, XS))
        tk.Label(opts_row, text="p", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE).pack(side="left")
        tk.Frame(opts_row, bg=GLASS_BG, width=LG).pack(side="left")
        tk.Label(opts_row, text="FPS", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE).pack(side="left")
        make_glass_combo(opts_row, self.v_fps, ["16", "20", "24", "30"], 4).pack(side="left", padx=(SM, 0))

        # ── Dependencies ──────────────────────────────────────────────────────
        dep_row = tk.Frame(p, bg=GLASS_BG)
        dep_row.pack(fill="x", pady=(SM, MD))
        
        deps = self._get_dependency_status()
        for text, ok in deps:
            badge_bg = GLASS_ELEVATED if ok else "#1a0f0f"
            badge = tk.Frame(dep_row, bg=GLASS_HIGHLIGHT)
            badge.pack(side="left", padx=(0, XS))
            inner_badge = tk.Frame(badge, bg=badge_bg)
            inner_badge.pack(padx=1, pady=1)
            color = SUCCESS if ok else WARNING
            icon = "✓" if ok else "!"
            tk.Label(inner_badge, text=f" {icon}  {text} ", font=FONT_CAPTION,
                    fg=color, bg=badge_bg).pack(padx=XS, pady=XXS)

        # ── Footer in left column ─────────────────────────────────────────────
        self._build_footer(p)

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT COLUMN - Actions & Log
        # ══════════════════════════════════════════════════════════════════════
        
        right_col = tk.Frame(content_area, bg=GLASS_BG)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(MD, 0))

        # ── Action Section ────────────────────────────────────────────────────
        action_card = GlassCardSimple(right_col)
        action_card.pack(fill="x", pady=(SM, MD))
        
        action_inner = tk.Frame(action_card.body, bg=GLASS_SURFACE)
        action_inner.pack(fill="x", padx=MD, pady=MD)
        
        self.btn_run = GlassButton(action_inner, "Start Compression", self._start_compression, style="primary", icon="▶")
        self.btn_run.pack(side="left")
        
        self.lbl_status = tk.Label(action_inner, text="", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE)
        self.lbl_status.pack(side="left", padx=LG)
        
        GlassButton(action_inner, "Clear", self._clear_log, style="ghost").pack(side="right")

        # ── Progress Section ──────────────────────────────────────────────────
        progress_card = GlassCardSimple(right_col)
        progress_card.pack(fill="x", pady=(0, MD))
        
        progress_inner = tk.Frame(progress_card.body, bg=GLASS_SURFACE)
        progress_inner.pack(fill="x", padx=MD, pady=MD)
        
        self.lbl_progress = tk.Label(progress_inner, text="Ready to compress", font=FONT_CAPTION, fg=TEXT_TERTIARY, bg=GLASS_SURFACE)
        self.lbl_progress.pack(anchor="w")
        
        self.progressbar = GlassProgress(progress_inner)
        self.progressbar.pack(fill="x", pady=(SM, 0))

        # ── Log Section (takes remaining space) ───────────────────────────────
        log_card = GlassCardSimple(right_col)
        log_card.pack(fill="both", expand=True)
        
        log_header = tk.Frame(log_card.body, bg=GLASS_SURFACE)
        log_header.pack(fill="x", padx=MD, pady=(MD, SM))
        tk.Label(log_header, text="Activity Log", font=FONT_HEADLINE, fg=TEXT_PRIMARY, bg=GLASS_SURFACE).pack(anchor="w")
        
        log_frame = tk.Frame(log_card.body, bg=GLASS_INSET)
        log_frame.pack(fill="both", expand=True, padx=MD, pady=(0, MD))

        self.txt_log = tk.Text(log_frame, bg=GLASS_INSET, fg=TEXT_SECONDARY,
                               font=FONT_MONO if shutil.which("cascadia") else FONT_MONO_ALT,
                               wrap="word", relief="flat", bd=0, padx=MD, pady=MD,
                               state="disabled", cursor="arrow")
        
        log_scroll = GlassScrollbar(log_frame, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_scroll.set)
        
        log_scroll.pack(side="right", fill="y", padx=(0, XS), pady=XS)
        self.txt_log.pack(fill="both", expand=True)
        
        # Configure log tags
        for tag, color in [("success", SUCCESS), ("error", ERROR), ("warn", WARNING),
                           ("accent", INFO), ("muted", TEXT_TERTIARY), ("bold", TEXT_PRIMARY)]:
            self.txt_log.tag_configure(tag, foreground=color)

    # ══════════════════════════════════════════════════════════════════════════
    # Footer
    # ══════════════════════════════════════════════════════════════════════════

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=GLASS_BG)
        footer.pack(fill="x", padx=XXL, pady=(MD, XXXL))
        
        # "Made with ♥ by nb6"
        made_row = tk.Frame(footer, bg=GLASS_BG)
        made_row.pack()
        
        parts = [
            ("Made with ", TEXT_TERTIARY, None),
            ("♥", ACCENT_RED, None),
            (" by ", TEXT_TERTIARY, None),
            ("NB6", ACCENT_CYAN, SOCIALS[0][2]),
        ]
        
        for text, color, url in parts:
            lbl = tk.Label(made_row, text=text, font=FONT_CAPTION,
                          fg=color, bg=GLASS_BG,
                          cursor="hand2" if url else "")
            lbl.pack(side="left")
            if url:
                lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                lbl.bind("<Enter>", lambda e, l=lbl: l.configure(fg=TEXT_PRIMARY))
                lbl.bind("<Leave>", lambda e, l=lbl, c=color: l.configure(fg=c))
        
        # Social chips
        chips_row = tk.Frame(footer, bg=GLASS_BG)
        chips_row.pack(pady=(LG, 0))
        
        for icon, label, url in SOCIALS:
            chip = tk.Frame(chips_row, bg=GLASS_HIGHLIGHT, cursor="hand2")
            chip_inner = tk.Frame(chip, bg=GLASS_SURFACE)
            chip_inner.pack(padx=1, pady=1)

            chip_label = tk.Label(chip_inner,
                                 text=f"{icon}  {label}",
                                 font=FONT_CAPTION, fg=TEXT_SECONDARY,
                                 bg=GLASS_SURFACE,
                                 padx=MD, pady=XS+2, cursor="hand2")
            chip_label.pack()
            chip.pack(side="left", padx=XS)

            # Hover: primary ghost border + tertiary text glow
            def make_handlers(ch, ci, cl, u):
                def enter(e):
                    ch.configure(bg=ACCENT_BLUE)
                    ci.configure(bg=GLASS_ELEVATED)
                    cl.configure(bg=GLASS_ELEVATED, fg=ACCENT_TERTIARY)
                def leave(e):
                    ch.configure(bg=GLASS_HIGHLIGHT)
                    ci.configure(bg=GLASS_SURFACE)
                    cl.configure(bg=GLASS_SURFACE, fg=TEXT_SECONDARY)
                def click(e):
                    webbrowser.open(u)
                return enter, leave, click
            
            h_enter, h_leave, h_click = make_handlers(chip, chip_inner, chip_label, url)
            for w in [chip, chip_inner, chip_label]:
                w.bind("<Enter>", h_enter)
                w.bind("<Leave>", h_leave)
                w.bind("<Button-1>", h_click)

    # ══════════════════════════════════════════════════════════════════════════
    # UI Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _divider(self, parent):
        """Tonal gap instead of hairline — Stitch No-Line Rule."""
        tk.Frame(parent, bg=GLASS_BG, height=LG).pack(fill="x")

    def _section_header(self, parent, text, icon=""):
        """Section header — label-md style, no divider beneath."""
        header = tk.Frame(parent, bg=GLASS_BG)
        header.pack(fill="x", padx=XL, pady=(LG, XS))

        if icon:
            tk.Label(header, text=icon, font=FONT_CAPTION,
                    fg=TEXT_TERTIARY, bg=GLASS_BG).pack(side="left", padx=(0, XS))

        tk.Label(header, text=text,
                font=FONT_OVERLINE, fg=ACCENT_BLUE, bg=GLASS_BG,
                anchor="w").pack(side="left")

    def _get_dependency_status(self):
        """Return list of (name, ok) tuples for dependencies."""
        deps = []
        deps.append(("ffmpeg", bool(self.ffmpeg)))
        deps.append(("Pillow", PIL_OK))
        if PIL_OK:
            deps.append(("HEIC", HEIF_OK))
        return deps

    # ══════════════════════════════════════════════════════════════════════════
    # Window Dragging
    # ══════════════════════════════════════════════════════════════════════════

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ══════════════════════════════════════════════════════════════════════════
    # Output Mode Toggle
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_output_mode(self):
        if self.v_out_mode.get() == "subfolder":
            self.frm_dst.pack(fill="x", padx=MD, pady=(0, MD))
        else:
            self.frm_dst.pack_forget()

    # ══════════════════════════════════════════════════════════════════════════
    # Dependency Notice
    # ══════════════════════════════════════════════════════════════════════════

    def _show_dep_notice(self):
        if PIL_OK and HEIF_OK and self.ffmpeg:
            self._log("✓  All dependencies found — ready to compress!", "success")
        else:
            if not PIL_OK:
                self._log("⚠  Pillow missing — run: pip install Pillow pillow-heif", "warn")
            elif not HEIF_OK:
                self._log("⚠  pillow-heif missing — run: pip install pillow-heif", "warn")
            if not self.ffmpeg:
                self._log("⚠  ffmpeg not found — video compression disabled", "warn")

    # ══════════════════════════════════════════════════════════════════════════
    # Logging
    # ══════════════════════════════════════════════════════════════════════════

    def _log(self, msg, tag="bold"):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n", tag)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # Browse Actions
    # ══════════════════════════════════════════════════════════════════════════

    def _browse_src(self):
        folder = filedialog.askdirectory(title="Select source folder")
        if folder:
            self.v_src.set(folder)
            self.v_dst.set(os.path.join(folder, "compressed"))

    def _browse_dst(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.v_dst.set(folder)

    def _clear_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # Start Compression
    # ══════════════════════════════════════════════════════════════════════════

    def _start_compression(self):
        if self.running:
            return
        
        src = self.v_src.get().strip()
        inplace = self.v_out_mode.get() == "inplace"
        dst = src if inplace else self.v_dst.get().strip()
        
        if not src or not os.path.isdir(src):
            messagebox.showerror("Error", "Please select a valid source folder.")
            return
        
        if not inplace and not dst:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        
        if inplace:
            if not messagebox.askyesno(
                "Replace in-place?",
                "This will OVERWRITE original files.\n\nMake sure you have a backup. Continue?",
                icon="warning"
            ):
                return
        
        if not self.v_img.get() and not self.v_vid.get():
            messagebox.showerror("Error", "Enable at least one file type.")
            return
        
        self.running = True
        self.btn_run.set_text("Compressing…")
        self.btn_run.set_style("secondary")
        self.btn_run.set_active(False)
        
        threading.Thread(target=self._run_compression, args=(src, dst), daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # Compression Thread
    # ══════════════════════════════════════════════════════════════════════════

    def _run_compression(self, src, dst):
        try:
            self._log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "muted")
            self._log(f"  Source: {src}", "accent")
            self._log(f"  Output: {dst}", "accent")
            self._log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "muted")

            images, videos = scan_folder(src)
            do_img = self.v_img.get() and PIL_OK
            do_vid = self.v_vid.get() and bool(self.ffmpeg)
            pi, pv = (images if do_img else []), (videos if do_vid else [])
            total = len(pi) + len(pv)

            if total == 0:
                self._log("\nNo eligible files found.", "warn")
                self._finish_compression(0, 0)
                return

            self._log(f"\nFound {len(images)} image(s), {len(videos)} video(s)", "bold")
            if not do_img and images:
                self._log("  Skipping images — Pillow missing", "warn")
            if not do_vid and videos:
                self._log("  Skipping videos — ffmpeg missing", "warn")

            done = ok = 0

            if pi:
                self._log("\n── Images ──────────────────────────────────", "muted")
                for i, path in enumerate(pi, 1):
                    rel = os.path.relpath(os.path.dirname(path), src)
                    ddir = os.path.join(dst, rel) if rel != "." else dst
                    self._log(f"[{i}/{len(pi)}]  {os.path.basename(path)}", "bold")
                    self.lbl_progress.config(text=f"Images: {i} / {len(pi)}")
                    if compress_image(path, ddir, self._log):
                        ok += 1
                    done += 1
                    self.progressbar.set(done / total * 100)
                    self.update_idletasks()

            if pv:
                self._log("\n── Videos ──────────────────────────────────", "muted")
                for i, path in enumerate(pv, 1):
                    rel = os.path.relpath(os.path.dirname(path), src)
                    ddir = os.path.join(dst, rel) if rel != "." else dst
                    self._log(f"[{i}/{len(pv)}]  {os.path.basename(path)}", "bold")
                    self.lbl_progress.config(text=f"Videos: {i} / {len(pv)}")
                    if compress_video(path, ddir, self.ffmpeg, self._log,
                                     max_height=int(self.v_res.get()),
                                     max_fps=int(self.v_fps.get())):
                        ok += 1
                    done += 1
                    self.progressbar.set(done / total * 100)
                    self.update_idletasks()

            self._finish_compression(ok, total)

        except Exception as e:
            self._log(f"\n✗ FATAL ERROR: {e}", "error")
            self._finish_compression(0, 0)

    def _finish_compression(self, ok, total):
        self.progressbar.set(100 if total > 0 else 0, animate=False)
        self.lbl_progress.config(text=f"Completed — {ok} / {total} files processed")
        self._log(f"\n✓  Finished: {ok} / {total} files compressed", "success")
        self._log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", "muted")
        self.lbl_status.config(text=f"✓ {ok}/{total} done", fg=SUCCESS)
        self.running = False
        self.btn_run.set_text("Start Compression")
        self.btn_run.set_style("primary")
        self.btn_run.set_active(True)


# ══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
