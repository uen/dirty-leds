from scipy.ndimage.filters import gaussian_filter1d
import lib.dsp as dsp
import numpy as np
import lib.config as config
import lib.melbank as melbank

class DSP():
    def __init__(self, board):
        # Name of board for which this dsp instance is processing audio
        print('biach')
        self.board = board
        print(type(board))

        # Initialise filters etc. I've no idea what most of these are for but i imagine i won't be getting rid of them soon 
        self.fft_plot_filter = dsp.ExpFilter(np.tile(1e-1, self.board.config["N_FFT_BINS"]), alpha_decay=0.5, alpha_rise=0.99)
        self.mel_gain =        dsp.ExpFilter(np.tile(1e-1, self.board.config["N_FFT_BINS"]), alpha_decay=0.01, alpha_rise=0.99)
        self.mel_smoothing =   dsp.ExpFilter(np.tile(1e-1, self.board.config["N_FFT_BINS"]), alpha_decay=0.5, alpha_rise=0.99)
        self.gain =            dsp.ExpFilter(np.tile(0.01, self.board.config["N_FFT_BINS"]), alpha_decay=0.001, alpha_rise=0.99)
        self.r_filt =          dsp.ExpFilter(np.tile(0.01, self.board.config["N_PIXELS"] // 2), alpha_decay=0.2, alpha_rise=0.99)
        self.g_filt =          dsp.ExpFilter(np.tile(0.01, self.board.config["N_PIXELS"] // 2), alpha_decay=0.05, alpha_rise=0.3)
        self.b_filt =          dsp.ExpFilter(np.tile(0.01, self.board.config["N_PIXELS"] // 2), alpha_decay=0.1, alpha_rise=0.5)
        self.common_mode =     dsp.ExpFilter(np.tile(0.01, self.board.config["N_PIXELS"] // 2), alpha_decay=0.99, alpha_rise=0.01)
        self.p_filt =          dsp.ExpFilter(np.tile(1, (3, self.board.config["N_PIXELS"] // 2)), alpha_decay=0.1, alpha_rise=0.99)
        self.volume =          dsp.ExpFilter(config.settings["configuration"]["MIN_VOLUME_THRESHOLD"], alpha_decay=0.02, alpha_rise=0.02)
        self.p =               np.tile(1.0, (3, self.board.config["N_PIXELS"] // 2))
        
        # Number of audio samples to read every time frame
        self.samples_per_frame = int(config.settings["configuration"]["MIC_RATE"] / config.settings["configuration"]["FPS"])
        # Array containing the rolling audio sample window
        self.y_roll = np.random.rand(config.settings["configuration"]["N_ROLLING_HISTORY"], self.samples_per_frame) / 1e16
        self.fft_window =      np.hamming(int(config.settings["configuration"]["MIC_RATE"] / config.settings["configuration"]["FPS"])\
                                         * config.settings["configuration"]["N_ROLLING_HISTORY"])

        self.samples = None
        self.mel_y = None
        self.mel_x = None
        self.create_mel_bank()

    def update(self, audio_samples):
        """ Return processed audio data

        Returns mel curve, x/y data

        This is called every time there is a microphone update

        Returns
        -------
        audio_data : dict
            Dict containinng "mel", "vol", "x", and "y"
        """

        audio_data = {}
        # Normalize samples between 0 and 1
        y = audio_samples / 2.0**15
        # Construct a rolling window of audio samples
        self.y_roll[:-1] = self.y_roll[1:]
        self.y_roll[-1, :] = np.copy(y)
        y_data = np.concatenate(self.y_roll, axis=0).astype(np.float32)
        vol = np.max(np.abs(y_data))
        # Transform audio input into the frequency domain
        N = len(y_data)
        N_zeros = 2**int(np.ceil(np.log2(N))) - N
        # Pad with zeros until the next power of two
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
        x = np.linspace(self.board.config["MIN_FREQUENCY"], self.board.config["MAX_FREQUENCY"], len(mel))
        y = self.fft_plot_filter.update(mel)

        audio_data["mel"] = mel
        audio_data["vol"] = vol
        audio_data["x"]   = x
        audio_data["y"]   = y
        return audio_data

    def rfft(self, data, window=None):
        window = 1.0 if window is None else window(len(data))
        ys = np.abs(np.fft.rfft(data * window))
        xs = np.fft.rfftfreq(len(data), 1.0 / config.settings["configuration"]["MIC_RATE"])
        return xs, ys


    def fft(self, data, window=None):
        window = 1.0 if window is None else window(len(data))
        ys = np.fft.fft(data * window)
        xs = np.fft.fftfreq(len(data), 1.0 / config.settings["configuration"]["MIC_RATE"])
        return xs, ys


    def create_mel_bank(self):
        samples = int(config.settings["configuration"]["MIC_RATE"] * config.settings["configuration"]["N_ROLLING_HISTORY"]\
                                                   / (2.0 * config.settings["configuration"]["FPS"]))
        self.mel_y, (_, self.mel_x) = melbank.compute_melmat(num_mel_bands=self.board.config["N_FFT_BINS"],
                                                             freq_min=self.board.config["MIN_FREQUENCY"],
                                                             freq_max=self.board.config["MAX_FREQUENCY"],
                                                             num_fft_bands=samples,
                                                             sample_rate=config.settings["configuration"]["MIC_RATE"])

