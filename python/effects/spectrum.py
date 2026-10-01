import numpy as np
import util

from effects.effect import Effect


class Spectrum(Effect):
    def __init__(self, visualizer):
        self.effectName = "Spectrum"
        # Previous frame, the green channel shows how much each pixel changed
        self.prev = np.zeros(visualizer.board.config["N_PIXELS"] // 2)

    def visualize(self, board, y):
        y = np.copy(util.interpolate(y, board.config["N_PIXELS"] // 2))
        board.signalProcessor.common_mode.update(y)
        diff = y - self.prev
        self.prev = np.copy(y)
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

        output = np.array([r, g, b]) * outputGradient
        output = util.blur(output, board.effectConfig["Spectrum"]["blur"]*2)
        return np.minimum(255, output * 2)