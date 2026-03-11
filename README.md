<div align="center">

# ⚡ Fab Compressor

**Smart, beautiful media compression for images and videos**

*Batch compress entire folders in seconds — macOS Liquid Glass UI on Windows*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/NB6RULES/fab-compressor)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Made by NB6](https://img.shields.io/badge/Made%20by-NB6-ff6482)](https://fabacademy.org/2026/labs/kochi/students/nadec-biju/)

</div>

---

## ✨ What It Does

**Fab Compressor** scans a folder (recursively), finds all your images and videos, and compresses them to web-friendly sizes — automatically.

| File Type | Target | Format |
|-----------|--------|--------|
| 🖼️ Images | ≤ 100 KB, ≤ 1600 px | JPG |
| 🎬 Videos | ≤ 1 MB/min of footage | MP4 |

Supports JPG, PNG, GIF, BMP, TIFF, WebP, HEIC, HEIF, AVIF, MP4, MOV, AVI, MKV, and [many more](#supported-formats).

---

## 🖥️ Screenshots

> *Dark glass UI with animated ambient background, real-time activity log, and progress bar.*

---

## 🚀 Quick Start

### Run from source

```bash
# 1. Clone the repo
git clone https://github.com/NB6RULES/fab-compressor.git
cd fab-compressor

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install ffmpeg (for video compression)
#    Windows: https://ffmpeg.org/download.html  — add to PATH

# 4. Run
python fab_compressor.py
```

### Or just double-click `debug_run.bat` on Windows

---

## 📦 Build Standalone EXE

Uses **PyInstaller** — the included `.spec` file is preconfigured:

```bash
pip install pyinstaller
pyinstaller FabCompressor.spec
# → dist/FabCompressor.exe
```

---

## 📋 Requirements

| Dependency | Purpose | Required? |
|------------|---------|-----------|
| Python 3.8+ | Runtime | ✅ Yes |
| [Pillow](https://pypi.org/project/Pillow/) | Image compression | ✅ Yes (images) |
| [ffmpeg](https://ffmpeg.org/) | Video compression | ✅ Yes (videos) |
| [pillow-heif](https://pypi.org/project/pillow-heif/) | HEIC/HEIF support | ⚠️ Optional |
| [pywinstyles](https://pypi.org/project/pywinstyles/) | Windows Acrylic blur | ⚠️ Optional |

```bash
pip install Pillow pillow-heif pywinstyles
```

---

## 🗂️ Supported Formats

**Images:** `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.tif` `.webp` `.heic` `.heif` `.avif`

**Videos:** `.mp4` `.mov` `.avi` `.mkv` `.wmv` `.flv` `.webm` `.m4v` `.3gp` `.mpeg` `.mpg` `.ts` `.mts` `.m2ts`

---

## ⚙️ How Compression Works

### Images
1. Resizes to max 1600 px on the longest edge (if larger)
2. Binary-searches JPEG quality (10–95) to hit ≤ 100 KB
3. Falls back to progressive downscaling if quality alone can't get there

### Videos
1. Probes duration with `ffprobe`
2. Calculates target bitrate to meet ≤ 1 MB/min
3. Encodes with `libx264` (slow preset, CRF 23) + AAC audio
4. Applies max resolution (360p–1080p) and FPS cap (16–30) you choose

---

## 🎛️ UI Features

- **Glass dark theme** — macOS Sonoma-inspired, animated ambient orbs
- **Windows Acrylic blur** — via `pywinstyles` (auto-enables if installed)
- **Animated toggles** — smooth spring-physics macOS-style switches
- **Real-time log** — colour-coded activity feed
- **Animated progress bar** — spring-eased fill animation
- **Two output modes** — save to subfolder, or replace-in-place (with warning)
- **Dependency badges** — shows ffmpeg / Pillow / HEIC status at launch
- **Custom titlebar** — draggable, with macOS traffic-light buttons

---

## 📁 Project Structure

```
fab-compressor/
├── fab_compressor.py     # Main application (single-file)
├── FabCompressor.spec    # PyInstaller build spec
├── debug_run.bat         # Quick launch script (Windows)
├── requirements.txt      # Python dependencies
├── LICENSE               # MIT
└── README.md
```

---

## 🤝 Contributing

PRs are welcome! Some ideas:

- [ ] macOS / Linux support
- [ ] Drag-and-drop folder input
- [ ] Preset profiles (Fab Academy, WhatsApp, Email, etc.)
- [ ] Per-file size override
- [ ] Post-compression folder summary report

---

## 👤 Author

**NB6 (Nadec Biju)**

[![Fab Academy](https://img.shields.io/badge/Fab%20Academy-2026-blue)](https://fabacademy.org/2026/labs/kochi/students/nadec-biju/)
[![Instagram](https://img.shields.io/badge/@nb6__rules-E4405F?logo=instagram&logoColor=white)](https://www.instagram.com/nb6_rules/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nadec-biju/)
[![GitHub](https://img.shields.io/badge/GitHub-NB6RULES-181717?logo=github&logoColor=white)](https://github.com/NB6RULES)

---

## 📄 License

[MIT](LICENSE) © 2026 NB6
