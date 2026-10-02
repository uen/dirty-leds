import numpy as np
import util
from lib.features import Envelope

from effects.effect import Effect

# The whole gradient glows this much even when quiet, so the strip reads as a map
BASE_GLOW = 0.1


class Wavelength(Effect):
    """The palette laid along the strip from bass to treble, each part lighting up
    when its frequencies are loud"""
    def __init__(self, visualizer):
        self.effectName = "Wavelength"
        self.offset = 0
        # Extra smoothing on top of the features so peaks swell and settle
        self.levels = Envelope(0.05, 0.25, 1 / 60, value=np.zeros(visualizer.board.config["N_PIXELS"]))

    def visualize(self, board, y):
        options = board.effectConfig["Wavelength"]
        features = board.features
        n = board.config["N_PIXELS"]
        levels = self.levels.update(util.interpolate(features.bins, n))
        levels = BASE_GLOW + (1 - BASE_GLOW) * levels ** 2
        gradient = board.visualizer.gradient(options["color_mode"], self.offset)
        gradient = gradient[:, n:] if options["reverse_grad"] else gradient[:, :n]
        output = gradient * levels * self.dynamics(features, floor=0.5)
        self.offset += options["roll_speed"] * (-1 if options["reverse_roll"] else 1)
        output = util.blur(output, options["blur"])
        if options["flip_lr"]:
            output = np.fliplr(output)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
