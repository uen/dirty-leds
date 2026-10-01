"""Audio analysis, and the filters effects keep per strip

The FFT and mel filterbank only depend on the audio and a strip's frequency
range, so strips with the same range share one AudioAnalyser and the work is
done once per frame instead of once per strip.
"""
import numpy as np
import config
import lib.melbank as melbank
from scipy.ndimage import gaussian_filter1d


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
            alpha = value - self.value
            alpha[alpha > 0.0] = self.alpha_rise
            alpha[alpha <= 0.0] = self.alpha_decay
        else:
            alpha = self.alpha_rise if value > self.value else self.alpha_decay
        self.value = alpha * value + (1.0 - alpha) * self.value
        return self.value


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
        self.mel_gain.update(np.max(gaussian_filter1d(mel, sigma=1.0)))
        mel /= self.mel_gain.value
        mel = self.mel_smoothing.update(mel)
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
