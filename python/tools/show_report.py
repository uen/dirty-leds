"""Judge how good the auto show looks on a song, without watching it

    python3 tools/show_report.py "song.mp3"                 # report + music/.reports/song.png
    python3 tools/show_report.py "song.mp3" --config rooms/living-room.json --seed 3

Renders the whole track through the auto show offline (with its
pre-analysis, as when it plays), captures every strip's LEDs every frame, and
produces:

  a lightogram   one image of the whole show: time left to right, each strip
                 a band with one row per LED, under the song's sections,
                 intensity and drops
  a score card   lighting-design checks with targets:
                   follows    light energy over time vs the song's intensity
                   drops      how much bigger peak sections look than calm ones,
                              and the jump in the moment after each drop
                   sections   how much the light changes at section boundaries
                              compared with random moments
                   on beat    how much more the light changes on beats than off
                   smooth     how much neighbouring LEDs move together (high =
                              structured motion, low = scattered flicker)
                   jitter     how often LEDs flip back and forth frame to frame
                   variety    effects used, share of time in unison
                   fresh      longest stretch with no visible change in the light
                   dominance  share of strip-time taken by the most used effect
                   colour     distinct hues on show during peak sections
                   comfort    average brightness and coverage in peaks
"""
import argparse
import os
import random
import subprocess
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("track", help="file in music/")
parser.add_argument("--config", default="rooms/flat.json", help="room to render (default %(default)s)")
parser.add_argument("--seed", type=int, default=1, help="random seed for the show's choices")
parser.add_argument("--style", choices=["mixed", "freestyle", "effects"], help="show style (default: the config's)")
parser.add_argument("--out", help="image path (default music/.reports/<track>.png)")
args = parser.parse_args()
os.environ["DIRTY_LEDS_CONFIG"] = args.config

import numpy as np  # noqa: E402
import config  # noqa: E402
import main  # noqa: E402
from lib.analysis import analyse_file  # noqa: E402
from lib.audio import MUSIC_DIR  # noqa: E402
from lib.features import Envelope  # noqa: E402

FPS = config.settings["configuration"]["FPS"]
TIER_COLOURS = {"calm": "#3b4a5c", "groove": "#7a6a3e", "peak": "#ffb547"}


def render(track):
    """Every strip's frames for the whole track, plus what the show chose when"""
    random.seed(args.seed)
    np.random.seed(args.seed)
    main.director.rng.seed(args.seed)
    analysis = analyse_file(os.path.join(MUSIC_DIR, track))
    main.library = types.SimpleNamespace(get=lambda _: analysis)
    main.audio = types.SimpleNamespace(track=track, track_frame=0)
    for board in main.boards.values():
        board.esp._ip, board.esp._port = "127.0.0.1", 9
        board.config["current_effect"] = "Auto"
        if args.style:
            board.effectConfig["Auto"]["style"] = args.style
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(MUSIC_DIR, track), "-f", "s16le",
                          "-ac", "1", "-ar", str(config.settings["configuration"]["MIC_RATE"]), "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    hop = main.boards[next(iter(main.boards))].signalProcessor.analyser.samples_per_frame
    frames = min(len(audio) // hop, analysis.frames)

    looks = []
    new_look, cast_cue = main.director._new_look, main.director._cast_cue

    def remember(reason):
        look = main.director.look
        looks.append((main.audio.track_frame, reason, dict(look["strips"]),
                      look.get("signature") or "/".join(sorted(set(look["strips"].values())))))

    def record(reason, features):
        new_look(reason, features)
        remember(reason)

    def record_cue(cue, features):
        cast_cue(cue, features)
        remember("drop" if cue.kind == "drop" else cue.kind)
    main.director._new_look = record
    main.director._cast_cue = record_cue

    strips = {name: np.zeros((frames, board.config["N_PIXELS"], 3), dtype=np.uint8) for name, board in main.boards.items()}
    for frame in range(frames):
        main.audio.track_frame = frame
        main.microphone_update(audio[frame * hop:(frame + 1) * hop])
        for name, board in main.boards.items():
            leds = np.frombuffer(board.esp.last_frame, dtype=np.uint8).reshape(-1, 3)
            strips[name][frame, :len(leds)] = leds
    return analysis, strips, looks, frames


def score(analysis, strips, looks, frames):
    light = np.concatenate([s.astype(np.float32) / 255 for s in strips.values()], axis=1)  # frames x leds x 3
    level = light.max(axis=2)  # brightness per LED
    energy = level.mean(axis=1)
    smooth_energy = Envelope(0.3, 0.3, 1 / FPS)
    energy_1s = np.array([smooth_energy.update(e) for e in energy])
    intensity = analysis.intensity[:frames]
    tiers = np.array([analysis.sections[i].tier for i in analysis.section_index[:frames]])
    checks = []

    def check(name, value, target, ok, detail):
        checks.append((name, value, target, ok, detail))

    follows = float(np.corrcoef(energy_1s, intensity)[0, 1])
    check("follows", f"{follows:.2f}", ">= 0.6", follows >= 0.6, "light energy vs song intensity over time")

    calm, peak = tiers == "calm", tiers == "peak"
    if calm.any() and peak.any():
        ratio = energy[peak].mean() / max(energy[calm].mean(), 1e-6)
        check("drops", f"{ratio:.1f}x", ">= 2.5x", ratio >= 2.5, "peak sections vs calm sections, mean brightness")
    jumps = []
    for drop in analysis.drops:
        if FPS <= drop < frames - FPS // 2:
            jumps.append(energy[drop:drop + FPS // 2].mean() / max(energy[drop - FPS:drop - FPS // 4].mean(), 1e-6))
    if jumps:
        check("drop hit", f"{np.mean(jumps):.1f}x", ">= 5x", np.mean(jumps) >= 5,
              "brightness in the half second after drops vs the second before")
    landings = [energy[d:d + 2 * FPS].mean() for d in analysis.drops if d + 2 * FPS < frames]
    if len(landings) >= 2:
        check("escalation", " -> ".join(f"{x:.2f}" for x in landings), "last >= first",
              landings[-1] >= 0.95 * landings[0], "brightness in the 2 s after each drop, in order")

    # How different the light is in the two seconds after a moment vs before it, in
    # colour as well as brightness: a palette change at the same brightness is a change
    window = 2 * FPS
    def change(at):
        before, after = light[max(0, at - window):at].mean(axis=0), light[at:at + window].mean(axis=0)
        return float(np.abs(after - before).mean())
    boundaries = [s.start for s in analysis.sections[1:] if window <= s.start < frames - window]
    rng = np.random.default_rng(0)
    baseline = np.median([change(int(t)) for t in rng.integers(window, frames - window, 60)])
    if boundaries:
        salience = np.mean([change(b) for b in boundaries]) / max(baseline, 1e-6)
        check("sections", f"{salience:.1f}x", ">= 2x", salience >= 2, "light change at section boundaries vs random moments")

    # Only sections with a real beat count: ambient music has no beat to be on
    rhythmic = np.zeros(frames, dtype=bool)
    for sec in analysis.sections:
        if sec.activity >= 0.4:
            rhythmic[sec.start:min(sec.end, frames)] = True
    flux = np.maximum(np.diff(level, axis=0), 0).mean(axis=1)
    near_beat = np.zeros(frames - 1, dtype=bool)
    for b in analysis.beat_frames:
        near_beat[max(0, b - 2):min(frames - 1, b + 3)] = True
    if rhythmic[:-1].sum() > 10 * FPS:
        on, off = near_beat & rhythmic[:-1], ~near_beat & rhythmic[:-1]
        on_beat = flux[on].mean() / max(flux[off].mean(), 1e-6)
        check("on beat", f"{on_beat:.1f}x", ">= 1.5x", on_beat >= 1.5, "light rising on beats vs off them (rhythmic parts)")

    delta = np.diff(level, axis=0)
    neighbours = []
    for s in strips.values():
        d = np.diff(s.astype(np.float32).max(axis=2) / 255, axis=0)
        a, b = d[:, :-1].ravel(), d[:, 1:].ravel()
        moving = (np.abs(a) + np.abs(b)) > 0.02
        if moving.sum() > 100:
            neighbours.append(np.corrcoef(a[moving], b[moving])[0, 1])
    coherence = float(np.mean(neighbours)) if neighbours else 1.0
    check("smooth", f"{coherence:.2f}", ">= 0.7", coherence >= 0.7, "neighbouring LEDs moving together")

    flips = (np.sign(delta[1:]) * np.sign(delta[:-1]) < 0) & (np.abs(delta[1:]) > 0.05) & (np.abs(delta[:-1]) > 0.05)
    jitter = float(flips.mean())
    check("jitter", f"{jitter:.1%}", "<= 2%", jitter <= 0.02, "LEDs flipping brighter/darker frame to frame")

    effects = {e for _, _, s, _ in looks for e in s.values()}
    signatures = {sig for _, _, _, sig in looks}
    # Strips "match" when their light looks alike: similar colour and brightness over time
    names = list(strips)
    alike = 0.0
    if len(names) > 1:
        means = np.stack([strips[n].astype(np.float32).mean(axis=1) for n in names])  # strips x frames x 3
        spread = np.abs(means - means.mean(axis=0, keepdims=True)).mean(axis=(0, 2))
        alike = float((spread < 6).mean())
    # About one new look every 20 s, at least 2
    wanted = max(2, int(frames / FPS / 20))
    check("variety", f"{len(signatures)} looks, {len(effects)} effects, {alike:.0%} alike",
          f">= {wanted} looks, <= 40%", len(signatures) >= wanted and alike <= 0.4,
          "distinct looks, share of time all strips look alike")

    # Longest stretch where the light's overall look (2 s averages) doesn't visibly
    # change. Calm parts may sit still for longer than grooves and peaks
    step = FPS
    starts = list(range(0, frames - window, step))
    blocks = [light[i:i + window].mean(axis=0) for i in starts]
    changes = [float(np.abs(b - a).mean()) for a, b in zip(blocks[:-2], blocks[2:])]
    threshold = max(0.03, 0.5 * float(np.median(changes))) if changes else 0.03
    longest = {"calm": 0, "moving": 0}
    run, run_kind = 0, None
    for i, c in enumerate(changes):
        at = min(starts[i] + window, frames - 1)
        # Calm or sparse parts may sit still for longer than rhythmic grooves and peaks
        kind = "calm" if tiers[at] == "calm" or not rhythmic[at] else "moving"
        run = run + 1 if c < threshold and kind == run_kind else (1 if c < threshold else 0)
        run_kind = kind
        longest[kind] = max(longest[kind], run)
    check("fresh", f"{longest['moving']} s grooves/peaks, {longest['calm']} s calm", "<= 12 s, <= 20 s",
          longest["moving"] <= 12 and longest["calm"] <= 20, "longest stretch without a visible change")

    # Freestyle changes its look from scene to scene, so it counts per scene rather than as one effect
    def kind(effect, signature):
        return f"Freestyle ({signature})" if effect == "Freestyle" else effect
    usage = {}
    for i, (start, _, s, sig) in enumerate(looks):
        end = looks[i + 1][0] if i + 1 < len(looks) else frames
        for effect in s.values():
            usage[kind(effect, sig)] = usage.get(kind(effect, sig), 0) + end - start
    if usage:
        top_effect = max(usage, key=usage.get)
        share = usage[top_effect] / sum(usage.values())
        check("dominance", f"{top_effect} {share:.0%}", "<= 35%", share <= 0.35, "share of strip-time of the most used effect")
        # Same on each strip on its own: one strip shouldn't keep showing the same thing
        worst = (None, None, 0.0)
        for name in strips:
            per = {}
            for i, (start, _, s, sig) in enumerate(looks):
                end = looks[i + 1][0] if i + 1 < len(looks) else frames
                key = kind(s.get(name), sig)
                per[key] = per.get(key, 0) + end - start
            effect = max(per, key=per.get)
            if per[effect] / frames > worst[2]:
                worst = (name, effect, per[effect] / frames)
        if frames >= 90 * FPS:
            check("per strip", f"{worst[0]}: {worst[1]} {worst[2]:.0%}", "<= 45%", worst[2] <= 0.45,
                  "most any one strip spends on a single effect")

    def hue_count(mask):
        colours = light[mask][level[mask] > 0.2]
        if not len(colours):
            return 0
        r, g, b = colours[:, 0], colours[:, 1], colours[:, 2]
        hue = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) + 360) % 360
        bins = np.bincount((hue // 30).astype(int), minlength=12) / len(hue)
        return int((bins >= 0.08).sum())

    peak_sections = [sec for sec in analysis.sections if sec.tier == "peak" and sec.start < frames]
    if peak_sections:
        counts = []
        for sec in peak_sections:
            mask = np.zeros(frames, dtype=bool)
            mask[sec.start:min(sec.end, frames)] = True
            counts.append(hue_count(mask))
        check("colour", f"{min(counts)} hues (weakest peak)", ">= 3", min(counts) >= 3,
              "distinct hues (30 degree bins, 8%+ each) in the least colourful peak section")

    lit_peak = float((level[peak] > 0.12).mean()) if peak.any() else 0.0
    mean_level = float(level.mean())
    check("comfort", f"{mean_level:.2f} avg, {lit_peak:.0%} lit in peaks", "avg <= 0.35",
          mean_level <= 0.35, "overall brightness, coverage during peaks")
    return checks, energy_1s, intensity


def draw(track, analysis, strips, looks, frames, energy, intensity, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seconds = frames / FPS
    columns = int(seconds * 8)  # 8 columns per second
    edges = np.linspace(0, frames, columns + 1).astype(int)
    heights = [1.2] + [1.0] * len(strips)
    fig, axes = plt.subplots(len(strips) + 1, 1, figsize=(min(40, 6 + seconds / 6), 2 + 1.1 * len(strips)),
                             gridspec_kw={"height_ratios": heights}, sharex=True, facecolor="#1c1d20")
    top = axes[0]
    for section in analysis.sections:
        top.axvspan(section.start / FPS, section.end / FPS, color=TIER_COLOURS[section.tier], alpha=0.35, lw=0)
    t = np.arange(frames) / FPS
    top.plot(t, intensity, color="#e9e7e2", lw=1, label="song intensity")
    top.plot(t, energy / max(energy.max(), 1e-6), color="#7fd3ff", lw=1, label="light energy")
    for drop in analysis.drops:
        top.axvline(drop / FPS, color="white", lw=1.2)
    for start, reason, _, _ in looks:
        top.axvline(start / FPS, ymin=0.9, ymax=1, color="#ff7a6b" if reason == "drop" else "#8d9097", lw=1)
    top.set_ylim(0, 1.05)
    top.legend(loc="upper left", fontsize=7, facecolor="#232428", labelcolor="#e9e7e2", framealpha=0.8)
    top.set_title(f"{track}: tempo {analysis.tempo:.0f}, sections shaded calm/groove/peak, white lines are drops, "
                  "ticks are look changes", color="#e9e7e2", fontsize=9, loc="left")

    for axis, (name, data) in zip(axes[1:], strips.items()):
        # Mean colour of each LED over each column's frames
        image = np.stack([data[a:b].mean(axis=0) if b > a else data[a] for a, b in zip(edges[:-1], edges[1:])], axis=1)
        axis.imshow(image.astype(np.uint8), aspect="auto", interpolation="nearest",
                    extent=(0, seconds, data.shape[1], 0))
        axis.set_ylabel(name, color="#e9e7e2", fontsize=8, rotation=0, ha="right", va="center")
        axis.set_yticks([])
    for axis in axes:
        axis.set_facecolor("#08090b")
        axis.tick_params(colors="#8d9097", labelsize=7)
        for spine in axis.spines.values():
            spine.set_color("#36383d")
    axes[-1].set_xlabel("seconds", color="#8d9097", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())


def main_():
    analysis, strips, looks, frames = render(args.track)
    checks, energy, intensity = score(analysis, strips, looks, frames)
    print(f"\n{args.track}: {frames / FPS:.0f} s, {len(looks)} looks, room {args.config}\n")
    for name, value, target, ok, detail in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:<9} {value:<28} target {target:<14} {detail}")
    name = os.path.splitext(os.path.basename(args.track))[0] + (f" ({args.style})" if args.style else "")
    path = args.out or os.path.join(MUSIC_DIR, ".reports", name + ".png")
    draw(args.track, analysis, strips, looks, frames, energy, intensity, path)
    print(f"\n  lightogram: {path}")


if __name__ == "__main__":
    main_()
