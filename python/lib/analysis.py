"""Pre-analysis of music files, so the show knows what is coming

Real-time analysis only knows the past, so it lags: intensity has to be
smoothed before it can be trusted, and a drop can only be reacted to after it
lands. For a file the whole song can be analysed up front instead:

    intensity   smoothed with the future as well as the past, so it changes
                exactly when the music does
    beats       a beat grid from dynamic programming over the whole song's
                onsets, which follows small tempo drifts
    sections    where the music changes character (self-similarity novelty
                over beats) or energy, each rated calm / groove / peak from its
                energy; boundaries snapped to beats, drops pinned to the hit
                where the bass comes in
    groove      the repeating rhythm of each section: hits averaged over its bars
                at sixteenth-note steps, so effects can play the pattern back

Analysis runs in a separate process (it would otherwise compete with the live
loop for Python's GIL) and is cached in music/.analysis, so each file is only
analysed once. Live sources and tracks still being analysed fall back to the
real-time features.
"""
import hashlib
import json
import multiprocessing
import os
import queue
import subprocess
import threading
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter1d

import config
from lib.audio import MUSIC_DIR, list_tracks
from lib.features import (BASS, BINS_RANGE, INTENSITY_BASS, N_BINS, PREFERRED_TEMPO, SILENCE_DBFS, TEMPO_RANGE,
                          WINDOW, _band, _log_filterbank)

ANALYSIS_VERSION = 5
CACHE_DIR = os.path.join(MUSIC_DIR, ".analysis")
TIERS = ("calm", "groove", "peak")
TIER_START = (0.35, 0.72)
# The kick drum's fundamental, which settles which of a family of related tempos is the beat
SUB = (30, 80)
# Sections shorter than this many beats are merged into a neighbour
MIN_SECTION_BEATS = 16
STEPS_PER_BEAT = 4
STEPS_PER_BAR = 4 * STEPS_PER_BEAT
# Below this the bars don't follow one pattern closely enough to play it back
MIN_GROOVE_STRENGTH = 0.3


@dataclass
class Section:
    start: int  # frame
    end: int
    tier: str
    # 0-1, how much is being hit (onset activity on an absolute scale): sparse or
    # beatless music is low, dense dance music high
    activity: float = 1.0


@dataclass
class Pattern:
    pattern: list  # how hard each of the 16 steps of a bar is hit, 0-1
    accents: list  # steps the pattern hits
    strength: float  # 0-1, how closely the bars follow the pattern

    @property
    def reliable(self):
        return self.strength >= MIN_GROOVE_STRENGTH

    def to_dict(self):
        return {"pattern": [round(float(v), 2) for v in self.pattern], "accents": self.accents,
                "strength": round(self.strength, 2), "reliable": self.reliable}


@dataclass
class Groove:
    song: Pattern  # the whole song's pattern, used where a section is too short to learn its own
    sections: list  # per section: its Pattern, or None for calm sections
    hits: np.ndarray  # per frame: an accent of that section's pattern lands here
    steps: np.ndarray  # per frame: step of the bar, -1 where unknown

    def at_section(self, index):
        pattern = self.sections[index] if index < len(self.sections) else None
        return pattern if pattern is not None else None


class TrackAnalysis:
    """Per-frame intensity, beats, sections and groove for one track"""
    def __init__(self, fps, intensity, beats, sections, tempo, groove):
        self.fps = fps
        self.groove = groove
        self.intensity = intensity
        self.frames = len(intensity)
        self.beat_frames = beats
        self.sections = sections
        self.tempo = tempo
        self.beat = np.zeros(self.frames, dtype=bool)
        self.beat[beats[(beats >= 0) & (beats < self.frames)]] = True
        self.beat_phase, self.local_tempo = self._phases(beats)
        self.section_index = np.zeros(self.frames, dtype=np.int32)
        for i, section in enumerate(sections):
            self.section_index[section.start:section.end] = i
        self.drops = [s.start for i, s in enumerate(sections)
                      if s.tier == "peak" and i > 0 and TIERS.index(sections[i - 1].tier) < 2]

    def _phases(self, beats):
        phase = np.zeros(self.frames, dtype=np.float32)
        tempo = np.full(self.frames, self.tempo, dtype=np.float32)
        for start, end in zip(beats[:-1], beats[1:]):
            phase[start:end] = np.arange(end - start) / (end - start)
            tempo[start:end] = 60 * self.fps / (end - start)
        return phase, tempo

    def at(self, frame):
        """Everything known about one frame of the track"""
        frame = frame % self.frames
        index = self.section_index[frame]
        section = self.sections[index]
        next_drop = next((d for d in self.drops if d > frame), None)
        following = self.sections[index + 1] if index + 1 < len(self.sections) else None
        return {
            "intensity": float(self.intensity[frame]),
            "beat": bool(self.beat[frame]),
            "beat_phase": float(self.beat_phase[frame]),
            "tempo": float(self.local_tempo[frame]),
            "tier": section.tier,
            "section_change": frame == section.start and frame > 0,
            # Only counts down within the stretch leading into the drop
            "until_drop": (next_drop - frame) / self.fps
            if next_drop is not None and self.section_index[next_drop] == self.section_index[frame] + 1 else None,
            "position": frame / self.fps,
            "groove_hit": bool(self.groove.hits[frame]),
            "groove_strength": self._groove_strength(index),
            "bar_step": int(self.groove.steps[frame]),
            # The next section, for the countdown in the web interface
            "upcoming": None if following is None else {
                "tier": following.tier,
                "in": (following.start - frame) / self.fps,
                "drop": following.start in self.drops,
            },
        }

    def _groove_strength(self, index):
        pattern = self.groove.at_section(index)
        return pattern.strength if pattern is not None and pattern.reliable else 0.0

    def summary(self):
        return {
            "duration": self.frames / self.fps,
            "tempo": round(self.tempo, 1),
            "sections": [{"start": s.start / self.fps, "end": s.end / self.fps, "tier": s.tier,
                          "activity": round(s.activity, 2),
                          "groove": None if self.groove.at_section(i) is None else self.groove.at_section(i).to_dict()}
                         for i, s in enumerate(self.sections)],
            "drops": [d / self.fps for d in self.drops],
            "groove": self.groove.song.to_dict(),
        }

    def save(self, path):
        np.savez_compressed(path, intensity=self.intensity, beats=self.beat_frames,
                            sections=np.array([[s.start, s.end, TIERS.index(s.tier), s.activity] for s in self.sections]),
                            groove_hits=self.groove.hits, groove_steps=self.groove.steps,
                            meta=json.dumps({"fps": self.fps, "tempo": self.tempo,
                                             "groove_song": self.groove.song.to_dict(),
                                             "groove_sections": [None if p is None else p.to_dict()
                                                                 for p in self.groove.sections]}))

    @classmethod
    def load(cls, path):
        data = np.load(path)
        meta = json.loads(str(data["meta"]))
        sections = [Section(int(a), int(b), TIERS[int(t)], float(activity)) for a, b, t, activity in data["sections"]]
        def pattern(d):
            return None if d is None else Pattern(d["pattern"], d["accents"], d["strength"])
        groove = Groove(pattern(meta["groove_song"]), [pattern(d) for d in meta["groove_sections"]],
                        data["groove_hits"], data["groove_steps"])
        return cls(meta["fps"], data["intensity"], data["beats"], sections, meta["tempo"], groove)


def analyse_file(path, progress=lambda fraction: None):
    rate = config.settings["configuration"]["MIC_RATE"]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"],
                         capture_output=True, check=True).stdout
    return analyse_audio(np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 2.0**15, progress)


def analyse_audio(audio, progress=lambda fraction: None):
    """Analyse mono samples (-1 to 1) at MIC_RATE"""
    rate = config.settings["configuration"]["MIC_RATE"]
    fps = config.settings["configuration"]["FPS"]
    hop = rate // fps
    frames = len(audio) // hop
    if frames < fps * 5:
        raise ValueError("track is shorter than 5 seconds")
    progress(0.1)

    # Same windows the live analysis sees: the last WINDOW samples up to the end of each frame
    padded = np.concatenate((np.zeros(WINDOW - hop, dtype=np.float32), audio[:frames * hop]))
    freqs = np.fft.rfftfreq(WINDOW, 1.0 / rate)
    intensity_band, audible, kick_band = _band(freqs, *INTENSITY_BASS), _band(freqs, 100, 14000), _band(freqs, *SUB)
    window = np.hanning(WINDOW)
    filterbank = _log_filterbank(freqs, N_BINS, *BINS_RANGE)
    bins_db = np.zeros((frames, N_BINS))
    total_db, bass_db, flux, kick_flux = np.zeros(frames), np.zeros(frames), np.zeros(frames), np.zeros(frames)
    previous = previous_kick = None
    for start in range(0, frames, 2000):
        idx = np.arange(start, min(frames, start + 2000))
        chunk = np.lib.stride_tricks.sliding_window_view(padded, WINDOW)[idx * hop]
        spectrum = np.abs(np.fft.rfft(chunk * window, axis=1)) / (WINDOW / 4)
        power = spectrum ** 2
        total_db[idx] = 10 * np.log10(power.sum(axis=1) + 1e-12)
        bass_db[idx] = 10 * np.log10(power[:, intensity_band].sum(axis=1) + 1e-12)
        bins_db[idx] = 10 * np.log10(power @ filterbank.T + 1e-12)
        compressed = np.log1p(100 * spectrum[:, audible])
        before = np.vstack(([compressed[0]] if previous is None else [previous], compressed[:-1]))
        flux[idx] = np.maximum(compressed - before, 0).mean(axis=1)
        previous = compressed[-1]
        kick = np.log1p(100 * spectrum[:, kick_band])
        kick_before = np.vstack(([kick[0]] if previous_kick is None else [previous_kick], kick[:-1]))
        kick_flux[idx] = np.maximum(kick - kick_before, 0).mean(axis=1)
        previous_kick = kick[-1]
        progress(0.1 + 0.4 * idx[-1] / frames)

    rms = np.sqrt(np.mean(audio[:frames * hop].reshape(frames, hop) ** 2, axis=1))
    loudness = 20 * np.log10(rms + 1e-9)
    silent = loudness < SILENCE_DBFS

    beats, tempo = _track_beats(flux, kick_flux, fps)
    progress(0.75)
    parts = _energy_parts(bass_db - total_db, loudness, flux, silent, fps)
    intensity = np.where(silent, 0.0, gaussian_filter1d(_energy(*parts), 0.15 * fps, mode="nearest"))
    sections = _sections(intensity, parts[3], bins_db, loudness, flux, bass_db - total_db, beats, tempo, fps)
    groove = _groove(_onset_strength(flux, fps), beats, sections, frames)
    progress(0.95)
    return TrackAnalysis(fps, intensity.astype(np.float32), beats, sections, tempo, groove)


def _normalise(values, mask, min_range):
    """0-1 against the song's own 10th to 90th percentile"""
    if not mask.any():
        return np.zeros_like(values)
    low, high = np.percentile(values[mask], [10, 90])
    low = min(low, high - min_range)
    return np.clip((values - low) / (high - low), 0, 1)


def _energy_parts(bass_share, loudness, flux, silent, fps):
    """How big the music is, in parts: three judged against the song itself (so
    every song has highs and lows) and one absolute (how much is being hit)"""
    audible = ~silent

    def smooth(values, seconds):
        return gaussian_filter1d(values, seconds * fps, mode="nearest")

    bass_relative = _normalise(smooth(bass_share, 0.4), audible, 12.0)
    loud_relative = _normalise(smooth(loudness, 0.4), audible, 6.0)
    flux_relative = _normalise(np.log(smooth(flux, 0.5) + 1e-4), audible, 0.7)
    # Onset activity on an absolute scale: 0.005 is barely anything (ambient), 0.1 is
    # a dense dance track. Bass share alone can't tell a drone from a drop
    flux_absolute = np.clip(np.log(smooth(flux, 1.0) / 0.005 + 1e-9) / np.log(0.1 / 0.005), 0, 1)
    return bass_relative, loud_relative, flux_relative, flux_absolute


def _energy(bass_relative, loud_relative, flux_relative, flux_absolute):
    relative = 0.45 * bass_relative + 0.3 * loud_relative + 0.25 * flux_relative
    # Quiet, sparse music can't reach the top however much it varies
    return relative * (0.55 + 0.45 * flux_absolute)


def _onset_strength(flux, fps):
    onset = np.maximum(flux - gaussian_filter1d(flux, fps, mode="nearest"), 0)
    return onset / (onset.std() + 1e-9)


def _periodicity(onset, lags):
    """How strongly the onsets repeat at each lag, and at 2 and 4 times it (bars)"""
    centred = onset - onset.mean()
    energy = np.dot(centred, centred) + 1e-9

    def correlation(lag):
        return np.dot(centred[:-lag], centred[lag:]) / energy if lag < len(centred) else 0.0

    return np.array([correlation(l) + 0.5 * correlation(2 * l) + 0.25 * correlation(4 * l) for l in lags])


def _track_beats(flux, kick_flux, fps):
    """Global tempo from autocorrelation, then beats placed by dynamic programming
    (Ellis 2007): each beat sits on strong onsets about one beat after the last"""
    onset = _onset_strength(flux, fps)
    lags = np.arange(int(60 * fps / TEMPO_RANGE[1]), int(60 * fps / TEMPO_RANGE[0]) + 1)
    bpm = 60 * fps / lags
    weights = np.exp(-0.5 * (np.log2(bpm / PREFERRED_TEMPO) / 0.7) ** 2)
    best = int(np.argmax(_periodicity(onset, lags) * weights))
    # Syncopated patterns (3-3-2 and the like) make tempos 4:3, 3:2 or 2:1 off the
    # beat look just as periodic. Among that family, trust the kick drum's
    # fundamental, which lands on the beat
    sub = _periodicity(_onset_strength(kick_flux, fps), lags)
    family = [i for i in range(len(lags))
              if any(abs(lags[i] / lags[best] - r) < 0.03 for r in (1, 3 / 4, 4 / 3, 2 / 3, 3 / 2, 1 / 2, 2))]
    period = float(lags[max(family, key=lambda i: sub[i])])
    tempo = 60 * fps / period

    tightness = 100.0
    n = len(onset)
    total = onset.copy()
    back = np.full(n, -1)
    low, high = int(round(period / 2)), int(round(2 * period))
    for t in range(low, n):
        previous = np.arange(max(0, t - high), t - low + 1)
        penalty = -tightness * np.log((t - previous) / period) ** 2
        candidates = total[previous] + penalty
        best = int(np.argmax(candidates))
        if candidates[best] > 0:
            total[t] = onset[t] + candidates[best]
            back[t] = previous[best]
    # Backtrack from the best-scoring beat in the last period
    tail = np.arange(max(0, n - int(period)), n)
    beat = int(tail[np.argmax(total[tail])])
    beats = [beat]
    while back[beat] >= 0:
        beat = int(back[beat])
        beats.append(beat)
    return np.array(beats[::-1]), tempo


def _novelty_boundaries(bins_db, loudness, flux, beats, half_width=16):
    """Beats where the music changes character (Foote 2000): each beat is described
    by its spectrum, loudness and hits, every beat is compared with every other, and
    a checkerboard kernel slid along the diagonal peaks where the past and future
    sound unlike each other"""
    count = len(beats) - 1
    if count < 4 * half_width:
        return []
    features = np.array([np.concatenate((bins_db[a:b].mean(axis=0), [loudness[a:b].mean(), np.log(flux[a:b].mean() + 1e-4)]))
                         for a, b in zip(beats[:-1], beats[1:])])
    features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-9)
    features = (features[:-1] + features[1:]) / 2  # smooth over two beats
    unit = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-9)
    similarity = unit @ unit.T
    offsets = np.arange(-half_width, half_width)
    taper = np.exp(-0.5 * ((offsets + 0.5) / (half_width / 2)) ** 2)
    kernel = np.outer(np.sign(offsets + 0.5), np.sign(offsets + 0.5)) * np.outer(taper, taper)
    novelty = np.zeros(len(similarity))
    for i in range(half_width, len(similarity) - half_width):
        novelty[i] = np.sum(similarity[i - half_width:i + half_width, i - half_width:i + half_width] * kernel)
    novelty = np.maximum(-novelty, 0)  # high where past and future differ
    threshold = novelty.mean() + 1.25 * novelty.std()
    peaks = []
    for i in np.argsort(-novelty):
        if novelty[i] < threshold:
            break
        if all(abs(i - j) >= half_width for j in peaks):
            peaks.append(int(i))
    top = novelty.max() + 1e-9
    return [(float(novelty[i] / top), int(beats[i + 1])) for i in peaks]


def _sections(intensity, flux_absolute, bins_db, loudness, flux, bass_share, beats, tempo, fps):
    frames = len(intensity)
    beat_frames = 60 * fps / tempo
    min_frames = MIN_SECTION_BEATS * beat_frames

    # Candidate boundaries: where the energy jumps (strongest first) and where the
    # music changes character. Jumps win when two are too close, since a drop
    # matters more than a change of timbre
    span = int(8 * beat_frames)
    smooth = gaussian_filter1d(intensity, fps, mode="nearest")
    candidates = []
    for b in beats[::2]:
        if span <= b < frames - span:
            change = smooth[b:b + span].mean() - smooth[b - span:b].mean()
            if abs(change) >= 0.25:
                candidates.append((2.0 + abs(change), int(b)))
    candidates += [(1.0 + strength, b) for strength, b in _novelty_boundaries(bins_db, loudness, flux, beats)]
    # Every clear energy jump is kept; changes of character only up to about one
    # section per 15 seconds overall, strongest first
    limit = max(1, int(frames / fps / 15))
    kept = []
    for priority, b in sorted(candidates, reverse=True):
        if priority < 2.0 and len(kept) >= limit:
            break
        if min_frames / 2 <= b <= frames - min_frames / 2 and all(abs(b - k) >= min_frames for k in kept):
            kept.append(b)
    edges = [0] + sorted(kept) + [frames]

    energy = [float(intensity[a:b].mean()) for a, b in zip(edges[:-1], edges[1:])]
    activity = [float(flux_absolute[a:b].mean()) for a, b in zip(edges[:-1], edges[1:])]
    tiers = [int(np.digitize(e, TIER_START)) for e in energy]
    # Energetic songs always get their peak moments; sparse music never peaks
    top = max(energy)
    if 2 not in tiers and top >= 0.45:
        tiers = [2 if e >= top - 0.08 and a >= 0.4 else t for e, a, t in zip(energy, activity, tiers)]
    tiers = [1 if t == 2 and a < 0.4 else t for t, a in zip(tiers, activity)]
    # Peaks are the high points: at most about half the song, the most energetic parts
    lengths = [b - a for a, b in zip(edges[:-1], edges[1:])]
    while sum(l for l, t in zip(lengths, tiers) if t == 2) > 0.55 * frames and tiers.count(2) > 1:
        weakest = min((e, i) for i, (e, t) in enumerate(zip(energy, tiers)) if t == 2)[1]
        tiers[weakest] = 1
    # Calm parts only where the song really has contrast
    if 0 not in tiers and top - min(energy) >= 0.2:
        tiers = [0 if e <= min(energy) + 0.05 else t for e, t in zip(energy, tiers)]
    runs = [[a, b, t] for a, b, t in zip(edges[:-1], edges[1:], tiers)]

    # Move rising boundaries onto the hit where the bass comes in, all onto beats
    rise = np.diff(gaussian_filter1d(bass_share, 0.05 * fps, mode="nearest"), prepend=bass_share[0])
    for k in range(1, len(runs)):
        boundary = runs[k][0]
        if runs[k][2] > runs[k - 1][2]:
            window = np.arange(max(0, boundary - 2 * fps), min(len(rise), boundary + 2 * fps))
            boundary = int(window[np.argmax(rise[window])])
        if len(beats):
            boundary = int(beats[np.argmin(np.abs(beats - boundary))])
        boundary = min(max(boundary, runs[k - 1][0] + 1), runs[k][1] - 1)
        runs[k - 1][1] = runs[k][0] = boundary
    return [Section(a, b, TIERS[t], float(flux_absolute[a:b].mean())) for a, b, t in runs]


def _pattern(bars):
    """Average pattern of complete bars (rows of 16 step strengths), or None if too few"""
    complete = np.array([bar for bar in bars if not np.isnan(bar).any()])
    if len(complete) < 4:
        return None
    pattern = complete.mean(axis=0)
    # How closely each bar follows the average pattern
    centred = complete - complete.mean(axis=1, keepdims=True)
    reference = pattern - pattern.mean()
    correlation = (centred @ reference) / (np.linalg.norm(centred, axis=1) * np.linalg.norm(reference) + 1e-9)
    pattern = pattern / (pattern.max() + 1e-9)
    threshold = pattern.mean() + 0.5 * pattern.std()
    accents = sorted(int(i) for i in np.argsort(-pattern)[:8] if pattern[i] >= threshold)
    return Pattern(list(pattern), accents, float(np.clip(np.mean(correlation), 0, 1)))


def _groove(onset, beats, sections, frames):
    """The rhythm each section repeats bar after bar, at sixteenth-note steps

    Bars are counted from the first drop's beat, since drops land on the one.
    Each groove or peak section averages the hit strength at each step over
    its own bars; the steps hit clearly harder than average are its accents.
    Sections too short to learn from use the whole song's pattern.
    """
    hits = np.zeros(frames, dtype=bool)
    steps = np.full(frames, -1, dtype=np.int8)
    empty = Groove(Pattern([0.0] * STEPS_PER_BAR, [], 0.0), [None] * len(sections), hits, steps)
    if len(beats) < 2 * 4 + 1:
        return empty
    section_of = np.zeros(frames, dtype=np.int32)
    starts = []
    for i, section in enumerate(sections):
        section_of[section.start:section.end] = i
        if section.tier == "peak" and i > 0 and TIERS.index(sections[i - 1].tier) < 2:
            starts.append(section.start)
    anchor = int(np.argmin(np.abs(beats - starts[0]))) if starts else 0

    # Frame and bar step of every sixteenth note between beats
    step_frames, step_numbers, bar_numbers = [], [], []
    for k in range(len(beats) - 1):
        a, b = beats[k], beats[k + 1]
        for j in range(STEPS_PER_BEAT):
            step_frames.append(a + (b - a) * j / STEPS_PER_BEAT)
            step_numbers.append(((k - anchor) % 4) * STEPS_PER_BEAT + j)
            bar_numbers.append((k - anchor) // 4)
    step_frames = np.array(step_frames)
    step_numbers = np.array(step_numbers)
    span = int(np.ceil(np.median(np.diff(beats)) / STEPS_PER_BEAT)) + 1
    for frame, step in zip(step_frames.astype(int), step_numbers):
        steps[frame:frame + span] = step

    # Strongest onset within an eighth of a beat of each step
    reach = max(1, int(np.median(np.diff(beats)) / 8))
    strength = np.array([onset[max(0, int(f) - reach):int(f) + reach + 1].max() for f in step_frames])
    step_section = section_of[np.clip(step_frames.astype(int), 0, frames - 1)]

    # Bars per section (a bar belongs to the section its first step is in)
    bars = {}
    for bar, step, value, section in zip(bar_numbers, step_numbers, strength, step_section):
        if sections[section].tier != "calm":
            bars.setdefault(section, {}).setdefault(bar, np.full(STEPS_PER_BAR, np.nan))[step] = value
    song = _pattern([bar for section_bars in bars.values() for bar in section_bars.values()]) or empty.song
    patterns = []
    for i, section in enumerate(sections):
        if section.tier == "calm":
            patterns.append(None)
            continue
        own = _pattern(list(bars.get(i, {}).values()))
        patterns.append(own if own is not None else song)

    for frame, step, section in zip(step_frames, step_numbers, step_section):
        pattern = patterns[section]
        if pattern is not None and pattern.reliable and step in pattern.accents:
            hits[min(frames - 1, int(round(frame)))] = True
    return Groove(song, patterns, hits, steps)


def cache_path(track):
    path = os.path.join(MUSIC_DIR, track)
    stat = os.stat(path)
    key = "{}|{}|{}|{}|{}|{}".format(track, stat.st_size, int(stat.st_mtime), ANALYSIS_VERSION,
                                     config.settings["configuration"]["MIC_RATE"], config.settings["configuration"]["FPS"])
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode()).hexdigest() + ".npz")


def _analyse_in_process(track, messages):
    """Runs in a child process: analyse a track, cache it and report progress"""
    try:
        def progress(fraction):
            messages.put(("progress", track, fraction))
        analysis = analyse_file(os.path.join(MUSIC_DIR, track), progress)
        os.makedirs(CACHE_DIR, exist_ok=True)
        analysis.save(cache_path(track))
        messages.put(("done", track, None))
    except Exception as error:
        messages.put(("failed", track, "{}: {}".format(type(error).__name__, error)))


class Library:
    """Analyses tracks in the background, one at a time, and keeps the results"""
    def __init__(self, on_change=None):
        self.on_change = on_change
        self.ready = {}
        self.status = {}  # track -> {"status": ..., "progress": ..., "error": ...}
        self.jobs = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self._work, daemon=True).start()

    def request(self, track, first=False):
        """Make sure a track is analysed; `first` jumps the queue (the track being played)"""
        with self.lock:
            if track in self.ready or self.status.get(track, {}).get("status") in ("queued", "analysing"):
                if first and self.status.get(track, {}).get("status") == "queued":
                    self.urgent = track
                return
            try:
                self.ready[track] = TrackAnalysis.load(cache_path(track))
                self.status[track] = {"status": "ready"}
                return
            except (OSError, KeyError, ValueError):
                pass
            self.status[track] = {"status": "queued", "progress": 0.0}
            if first:
                self.urgent = track
        self.jobs.put(track)
        self._changed()

    def request_all(self):
        for track in list_tracks():
            self.request(track)

    def get(self, track):
        return self.ready.get(track)

    def status_of(self, track):
        return self.status.get(track, {"status": "none"})

    def _changed(self):
        if self.on_change:
            self.on_change()

    def _next_job(self):
        urgent = getattr(self, "urgent", None)
        if urgent and self.status.get(urgent, {}).get("status") == "queued":
            self.urgent = None
            return urgent
        while True:
            track = self.jobs.get()
            if self.status.get(track, {}).get("status") == "queued":
                return track

    def _work(self):
        context = multiprocessing.get_context("spawn")
        while True:
            track = self._next_job()
            messages = context.Queue()
            process = context.Process(target=_analyse_in_process, args=(track, messages), daemon=True)
            self.status[track] = {"status": "analysing", "progress": 0.0}
            self._changed()
            process.start()
            last_reported = 0.0
            while True:
                try:
                    kind, _, value = messages.get(timeout=1)
                except queue.Empty:
                    if not process.is_alive():
                        self.status[track] = {"status": "failed", "error": "analysis stopped unexpectedly"}
                        self._changed()
                        break
                    continue
                if kind == "progress":
                    self.status[track]["progress"] = value
                    if value - last_reported >= 0.2:
                        last_reported = value
                        self._changed()
                elif kind == "done":
                    self.ready[track] = TrackAnalysis.load(cache_path(track))
                    self.status[track] = {"status": "ready"}
                    self._changed()
                    break
                else:
                    self.status[track] = {"status": "failed", "error": value}
                    print("dirty-leds: analysing {} failed, {}".format(track, value))
                    self._changed()
                    break
            process.join(timeout=5)
