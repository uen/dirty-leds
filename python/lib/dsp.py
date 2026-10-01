"""Audio analysis, and the filters effects keep per strip

The FFT and mel filterbank only depend on the audio and a strip's frequency
range, so strips with the same range share one AudioAnalyser and the work is
done once per frame instead of once per strip.
"""
import time
import numpy as np
import config
import lib.melbank as melbank
import util


class ExpFilter:
    """Simple exponential smoothing filter"""
    def __init__(self, val=0.0, alpha_decay=0.5, alpha_rise=0.5):
        """Small rise / decay factors = more smoothing"""
        assert 0.0 < alpha_decay < 1.0, 'Invalid decay smoothing factor'
        assert 0.0 < alpha_rise < 1.0, 'Invalid rise smoothing factor'
        self.alpha_decay = alpha_decay
        self.alpha_rise = alpha_rise
        self.value = val

    def update(self, value):
        if isinstance(self.value, (list, np.ndarray, tuple)):
            alpha = np.where(value > self.value, self.alpha_rise, self.alpha_decay)
        else:
            alpha = self.alpha_rise if value > self.value else self.alpha_decay
        self.value = alpha * value + (1.0 - alpha) * self.value
        return self.value


class BeatDetector:
    """Flags beats and low / mid / high hits

    A range hits when one of its mel bins jumps well above that bin's average
    over the last HISTORY frames and is loud enough. Each range then waits
    COOLDOWN seconds before it can hit again.
    """
    HISTORY = 40
    COOLDOWN = 0.2
    # Fractions of the mel bins each range covers
    RANGES = {"beat": (0, 0.11), "low": (0.13, 0.4), "mid": (0.4, 0.7), "high": (0.8, 1.0)}
    MIN_AMPLITUDE = {"beat": 0.7, "low": 0.5, "mid": 0.3, "high": 0.3}
    MIN_PERCENT_DIFF = {"beat": 70, "low": 100, "mid": 50, "high": 30}

    def __init__(self, n_bins):
        self.history = np.zeros((self.HISTORY, n_bins))
        self.frames = 0
        self.ranges = {name: (int(n_bins * start), int(n_bins * end)) for name, (start, end) in self.RANGES.items()}
        self.last_hit = dict.fromkeys(self.RANGES, 0.0)
        self.detected = dict.fromkeys(self.RANGES, False)

    def update(self, mel):
        self.history[self.frames % self.HISTORY] = mel
        self.frames += 1
        if self.frames < self.HISTORY:
            return
        average = self.history.mean(axis=0)
        # A bin that has been silent for the whole history averages to exactly 0
        percent_diff = ((mel - average) * 100) // np.maximum(average, 1e-6)
        now = time.time()
        for name, (start, end) in self.ranges.items():
            loud_jump = (percent_diff[start:end] >= self.MIN_PERCENT_DIFF[name]) & \
                        (mel[start:end] >= self.MIN_AMPLITUDE[name])
            hit = bool(loud_jump.any()) and now - self.last_hit[name] > self.COOLDOWN
            if hit:
                self.last_hit[name] = now
            self.detected[name] = hit


class AudioAnalyser:
    """Turns frames of audio samples into a smoothed, gain-normalised mel spectrum"""
    def __init__(self, n_bins, min_frequency, max_frequency):
        rate = config.settings["configuration"]["MIC_RATE"]
        fps = config.settings["configuration"]["FPS"]
        history = config.settings["configuration"]["N_ROLLING_HISTORY"]

        self.samples_per_frame = int(rate / fps)
        # Rolling window of the last `history` frames of audio
        self.y_roll = np.zeros((history, self.samples_per_frame))
        self.fft_window = np.hamming(self.samples_per_frame * history)
        self.mel_gain = ExpFilter(np.tile(1e-1, n_bins), alpha_decay=0.01, alpha_rise=0.99)
        self.mel_smoothing = ExpFilter(np.tile(1e-1, n_bins), alpha_decay=0.5, alpha_rise=0.99)
        self.beats = BeatDetector(n_bins)
        self.mel_y, _ = melbank.compute_melmat(num_mel_bands=n_bins,
                                               freq_min=min_frequency,
                                               freq_max=max_frequency,
                                               num_fft_bands=int(rate * history / (2.0 * fps)),
                                               sample_rate=rate)

    def update(self, audio_samples):
        """Analyse one frame. Returns {"mel": spectrum, "vol": peak level 0-1}"""
        # Normalize samples between 0 and 1
        y = audio_samples / 2.0**15
        # Construct a rolling window of audio samples
        self.y_roll[:-1] = self.y_roll[1:]
        self.y_roll[-1, :] = y
        y_data = np.concatenate(self.y_roll, axis=0).astype(np.float32)
        vol = np.max(np.abs(y_data))
        # Transform audio input into the frequency domain, padded to the next power of two
        N = len(y_data)
        N_zeros = 2**int(np.ceil(np.log2(N))) - N
        y_data *= self.fft_window
        y_padded = np.pad(y_data, (0, N_zeros), mode='constant')
        YS = np.abs(np.fft.rfft(y_padded)[:N // 2])
        # Construct a Mel filterbank from the FFT data
        mel = np.atleast_2d(YS).T * self.mel_y.T
        # Scale data to values more suitable for visualization
        mel = np.sum(mel, axis=0)
        mel = mel**2.0
        # Gain normalization
        self.mel_gain.update(np.max(util.blur(mel, 1.0)))
        mel /= self.mel_gain.value
        mel = self.mel_smoothing.update(mel)
        self.beats.update(mel)
        return {"mel": mel, "vol": vol}


_analysers = {}


def analyser_for(n_bins, min_frequency, max_frequency):
    """The shared analyser for a frequency range, created on first use"""
    key = (n_bins, min_frequency, max_frequency)
    if key not in _analysers:
        _analysers[key] = AudioAnalyser(*key)
    return _analysers[key]


class DSP():
    """Per-strip filters that effects carry from frame to frame, plus the strip's analyser"""
    def __init__(self, board):
        self.board = board
        n_bins = board.config["N_FFT_BINS"]
        half_strip = board.config["N_PIXELS"] // 2
        self.gain =        ExpFilter(np.tile(0.01, n_bins), alpha_decay=0.001, alpha_rise=0.99)
        self.r_filt =      ExpFilter(np.tile(0.01, half_strip), alpha_decay=0.2, alpha_rise=0.99)
        self.b_filt =      ExpFilter(np.tile(0.01, half_strip), alpha_decay=0.1, alpha_rise=0.5)
        self.common_mode = ExpFilter(np.tile(0.01, half_strip), alpha_decay=0.99, alpha_rise=0.01)
        self.update_frequency_range()

    def update_frequency_range(self):
        """Pick up a changed MIN_FREQUENCY / MAX_FREQUENCY"""
        self.analyser = analyser_for(self.board.config["N_FFT_BINS"],
                                     self.board.config["MIN_FREQUENCY"],
                                     self.board.config["MAX_FREQUENCY"])
