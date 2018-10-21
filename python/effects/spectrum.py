from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util

from effects.effect import Effect


class Spectrum(Effect):
    def __init__(self, visualizer):
        self.effectName = "Spectrum"

    def visualize(self, board, y):
        y = np.copy(util.interpolate(y, board.config["N_PIXELS"] // 2))
        board.signalProcessor.common_mode.update(y)
        diff = y - board.visualizer.prev_spectrum
        board.visualizer.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = board.signalProcessor.r_filt.update(y - board.signalProcessor.common_mode.value)
        g = np.abs(diff)
        b = board.signalProcessor.b_filt.update(np.copy(y))
            
        # Mirror the color channels for symmetric output
        r = np.concatenate((r[::-1], r))
        g = np.concatenate((g[::-1], g))
        b = np.concatenate((b[::-1], b))

        outputGradient = np.array(
            [
                board.visualizer.multicolor_modes[board.effectConfig["Spectrum"]["color_mode"]][0][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Spectrum"]["color_mode"]][1][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Spectrum"]["color_mode"]][2][:board.config["N_PIXELS"]],
            ]
        )

        r = np.multiply(r, outputGradient[0])
        g = np.multiply(g, outputGradient[1])
        b = np.multiply(b, outputGradient[2])

        r = gaussian_filter1d(r, sigma=board.effectConfig["Spectrum"]["blur"]*2)
        g = gaussian_filter1d(g, sigma=board.effectConfig["Spectrum"]["blur"]*2)
        b = gaussian_filter1d(b, sigma=board.effectConfig["Spectrum"]["blur"]*2)

        r = np.minimum(255, np.multiply(r, 2))
        g = np.minimum(255, np.multiply(g, 2))
        b = np.minimum(255, np.multiply(b, 2))

        output = np.array([r,g,b])

        board.visualizer.prev_spectrum = y
        return output