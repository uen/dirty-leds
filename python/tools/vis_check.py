"""Check how every effect behaves on real songs

    python3 tools/vis_check.py                     # every track in music/
    python3 tools/vis_check.py "test/02 Breakdown and drop.wav" song.mp3

Runs each track through the audio pipeline and every effect on a 150 LED strip
(--leds to change)
and reports, per effect:

    lit     share of LEDs visibly on, on average
    loud    average brightness while the music is big (intensity > 0.7)
    quiet   average brightness while it is small (intensity < 0.3)
    motion  how much the strip changes from frame to frame

and flags effects that are too dim, saturated, don't follow the song's
dynamics, or barely move. The aim is effects that look good on any song
without tuning, so the same numbers should come out healthy across tracks.
"""
import argparse
import copy
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DIRTY_LEDS_CONFIG", "rooms/flat.json")

import numpy as np  # noqa: E402
import config  # noqa: E402
import main  # noqa: E402
from lib.audio import MUSIC_DIR, list_tracks  # noqa: E402

LIT_LEVEL = 30  # a channel above this counts as visibly on
STRIP = 150  # default strip length, --leds to change


def decode(track):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(MUSIC_DIR, track),
                          "-f", "s16le", "-ac", "1", "-ar", str(config.settings["configuration"]["MIC_RATE"]), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32)


def strip_boards(effects):
    """A separate 150 LED board per effect, so each keeps its own state"""
    template = next(iter(main.boards.values()))
    boards = {}
    for effect in effects:
        board = main.Board(template.board)
        board.config = dict(template.config, N_PIXELS=args.leds, current_effect=effect)
        board.effectConfig = copy.deepcopy(template.effectConfig)
        board.visualizer = main.Visualizer(board)
        board.signalProcessor = main.DSP(board)
        boards[effect] = board
    return boards


def check(track, effects):
    audio = decode(track)
    samples = main.boards[next(iter(main.boards))].signalProcessor.analyser.samples_per_frame
    boards = strip_boards(effects)
    lit = {e: [] for e in effects}
    level = {e: [] for e in effects}
    motion = {e: [] for e in effects}
    previous = {}
    intensity = []
    beats = 0
    for i in range(len(audio) // samples):
        analysis = main.analyse(audio[i * samples:(i + 1) * samples])
        data = next(iter(analysis.values()))
        features = main.music.current
        intensity.append(features.intensity)
        beats += features.beat
        for effect, board in boards.items():
            frame = np.clip(main.render(board, data) / config.settings["brightness"], 0, 255)
            peak = frame.max(axis=0)
            lit[effect].append(np.mean(peak > LIT_LEVEL))
            level[effect].append(np.mean(peak) / 255)
            if effect in previous:
                motion[effect].append(np.mean(np.abs(frame - previous[effect])) / 255)
            previous[effect] = frame

    intensity = np.array(intensity)
    loud, quiet = intensity > 0.7, intensity < 0.3
    minutes = len(intensity) / config.settings["configuration"]["FPS"] / 60
    print("\n{}  ({:.0f} s, tempo {:.0f}, {:.0f} beats/min, {:.0f}% loud / {:.0f}% quiet)".format(
        track, minutes * 60, main.music.current.tempo, beats / minutes, 100 * loud.mean(), 100 * quiet.mean()))
    print("  {:<16}{:>6}{:>7}{:>7}{:>8}   ".format("effect", "lit", "loud", "quiet", "motion"))
    for effect in effects:
        lv = np.array(level[effect])
        loud_level = lv[loud].mean() if loud.any() else float("nan")
        quiet_level = lv[quiet].mean() if quiet.any() else float("nan")
        share, move = np.mean(lit[effect]), np.mean(motion[effect]) if motion[effect] else 0.0
        notes = []
        if share < 0.15:
            notes.append("dim")
        if share > 0.9:
            notes.append("saturated")
        if loud.any() and quiet.any() and not board_is_ambient(boards[effect]) and loud_level < 1.3 * quiet_level:
            notes.append("ignores dynamics")
        if move < 0.005 and not board_is_ambient(boards[effect]):
            notes.append("static")
        print("  {:<16}{:>6.0%}{:>7.2f}{:>7.2f}{:>8.3f}   {}".format(
            effect, share, loud_level, quiet_level, move, ", ".join(notes)))


def board_is_ambient(board):
    return board.visualizer.effects[board.config["current_effect"]].nonReactive


def main_():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tracks", nargs="*", help="files in music/ (default: all)")
    parser.add_argument("--effects", help="comma separated effects (default: all music-reactive ones)")
    parser.add_argument("--leds", type=int, default=STRIP, help="strip length to test on (default %(default)s)")
    global args
    args = parser.parse_args()
    config.settings["sync"] = False
    for board in main.boards.values():
        board.esp._ip, board.esp._port = "127.0.0.1", 9
    template = next(iter(main.boards.values()))
    effects = args.effects.split(",") if args.effects else \
        [name for name, effect in template.visualizer.effects.items() if not effect.nonReactive]
    for track in args.tracks or list_tracks():
        check(track, effects)


if __name__ == "__main__":
    main_()
