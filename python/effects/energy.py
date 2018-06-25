from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util

from effects.effect import Effect


class Energy(Effect):
    def __init__(self, board):
    	self.effectName = "Energy"

    def visualize(self, board, y):

        y = np.copy(y)
        board.signalProcessor.gain.update(y)
        y /= board.signalProcessor.gain.value
        scale = config.settings["devices"][board.board]["effect_opts"]["Energy"]["scale"]
        # Scale by the width of the LED strip
        y *= float((config.settings["devices"][board.board]["configuration"]["N_PIXELS"] * scale) - 1)
        y = np.copy(util.interpolate(y, config.settings["devices"][board.board]["configuration"]["N_PIXELS"] // 2))
        # Map color channels according to energy in the different freq bands
        #y = np.copy(util.interpolate(y, config.settings["devices"][board.board]["configuration"]["N_PIXELS"] // 2))
        diff = y - board.visualizer.prev_spectrum
        board.visualizer.prev_spectrum = np.copy(y)
        spectrum = np.copy(board.visualizer.prev_spectrum)
        spectrum = np.array([j for i in zip(spectrum,spectrum) for j in i])
        # Color channel mappings
        r = int(np.mean(spectrum[:len(spectrum) // 3]**scale)*config.settings["devices"][board.board]["effect_opts"]["Energy"]["r_multiplier"])
        g = int(np.mean(spectrum[len(spectrum) // 3: 2 * len(spectrum) // 3]**scale)*config.settings["devices"][board.board]["effect_opts"]["Energy"]["g_multiplier"])
        b = int(np.mean(spectrum[2 * len(spectrum) // 3:]**scale)*config.settings["devices"][board.board]["effect_opts"]["Energy"]["b_multiplier"])
        # Assign color to different frequency regions
        board.visualizer.output[0, :r] = 255
        board.visualizer.output[0, r:] = 0
        board.visualizer.output[1, :g] = 255
        board.visualizer.output[1, g:] = 0
        board.visualizer.output[2, :b] = 255
        board.visualizer.output[2, b:] = 0
        # Apply blur to smooth the edges
        board.visualizer.output[0, :] = gaussian_filter1d(board.visualizer.output[0, :], sigma=config.settings["devices"][board.board]["effect_opts"]["Energy"]["blur"])
        board.visualizer.output[1, :] = gaussian_filter1d(board.visualizer.output[1, :], sigma=config.settings["devices"][board.board]["effect_opts"]["Energy"]["blur"])
        board.visualizer.output[2, :] = gaussian_filter1d(board.visualizer.output[2, :], sigma=config.settings["devices"][board.board]["effect_opts"]["Energy"]["blur"])
        if config.settings["devices"][board.board]["effect_opts"]["Energy"]["mirror"]:
            p = np.concatenate((board.visualizer.output[:, ::-2], board.visualizer.output[:, ::2]), axis=1)
        else:
            p = board.visualizer.output
        
        return p