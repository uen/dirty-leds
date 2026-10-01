"""Time each stage of the per-frame pipeline for every effect

    python3 tools/benchmark.py --config rooms/flat.json --track "test/01 Four on the floor 120bpm.wav"

Feeds decoded audio through the same path as main.microphone_update, without
the real-time pacing, and reports milliseconds per frame for DSP, effect
rendering and sending. At 60 FPS the whole frame has 16.7 ms.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--config", default="rooms/flat.json")
parser.add_argument("--track", help="file in music/ to use as input (default: random noise)")
parser.add_argument("--frames", type=int, default=120, help="frames per effect")
parser.add_argument("--no-sync", action="store_true", help="render every board separately")
args = parser.parse_args()
os.environ["DIRTY_LEDS_CONFIG"] = args.config

import numpy as np  # noqa: E402
import config  # noqa: E402
import main  # noqa: E402
from lib.audio import MUSIC_DIR  # noqa: E402

FRAME_BUDGET_MS = 1000 / config.settings["configuration"]["FPS"]
SAMPLES = main.boards[next(iter(main.boards))].signalProcessor.analyser.samples_per_frame


def load_frames(count):
    if not args.track:
        return [(np.random.randn(SAMPLES) * 3000).astype(np.float32) for _ in range(count)]
    rate = config.settings["configuration"]["MIC_RATE"]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(MUSIC_DIR, args.track),
                          "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"],
                         check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    # Skip the intro of long tracks so the sample has music in it
    if len(audio) > 60 * rate:
        audio = audio[45 * rate:]
    frames = [audio[i * SAMPLES:(i + 1) * SAMPLES] for i in range(len(audio) // SAMPLES)]
    if not frames:
        raise SystemExit("Track is shorter than one frame: {}".format(args.track))
    return (frames * (count // len(frames) + 1))[:count]


def time_effect(effect, frames):
    """Times each stage of main.microphone_update"""
    totals = {"dsp": 0.0, "render": 0.0, "send": 0.0}
    for board in main.boards.values():
        board.config["current_effect"] = effect
    for samples in frames:
        start = time.perf_counter()
        audio = main.analyse(samples)
        after_dsp = time.perf_counter()
        outputs = main.render_all(audio)
        after_render = time.perf_counter()
        main.send_all(outputs)
        end = time.perf_counter()
        totals["dsp"] += after_dsp - start
        totals["render"] += after_render - after_dsp
        totals["send"] += end - after_render
    return {stage: 1000 * total / len(frames) for stage, total in totals.items()}


def main_():
    config.settings["sync"] = not args.no_sync
    # Point every board at a dead local port so nothing reaches real strips
    for board in main.boards.values():
        board.esp._ip, board.esp._port = "127.0.0.1", 9
    frames = load_frames(args.frames)
    print("{} boards, {} LEDs, sync {}, {} frames per effect, budget {:.1f} ms\n".format(
        len(main.boards), sum(b.config["N_PIXELS"] for b in main.boards.values()),
        "on" if config.settings["sync"] else "off", len(frames), FRAME_BUDGET_MS))

    results = []
    for effect in main.boards[next(iter(main.boards))].visualizer.effects:
        results.append((effect, time_effect(effect, frames)))

    print("{:<16}{:>8}{:>8}{:>8}{:>8}  budget".format("effect", "dsp", "render", "send", "total"))
    timed = sorted((r for r in results if r[1]), key=lambda r: -sum(r[1].values()))
    for effect, t in timed:
        total = sum(t.values())
        bar = "#" * min(40, int(40 * total / FRAME_BUDGET_MS))
        print("{:<16}{:>8.2f}{:>8.2f}{:>8.2f}{:>8.2f}  {}".format(effect, t["dsp"], t["render"], t["send"], total, bar))


if __name__ == "__main__":
    main_()
