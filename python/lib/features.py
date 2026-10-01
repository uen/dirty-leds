"""Musical features of the audio, normalised so effects behave the same on every song

MusicFeatures.update() takes one frame of samples and returns a Features with:

    bass, mid, treble   0-1, how strong each band is right now: its presence in
                        the song so far times how much it is pulsing (BandLevels)
    bins                24 log-spaced bands, 0-1 each, for spectrum-style effects
    intensity           0-1, how big this part of the song is: low in an intro
                        or breakdown, high in a drop, relative to the last 30 s
    brightness          0-1, dull to bright sound (spectral centroid)
    kick, snare, hat    0-1, jump to 1 on a hit in that range and fade out
    onset               0-1, the same for any hit
    beat                True on the frame a beat lands
    beat_phase          0-1, position within the current beat
    tempo               beats per minute
    section_change      True on the frame the song moves to a new part
    silent              True when there is no meaningful sound

Everything adapts to loudness, so the same song at any volume, or a quiet song
next to a loud one, uses the full range. Time constants are in seconds.
"""
import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

import config

WINDOW = 2048
# Below this the input is treated as silence, so background noise isn't amplified
SILENCE_DBFS = -60.0
BASS = (30, 200)
MID = (200, 2500)
TREBLE = (2500, 14000)
# Onset ranges: kick drums, snares and vocals, hi-hats and cymbals
KICK = (30, 150)
SNARE = (150, 4000)
HAT = (6000, 16000)
# Range used for how much of the energy is bass, which drives intensity
INTENSITY_BASS = (30, 150)
N_BINS = 24
BINS_RANGE = (40, 14000)
TEMPO_RANGE = (70, 180)
PREFERRED_TEMPO = 120


def _rate(seconds, dt):
    """Per-frame smoothing coefficient for a time constant in seconds"""
    return 1.0 if seconds <= 0 else 1.0 - math.exp(-dt / seconds)


class Envelope:
    """Follows a value (or array) with separate attack and release times"""
    def __init__(self, attack, release, dt, value=0.0):
        self.attack = _rate(attack, dt)
        self.release = _rate(release, dt)
        self.value = value

    def update(self, target):
        rate = np.where(target > self.value, self.attack, self.release)
        self.value = self.value + rate * (target - self.value)
        return self.value


class AdaptiveRange:
    """Maps levels in dB to 0-1 against their own recent peak and floor

    The peak jumps up to new highs and sinks by `fall` dB a second; the floor
    drops to new lows and rises by `rise` dB a second. They are kept at least
    `min_range` dB apart, so a steady sound isn't blown up to full scale.
    """
    def __init__(self, dt, fall=1.5, rise=1.0, min_range=18.0):
        self.fall = fall * dt
        self.rise = rise * dt
        self.min_range = min_range
        self.peak = None
        self.floor = None

    def update(self, level):
        if self.peak is None:
            self.peak = np.array(level, dtype=float)
            self.floor = self.peak - self.min_range
        self.peak = np.maximum(level, self.peak - self.fall)
        self.floor = np.minimum(level, self.floor + self.rise)
        span = np.maximum(self.peak - self.floor, self.min_range)
        return np.clip((level - (self.peak - span)) / span, 0.0, 1.0)


class BandLevels:
    """Turns band levels in dB into 0-1 values that pulse with the music

    presence: how strong the band is against its own range over the song so far,
              so bass is low through a breakdown and high in a drop
    pulse:    how far it is above or below its typical level over the last
              second, so hits jump up and gaps between them drop down
    The value is presence x pulse, smoothed with a fast attack and short release.
    """
    def __init__(self, dt, size, window=1.0):
        self.presence = AdaptiveRange(dt)
        self.recent = deque(maxlen=max(3, int(window / dt)))
        self.envelope = Envelope(0.01, 0.12, dt, value=np.zeros(size))

    def update(self, levels_db):
        self.recent.append(levels_db)
        history = np.array(self.recent)
        median = np.median(history, axis=0)
        spread = np.maximum(np.median(np.abs(history - median), axis=0), 1.5)
        pulse = np.clip(0.5 + (levels_db - median) / (4 * spread), 0.0, 1.0)
        return self.envelope.update(self.presence.update(levels_db) * pulse)

    def silence(self):
        return self.envelope.update(np.zeros_like(self.envelope.value))


class OnsetDetector:
    """Spectral flux with an adaptive threshold: fires when a range suddenly gets louder"""
    def __init__(self, dt, history=0.5, sensitivity=3.5, min_gap=0.1, release=0.15):
        self.flux = deque(maxlen=max(3, int(history / dt)))
        self.sensitivity = sensitivity
        self.min_gap = min_gap
        self.dt = dt
        self.since_last = min_gap
        self.was_above = False
        self.envelope = Envelope(0, release, dt)
        self.hit = False

    def update(self, flux):
        self.since_last += self.dt
        history = np.array(self.flux) if self.flux else np.array([flux])
        median = np.median(history)
        threshold = median + self.sensitivity * np.mean(np.abs(history - median)) + 1e-3
        above = flux > threshold
        self.hit = above and not self.was_above and self.since_last >= self.min_gap
        if self.hit:
            self.since_last = 0.0
        self.was_above = above
        self.flux.append(flux)
        self.envelope.update(1.0 if self.hit else 0.0)
        return self.hit


class BeatTracker:
    """Estimates tempo from the onset signal and keeps a beat clock locked to it

    Tempo comes from autocorrelating the last few seconds of onset strength. A
    phase oscillator ticks at that tempo and is nudged toward kicks, so beats
    keep landing through quiet passages instead of only on detected hits.
    """
    def __init__(self, fps, history=8.0, update_every=0.5):
        self.fps = fps
        self.strength = deque(maxlen=int(history * fps))
        self.update_every = int(update_every * fps)
        self.frames = 0
        self.tempo = float(PREFERRED_TEMPO)
        self.confidence = 0.0
        self.challenger = 0
        self.phase = 0.0
        min_lag = int(round(60 * fps / TEMPO_RANGE[1]))
        max_lag = int(round(60 * fps / TEMPO_RANGE[0]))
        self.lags = np.arange(min_lag, max_lag + 1)
        # Prefer tempos near PREFERRED_TEMPO, which settles half/double tempo ambiguity
        bpm = 60 * fps / self.lags
        self.weights = np.exp(-0.5 * (np.log2(bpm / PREFERRED_TEMPO) / 0.7) ** 2)

    def update(self, onset_strength, onset_hit):
        self.strength.append(onset_strength)
        self.frames += 1
        if self.frames % self.update_every == 0 and len(self.strength) > self.lags[-1] * 2:
            self._estimate_tempo()

        self.phase += self.tempo / 60 / self.fps
        if onset_hit and self.confidence > 0.1:
            # Pull the clock toward the hit, by how far it is from the nearest beat
            error = self.phase if self.phase < 0.5 else self.phase - 1.0
            if abs(error) < 0.3:
                self.phase -= 0.2 * error
        beat = self.phase >= 1.0
        if beat:
            self.phase -= math.floor(self.phase)
        if self.confidence <= 0.1:
            # No steady tempo: fall back to beating on hits
            beat = onset_hit
            if onset_hit:
                self.phase = 0.0
        return beat

    def _estimate_tempo(self):
        signal = np.array(self.strength)
        signal = signal - signal.mean()
        energy = float(np.dot(signal, signal))
        if energy <= 1e-12:
            self.confidence = 0.0
            return
        n = len(signal)

        def autocorrelation(lag):
            return np.dot(signal[:n - lag], signal[lag:]) / energy if lag < n else 0.0

        correlation = np.array([autocorrelation(lag) for lag in self.lags])
        # The real beat also repeats every 2 and 4 beats (bars); syncopated patterns
        # that only look periodic over one gap, like 3-3-2 rhythms, don't
        score = correlation + 0.5 * np.array([autocorrelation(2 * lag) for lag in self.lags]) \
            + 0.25 * np.array([autocorrelation(4 * lag) for lag in self.lags])
        best = int(np.argmax(score * self.weights))
        lag = float(self.lags[best])
        if 0 < best < len(self.lags) - 1:
            # Parabolic interpolation between neighbouring lags for a finer tempo
            a, b, c = correlation[best - 1:best + 2]
            denominator = a - 2 * b + c
            if denominator < 0:
                lag += 0.5 * (a - c) / denominator
        self.confidence = float(max(0.0, correlation[best]))
        tempo = 60 * self.fps / lag
        if abs(tempo - self.tempo) <= 0.08 * self.tempo:
            self.tempo = 0.7 * self.tempo + 0.3 * tempo
            self.challenger = 0
            return
        # A different tempo has to win clearly, several times in a row, before the
        # clock switches; otherwise syncopated parts make it flip back and forth
        current = int(np.argmin(np.abs(60 * self.fps / self.lags - self.tempo)))
        # Tempos in a simple ratio to the current one (3:4, 2:3, 1:2...) are usually
        # the same music heard through a different rhythm, so need far more evidence
        ratio = max(tempo, self.tempo) / min(tempo, self.tempo)
        related = any(abs(ratio - r) < 0.05 for r in (4 / 3, 3 / 2, 2.0))
        margin, needed = (1.4, 8) if related else (1.15, 3)
        clearly_better = score[best] * self.weights[best] > margin * score[current] * self.weights[current]
        self.challenger = self.challenger + 1 if clearly_better else 0
        if self.challenger >= needed or self.frames < 4 * self.update_every:
            self.tempo = tempo
            self.challenger = 0


class SongHistory:
    """Recent values of a level, to judge a new value against the song so far

    Until there is enough history, judges against a fixed prior range instead.
    """
    def __init__(self, fps, seconds=60, warmup=10):
        self.values = deque(maxlen=seconds * fps)
        self.warmup = warmup * fps

    def normalise(self, value, min_range, prior):
        self.values.append(value)
        prior_value = np.clip((value - prior[0]) / (prior[1] - prior[0]), 0, 1)
        if len(self.values) < 2:
            return float(prior_value)
        history = np.array(self.values)
        top = np.percentile(history, 90)
        bottom = min(np.percentile(history, 10), top - min_range)
        learned = np.clip((value - bottom) / (top - bottom), 0, 1)
        trust = min(1.0, len(self.values) / self.warmup)
        return float(trust * learned + (1 - trust) * prior_value)


@dataclass
class Features:
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    bins: np.ndarray = field(default_factory=lambda: np.zeros(N_BINS))
    intensity: float = 0.0
    brightness: float = 0.5
    kick: float = 0.0
    snare: float = 0.0
    hat: float = 0.0
    onset: float = 0.0
    kick_hit: bool = False
    snare_hit: bool = False
    hat_hit: bool = False
    beat: bool = False
    beat_phase: float = 0.0
    tempo: float = float(PREFERRED_TEMPO)
    section_change: bool = False
    silent: bool = True


def _band(freqs, low, high):
    return (freqs >= low) & (freqs < high)


def _log_filterbank(freqs, n_bins, low, high):
    """Triangular filters with centres evenly spaced in log frequency"""
    edges = np.geomspace(low, high, n_bins + 2)
    bank = np.zeros((n_bins, len(freqs)))
    for i in range(n_bins):
        left, centre, right = edges[i:i + 3]
        rising = (freqs - left) / (centre - left)
        falling = (right - freqs) / (right - centre)
        bank[i] = np.clip(np.minimum(rising, falling), 0, None)
    return bank / np.maximum(bank.sum(axis=1, keepdims=True), 1e-12)


class MusicFeatures:
    def __init__(self):
        self.rate = config.settings["configuration"]["MIC_RATE"]
        self.fps = config.settings["configuration"]["FPS"]
        dt = 1.0 / self.fps
        self.samples = np.zeros(WINDOW)
        self.window = np.hanning(WINDOW)
        freqs = np.fft.rfftfreq(WINDOW, 1.0 / self.rate)
        self.bands = [_band(freqs, *BASS), _band(freqs, *MID), _band(freqs, *TREBLE)]
        self.onset_bands = [_band(freqs, *KICK), _band(freqs, *SNARE), _band(freqs, *HAT)]
        self.filterbank = _log_filterbank(freqs, N_BINS, *BINS_RANGE)
        audible = _band(freqs, 100, 14000)
        self.centroid_freqs = freqs[audible]
        self.audible = audible

        self.band_levels = BandLevels(dt, 3)
        self.bin_levels = BandLevels(dt, N_BINS)
        self.intensity_band = _band(freqs, *INTENSITY_BASS)
        self.loudness = Envelope(0.3, 1.5, dt, value=SILENCE_DBFS)
        self.bass_share = Envelope(0.3, 1.5, dt, value=-20.0)
        self.loudness_history = SongHistory(self.fps)
        self.bass_share_history = SongHistory(self.fps)
        self.intensity = Envelope(0.5, 0.5, dt)
        self.brightness = Envelope(0.3, 0.3, dt, value=0.5)
        self.previous_spectrum = None
        self.kick = OnsetDetector(dt)
        self.snare = OnsetDetector(dt)
        self.hat = OnsetDetector(dt, min_gap=0.06, release=0.08)
        self.onset = OnsetDetector(dt)
        self.beats = BeatTracker(self.fps)
        # Section changes: loudness over the last few seconds against the stretch before it
        self.recent = deque(maxlen=3 * self.fps)
        self.earlier = deque(maxlen=8 * self.fps)
        self.since_section = 0.0
        self.current = Features()

    def update(self, audio_samples):
        dt = 1.0 / self.fps
        y = np.asarray(audio_samples, dtype=float) / 2.0**15
        self.samples = np.roll(self.samples, -len(y))
        self.samples[-len(y):] = y

        rms = math.sqrt(float(np.mean(y * y)))
        level = 20 * math.log10(rms + 1e-9)
        silent = level < SILENCE_DBFS

        spectrum = np.abs(np.fft.rfft(self.samples * self.window)) / (WINDOW / 4)
        power = spectrum ** 2
        band_db = np.array([10 * math.log10(float(power[b].sum()) + 1e-12) for b in self.bands])
        bins_db = 10 * np.log10(self.filterbank @ power + 1e-12)
        if silent:
            # Keep the learned ranges for when the music comes back
            bands = self.band_levels.silence()
            bins = self.bin_levels.silence()
        else:
            bands = self.band_levels.update(band_db)
            bins = self.bin_levels.update(bins_db)

        # Spectral flux on compressed magnitudes, per onset range
        compressed = np.log1p(100 * spectrum)
        if self.previous_spectrum is None:
            self.previous_spectrum = compressed
        rise = np.maximum(compressed - self.previous_spectrum, 0)
        self.previous_spectrum = compressed
        fluxes = [float(rise[b].mean()) for b in self.onset_bands]
        total_flux = float(rise[self.audible].mean())
        kick_hit = self.kick.update(0.0 if silent else fluxes[0])
        snare_hit = self.snare.update(0.0 if silent else fluxes[1])
        hat_hit = self.hat.update(0.0 if silent else fluxes[2])
        onset_hit = self.onset.update(0.0 if silent else total_flux)
        beat = self.beats.update(0.0 if silent else total_flux, kick_hit or onset_hit)

        # How big this part of the song is. Mostly how much of the energy is bass,
        # which swings 15-30 dB between breakdowns and drops while loudness barely
        # moves on modern masters; partly loudness against the song so far
        total_db = 10 * math.log10(float(power.sum()) + 1e-12)
        bass_db = 10 * math.log10(float(power[self.intensity_band].sum()) + 1e-12)
        loudness = float(self.loudness.update(SILENCE_DBFS if silent else level))
        bass_share = float(self.bass_share.update(-40.0 if silent else bass_db - total_db))
        if silent:
            target = 0.0
        else:
            bass_part = self.bass_share_history.normalise(bass_share, min_range=12.0, prior=(-18.0, 0.0))
            loud_part = self.loudness_history.normalise(loudness, min_range=6.0, prior=(-30.0, -10.0))
            target = 0.7 * bass_part + 0.3 * loud_part
        intensity = float(self.intensity.update(target))

        weights = power[self.audible]
        if not silent and weights.sum() > 0:
            centroid = float(np.dot(self.centroid_freqs, weights) / weights.sum())
            # 200 Hz (dull) to 5 kHz (bright), on a log scale
            self.brightness.update(float(np.clip(np.log2(centroid / 200) / np.log2(5000 / 200), 0, 1)))

        self.since_section += dt
        self.recent.append(loudness)
        section_change = False
        if len(self.earlier) == self.earlier.maxlen and not silent:
            if abs(np.mean(self.recent) - np.mean(self.earlier)) > 4.0 and self.since_section > 8.0:
                section_change = True
                self.since_section = 0.0
        if len(self.recent) == self.recent.maxlen:
            self.earlier.append(self.recent[0])

        self.current = Features(
            bass=float(bands[0]), mid=float(bands[1]), treble=float(bands[2]), bins=np.array(bins),
            intensity=intensity, brightness=float(self.brightness.value),
            kick=float(self.kick.envelope.value), snare=float(self.snare.envelope.value),
            hat=float(self.hat.envelope.value), onset=float(self.onset.envelope.value),
            kick_hit=kick_hit, snare_hit=snare_hit, hat_hit=hat_hit,
            beat=bool(beat), beat_phase=float(self.beats.phase), tempo=float(self.beats.tempo),
            section_change=section_change, silent=silent,
        )
        return self.current
