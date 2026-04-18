"""
main.py
-------
AsciiCell Lab — Entry Point

Loads config, wires dependencies, selects and runs engine.

Usage:
  python main.py                              # defaults from config
  python main.py --engine delta               # override engine
  python main.py --color cyberpunk            # override color mode
  python main.py --color matrix --fps 24      # multiple overrides
  python main.py --no-save                    # disable frame saving
  python main.py --no-log                     # disable CSV logging
  python main.py --charset extended           # use extended charset
  python main.py --config configs/custom.yaml # custom config

Ctrl+C to exit cleanly.
"""

import argparse
import sys
from pathlib import Path

import yaml

from core.capture      import Capture
from core.renderer     import Renderer
from engines.baseline  import BaselineEngine
from engines.delta     import DeltaEngine
from utils.fps         import FPSTracker
from utils.logger      import FrameLogger
from utils.frame_saver import FrameSaver
from core.ascii_map    import CHARSETS


# ------------------------------------------------------------------
# Engine registry — add new engines here
# ------------------------------------------------------------------

ENGINE_REGISTRY = {
    "baseline": BaselineEngine,
    "delta":    DeltaEngine,
}

VALID_COLOR_MODES = {
    "none", "256", "truecolor",
    "matrix", "cyberpunk", "blood", "amber", "heatmap", "neon",
}


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AsciiCell Lab — Terminal Webcam ASCII Renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Color modes:
  none        — grayscale chars, no ANSI color (research baseline)
  256         — xterm 256-color approximation
  truecolor   — 24-bit ANSI per character
  matrix      — deep green glow
  cyberpunk   — purple → cyan → neon pink  [RECOMMENDED]
  blood       — black → deep crimson
  amber       — retro hacker amber
  heatmap     — blue → green → yellow → red
  neon        — electric cyan → lime → yellow  [NEW]

Engines:
  baseline    — full recompute every frame (research baseline)
  delta       — only update changed cells (experimental)
        """,
    )
    p.add_argument("--config",   default="configs/default.yaml",
                   help="Path to YAML config (default: configs/default.yaml)")
    p.add_argument("--engine",   choices=list(ENGINE_REGISTRY.keys()),
                   help="Override renderer engine from config")
    p.add_argument("--color",    dest="color_mode",
                   choices=sorted(VALID_COLOR_MODES),
                   help="Override color mode from config")
    p.add_argument("--fps",      type=int,
                   help="Override target FPS from config")
    p.add_argument("--width",    type=int,
                   help="Override capture/output width")
    p.add_argument("--height",   type=int,
                   help="Override capture/output height")
    p.add_argument("--charset",  choices=list(CHARSETS.keys()),
                   help="Override ASCII charset (classic|extended|minimal|blocks)")
    p.add_argument("--device",   type=int,
                   help="Override webcam device index")
    p.add_argument("--no-save",  action="store_true",
                   help="Disable saving raw frames to disk")
    p.add_argument("--no-log",   action="store_true",
                   help="Disable CSV frame logging")
    p.add_argument("--auto",     action="store_true",
                   help="Auto-detect terminal size and fill screen")
    p.add_argument("--aspect-ratio", type=float,
                   help="Height scale correction (default: 0.5)")
    p.add_argument("--contrast",     choices=["none", "normalize", "equalize"],
                   help="Preprocessing contrast mode")
    p.add_argument("--max-frames",   type=int,
                   help="Max frames to keep on disk (default: 1000)")
    p.add_argument("--threshold", type=float,
                   help="Delta engine change threshold (default: 0.05)")
    return p


# ------------------------------------------------------------------
# Config loading + CLI override
# ------------------------------------------------------------------

def load_config(config_path: str, args: argparse.Namespace) -> dict:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Apply CLI overrides on top of config
    if args.engine:
        cfg["renderer"]["engine"] = args.engine
    if args.color_mode:
        cfg["renderer"]["color_mode"] = args.color_mode
    if args.fps:
        cfg["capture"]["target_fps"] = args.fps
    if args.width:
        cfg["capture"]["width"] = args.width
    if args.height:
        cfg["capture"]["height"] = args.height
    if args.charset:
        cfg["ascii"]["charset"] = CHARSETS[args.charset]
    if args.device is not None:
        cfg["capture"]["device_index"] = args.device
    if args.no_save:
        cfg["data"]["save_frames"] = False
    if args.no_log:
        cfg["logging"]["enabled"] = False
    if args.auto:
        cfg["capture"]["auto_size"] = True
    if args.aspect_ratio is not None:
        cfg["capture"]["aspect_ratio"] = args.aspect_ratio
    if args.contrast:
        cfg["capture"]["contrast_mode"] = args.contrast
    if args.max_frames is not None:
        cfg["data"]["max_saved_frames"] = args.max_frames
    if args.threshold is not None:
        cfg.setdefault("delta", {})["threshold"] = args.threshold

    return cfg


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(str(config_path), args)

    # -- Print session header --
    res_str = "AUTO" if cfg["capture"].get("auto_size") else f"{cfg['capture']['width']}×{cfg['capture']['height']}"
    print(
        f"\n  AsciiCell Lab\n"
        f"  engine:   {cfg['renderer']['engine']}\n"
        f"  color:    {cfg['renderer']['color_mode']}\n"
        f"  contrast: {cfg['capture'].get('contrast_mode', 'none')}\n"
        f"  res:      {res_str}\n"
        f"  fps:      {cfg['capture']['target_fps']}\n"
        f"  frames:   {'saving' if cfg['data'].get('save_frames') else 'OFF'}\n"
        f"  log:      {'enabled' if cfg['logging'].get('enabled') else 'OFF'}\n"
        f"\n  Starting in 1 second... (Ctrl+C to quit)\n"
    )

    import time
    time.sleep(1.0)

    # -- Wire up components --
    capture     = Capture(
        device_index = cfg["capture"]["device_index"],
        width        = cfg["capture"]["width"],
        height       = cfg["capture"]["height"],
    )
    renderer    = Renderer()
    fps_tracker = FPSTracker(window_size=30)

    # Logger
    logger = None
    if cfg["logging"].get("enabled", True):
        logger = FrameLogger(
            log_dir             = cfg["logging"]["log_dir"],
            log_interval_frames = cfg["logging"].get("log_interval_frames", 30),
        )

    # Frame saver
    frame_saver = None
    if cfg["data"].get("save_frames", False):
        metadata = {
            "resolution":  [cfg["capture"]["width"], cfg["capture"]["height"]],
            "target_fps":  cfg["capture"]["target_fps"],
            "charset":     cfg["ascii"]["charset"],
            "color_mode":  cfg["renderer"]["color_mode"],
            "engine":      cfg["renderer"]["engine"],
        }
        frame_saver = FrameSaver(
            frame_dir  = cfg["data"]["frame_dir"],
            metadata   = metadata,
            max_frames = cfg["data"]["max_saved_frames"],
        )

    # -- Select engine class --
    engine_name  = cfg["renderer"]["engine"]
    EngineClass  = ENGINE_REGISTRY.get(engine_name)
    if EngineClass is None:
        print(f"[ERROR] Unknown engine: {engine_name!r}", file=sys.stderr)
        sys.exit(1)

    # -- Run --
    with capture, renderer:
        engine = EngineClass(
            capture     = capture,
            renderer    = renderer,
            fps_tracker = fps_tracker,
            logger      = logger,
            frame_saver = frame_saver,
            config      = cfg,
        )
        engine.run()

    # Cleanup loggers after context managers exit
    if logger:
        logger.close()
        print(f"\n  Log saved → {logger.filepath}")
    if frame_saver:
        print(f"  Frames saved → {frame_saver.frame_dir}/")


if __name__ == "__main__":
    main()
