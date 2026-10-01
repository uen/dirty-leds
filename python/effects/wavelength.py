import numpy as np
import util

from effects.effect import Effect


class Wavelength(Effect):
    """A colour gradient along the strip, lit where its part of the spectrum is loud"""
    def __init__(self, visualizer):
        self.effectName = "Wavelength"
        self.offset = 0

    def visualize(self, board, y):
        options = board.effectConfig["Wavelength"]
        features = board.features
        n = board.config["N_PIXELS"]
        levels = np.repeat(util.interpolate(features.bins, n // 2), 2) ** 1.5
        gradient = board.visualizer.gradient(options["color_mode"], self.offset)
        gradient = gradient[:, n:] if options["reverse_grad"] else gradient[:, :n]
        output = gradient * levels * self.dynamics(features)
        self.offset += options["roll_speed"] * (-1 if options["reverse_roll"] else 1)
        output = util.blur(output, options["blur"])
        if options["flip_lr"]:
            output = np.fliplr(output)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
