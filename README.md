# 🌌 AsciiCell Lab

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Engine: Delta](https://img.shields.io/badge/Engine-Delta--Patching-orange.svg)](file:///home/zenoguy/Desktop/AsciiCell/engines/delta.py)

**AsciiCell Lab** is a high-performance, research-grade terminal engine designed for real-time webcam-to-ASCII rendering. Built with pluggable experimentation in mind, it serves as the backbone for analyzing cellular automata, frame-differencing optimizations, and visually stunning digital aesthetics.

---

## ⚡ The Science of the Engine

Unlike simple scripts, the **AsciiCell Lab** is an experimental infrastructure designed for publication-ready results.

- **`delta` Engine**: Implements per-cell ANSI cursor positioning (`\033[r;cH`) to selectively patch only regions of the frame that have changed beyond a configurable threshold.
- **`baseline` Engine**: A deterministic full-frame recompute engine used as the research ground truth for benchmarking.
- **Auto-Resolution**: Real-time terminal dimension detection with dynamic resizing and aspect ratio correction (0.5x height scale).

---

## 🌈 Visual Identities

| Mode | Aesthetic | Palette |
| :--- | :--- | :--- |
| **Cyberpunk** | Neon High-Tech | `Purple` → `Cyan` → `Neon Pink` |
| **Matrix** | The Digital Rain | `Deep Forest Green` |
| **Blood** | Dark Crimson | `Black` → `Pure Red` |
| **Amber** | Retro Hacker | `Classic Terminal Amber` |
| **Heatmap** | Intensity Analysis | `Blue` → `Green` → `Yellow` → `Red` |

---

## 🛠️ Installation

```bash
# Clone the lab
git clone https://github.com/yourusername/ascii_ca_lab.git
cd ascii_ca_lab

# Install dependencies (requires OpenCV and NumPy)
pip install -r requirements.txt
```

---

## 🚀 Quick Start

Launch the lab with the **Delta engine** and **Cyberpunk** aesthetics:

```bash
python main.py --auto --engine delta --color cyberpunk
```

### Advanced Usage

| Flag | Description |
| :--- | :--- |
| `--engine [baseline\|delta]` | Select the rendering algorithm. |
| `--color [mode]` | Set the aesthetic palette. |
| `--auto` | Fill the entire terminal screen. |
| `--fps [N]` | Target framerate (default: 30). |
| `--charset [name]` | Choose between classic (10-level) or extended (70-level). |
| `--threshold [0.05]` | Sensitivity for the delta engine patching. |
| `--no-save` | Disable raw `.npy` frame dumping. |

---

## 🔬 Experimental Infrastructure

### CSV Research Logging
Every session generates a timestamped CSV in `logs/` containing:
- `frame_id`, `fps`, `proc_ms`
- `changed_cells` (Primary metric for delta-patching efficiency)

### Data Persistence
Enable `save_frames` in `configs/default.yaml` to dump raw `float32` grayscale frames as `.npy` files for perfect reproducibility and figure generation for your papers.

---

## 📂 Project Architecture

```text
/ascii_ca_lab
 ├── core/
 │    ├── capture.py        # Low-latency webcam input
 │    ├── preprocess.py     # Resize, grayscale, normalization
 │    ├── ascii_map.py      # Vectorized intensity → char mapping
 │    ├── color.py          # ANSI 24-bit Truecolor palette engine
 │    └── renderer.py       # Anti-flicker terminal rendering (\033[H)
 │
 ├── engines/
 │    ├── baseline.py       # Standard ground-truth engine
 │    └── delta.py          # Diff-patching experimental engine
 │
 ├── utils/
 │    ├── fps.py            # High-precision rolling-window FPS
 │    ├── logger.py         # Buffered CSV research logger
 │    └── frame_saver.py    # .npy frame + metadata persistence
 │
 └── configs/
      └── default.yaml      # Centralized research tunables
```

---

## 📜 License
AsciiCell Lab is open-sourced under the MIT License. Built for the intersection of art and computational science.
