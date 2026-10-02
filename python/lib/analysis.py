"""Pre-analysis of music files, so the show knows what is coming

Real-time analysis only knows the past, so it lags: intensity has to be
smoothed before it can be trusted, and a drop can only be reacted to after it
lands. For a file the whole song can be analysed up front instead:

    intensity   smoothed with the future as well as the past, so it changes
                exactly when the music does
    beats       a beat grid from dynamic programming over the whole song's
                onsets, which follows small tempo drifts
    sections    calm / groove / peak parts, boundaries snapped to beats, drops
                pinned to the hit where the bass comes in

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
from lib.features import (BASS, INTENSITY_BASS, PREFERRED_TEMPO, SILENCE_DBFS, TEMPO_RANGE, WINDOW,
                          _band)

ANALYSIS_VERSION = 1
CACHE_DIR = os.path.join(MUSIC_DIR, ".analysis")
TIERS = ("calm", "groove", "peak")
TIER_START = (0.35, 0.72)
# The kick drum's fundamental, which settles which of a family of related tempos is the beat
SUB = (30, 80)
# Sections shorter than this many beats are merged into a neighbour
MIN_SECTION_BEATS = 16


@dataclass
class Section:
    start: int  # frame
    end: int
    tier: str


class TrackAnalysis:
    """Per-frame intensity, beats and sections for one track"""
    def __init__(self, fps, intensity, beats, sections, tempo):
        self.fps = fps
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
        section = self.sections[self.section_index[frame]]
        next_drop = next((d for d in self.drops if d > frame), None)
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
        }

    def summary(self):
        return {
            "duration": self.frames / self.fps,
            "tempo": round(self.tempo, 1),
            "sections": [{"start": s.start / self.fps, "end": s.end / self.fps, "tier": s.tier} for s in self.sections],
            "drops": [d / self.fps for d in self.drops],
        }

    def save(self, path):
        np.savez_compressed(path, intensity=self.intensity, beats=self.beat_frames,
                            sections=np.array([[s.start, s.end, TIERS.index(s.tier)] for s in self.sections]),
                            meta=json.dumps({"fps": self.fps, "tempo": self.tempo}))

    @classmethod
    def load(cls, path):
        data = np.load(path)
        meta = json.loads(str(data["meta"]))
        sections = [Section(int(a), int(b), TIERS[int(t)]) for a, b, t in data["sections"]]
        return cls(meta["fps"], data["intensity"], data["beats"], sections, meta["tempo"])


def analyse_file(path, progress=lambda fraction: None):
    rate = config.settings["configuration"]["MIC_RATE"]
    fps = config.settings["configuration"]["FPS"]
    hop = rate // fps
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 2.0**15
    frames = len(audio) // hop
    if frames < fps * 5:
        raise ValueError("track is shorter than 5 seconds")
    progress(0.1)

    # Same windows the live analysis sees: the last WINDOW samples up to the end of each frame
    padded = np.concatenate((np.zeros(WINDOW - hop, dtype=np.float32), audio[:frames * hop]))
    freqs = np.fft.rfftfreq(WINDOW, 1.0 / rate)
    intensity_band, audible, kick_band = _band(freqs, *INTENSITY_BASS), _band(freqs, 100, 14000), _band(freqs, *SUB)
    window = np.hanning(WINDOW)
    total_db, bass_db, flux, kick_flux = np.zeros(frames), np.zeros(frames), np.zeros(frames), np.zeros(frames)
    previous = previous_kick = None
    for start in range(0, frames, 2000):
        idx = np.arange(start, min(frames, start + 2000))
        chunk = np.lib.stride_tricks.sliding_window_view(padded, WINDOW)[idx * hop]
        spectrum = np.abs(np.fft.rfft(chunk * window, axis=1)) / (WINDOW / 4)
        power = spectrum ** 2
        total_db[idx] = 10 * np.log10(power.sum(axis=1) + 1e-12)
        bass_db[idx] = 10 * np.log10(power[:, intensity_band].sum(axis=1) + 1e-12)
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
    intensity = _intensity(bass_db - total_db, loudness, silent, fps)
    sections = _sections(intensity, bass_db - total_db, beats, tempo, fps)
    progress(0.95)
    return TrackAnalysis(fps, intensity.astype(np.float32), beats, sections, tempo)


def _normalise(values, mask, min_range):
    """0-1 against the song's own 10th to 90th percentile"""
    if not mask.any():
        return np.zeros_like(values)
    low, high = np.percentile(values[mask], [10, 90])
    low = min(low, high - min_range)
    return np.clip((values - low) / (high - low), 0, 1)


def _intensity(bass_share, loudness, silent, fps):
    """Same recipe as the live intensity, but judged against the whole song and
    smoothed with the future as well as the past, so it has no lag"""
    audible = ~silent
    bass = _normalise(gaussian_filter1d(bass_share, 0.4 * fps, mode="nearest"), audible, 12.0)
    loud = _normalise(gaussian_filter1d(loudness, 0.4 * fps, mode="nearest"), audible, 6.0)
    intensity = np.where(silent, 0.0, 0.7 * bass + 0.3 * loud)
    return gaussian_filter1d(intensity, 0.15 * fps, mode="nearest")


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


def _sections(intensity, bass_share, beats, tempo, fps):
    tier = np.digitize(intensity, TIER_START)
    # Runs of the same tier
    edges = np.flatnonzero(np.diff(tier)) + 1
    starts = np.concatenate(([0], edges))
    ends = np.concatenate((edges, [len(tier)]))
    runs = [[int(a), int(b), int(tier[a])] for a, b in zip(starts, ends)]

    # Merge runs that are too short to be a section into the neighbour closest in intensity
    min_frames = MIN_SECTION_BEATS * 60 * fps / tempo
    while len(runs) > 1:
        lengths = [b - a for a, b, _ in runs]
        i = int(np.argmin(lengths))
        if lengths[i] >= min_frames:
            break
        mean = intensity[runs[i][0]:runs[i][1]].mean()
        neighbours = [j for j in (i - 1, i + 1) if 0 <= j < len(runs)]
        j = min(neighbours, key=lambda k: abs(intensity[runs[k][0]:runs[k][1]].mean() - mean))
        a, b = min(runs[i][0], runs[j][0]), max(runs[i][1], runs[j][1])
        keep = runs[j][2] if runs[j][1] - runs[j][0] >= runs[i][1] - runs[i][0] else runs[i][2]
        runs[min(i, j)] = [a, b, keep]
        del runs[max(i, j)]
        # Neighbours with the same tier become one section
        merged = [runs[0]]
        for run in runs[1:]:
            if run[2] == merged[-1][2]:
                merged[-1][1] = run[1]
            else:
                merged.append(run)
        runs = merged

    # Move each boundary onto a beat; when the energy rises, onto the hit where the bass comes in
    rise = np.diff(gaussian_filter1d(bass_share, 0.05 * fps, mode="nearest"), prepend=bass_share[0])
    for k in range(1, len(runs)):
        boundary = runs[k][0]
        if runs[k][2] > runs[k - 1][2]:
            window = np.arange(max(0, boundary - fps), min(len(rise), boundary + fps))
            boundary = int(window[np.argmax(rise[window])])
        if len(beats):
            boundary = int(beats[np.argmin(np.abs(beats - boundary))])
        boundary = min(max(boundary, runs[k - 1][0] + 1), runs[k][1] - 1)
        runs[k - 1][1] = runs[k][0] = boundary
    return [Section(a, b, TIERS[t]) for a, b, t in runs]


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
