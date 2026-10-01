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
SAMPLES = main.boards[next(iter(main.boards))].signalProcessor.samples_per_frame
# Effects that sleep() on purpose; timing them measures the sleep
SLEEPING = {name for name, opts in config.effectOptions.items() if "delay" in opts}


def load_frames(count):
    if not args.track:
        return [(np.random.randn(SAMPLES) * 3000).astype(np.float32) for _ in range(count)]
    # Skip the intro so the sample has music in it
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "45", "-i", os.path.join(MUSIC_DIR, args.track),
                          "-f", "s16le", "-ac", "1", "-ar", str(config.settings["configuration"]["MIC_RATE"]), "-"],
                         check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    frames = [audio[i * SAMPLES:(i + 1) * SAMPLES] for i in range(len(audio) // SAMPLES)]
    return (frames * (count // len(frames) + 1))[:count]


def time_effect(effect, frames):
    """Mirrors microphone_update, timing each stage"""
    totals = {"dsp": 0.0, "render": 0.0, "send": 0.0}
    boards = main.boards
    for board in boards.values():
        board.config["current_effect"] = effect
    render_boards = [max(boards.values(), key=lambda b: b.config["N_PIXELS"])] if config.settings["sync"] \
        else list(boards.values())

    for samples in frames:
        start = time.perf_counter()
        audio = {name: board.signalProcessor.update(samples) for name, board in boards.items()}
        after_dsp = time.perf_counter()
        outputs = {}
        for board in render_boards:
            data = audio[board.board]
            output = board.visualizer.get_vis(data["mel"], data["vol"] > config.settings["configuration"]["MIN_VOLUME_THRESHOLD"])
            outputs[board.board] = output * config.settings["brightness"]
        after_render = time.perf_counter()
        for name, board in boards.items():
            board.esp.show(outputs.get(name, outputs[render_boards[0].board]))
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
        if effect in SLEEPING:
            results.append((effect, None))
            continue
        results.append((effect, time_effect(effect, frames)))

    print("{:<16}{:>8}{:>8}{:>8}{:>8}  budget".format("effect", "dsp", "render", "send", "total"))
    timed = sorted((r for r in results if r[1]), key=lambda r: -sum(r[1].values()))
    for effect, t in timed:
        total = sum(t.values())
        bar = "#" * min(40, int(40 * total / FRAME_BUDGET_MS))
        print("{:<16}{:>8.2f}{:>8.2f}{:>8.2f}{:>8.2f}  {}".format(effect, t["dsp"], t["render"], t["send"], total, bar))
    for effect, _ in results:
        if effect in SLEEPING:
            delay = config.effectOptions[effect]["delay"]
            print("{:<16}  sleeps {:.0f} ms per board every frame (effect option 'delay')".format(effect, delay * 1000))


if __name__ == "__main__":
    main_()
