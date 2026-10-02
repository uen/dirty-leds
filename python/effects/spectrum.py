import numpy as np
import util
from lib.features import Envelope

from effects.effect import Effect


class Spectrum(Effect):
    """The frequency spectrum mirrored out from the centre, bass in the middle"""
    def __init__(self, visualizer):
        self.effectName = "Spectrum"
        # Smoothing on top of the features so the spectrum swells and settles instead of flickering
        self.levels = Envelope(0.04, 0.2, 1 / 60, value=np.zeros(visualizer.board.config["N_PIXELS"] // 2))

    def visualize(self, board, y):
        options = board.effectConfig["Spectrum"]
        features = board.features
        n = board.config["N_PIXELS"]
        # Steep curve so only the strong parts of the spectrum light up
        levels = self.levels.update(util.interpolate(features.bins, n // 2)) ** 2.5
        # Mirror so bass sits in the middle of the strip
        shape = np.concatenate((levels[::-1], levels))
        gradient = board.visualizer.gradient(options["color_mode"])[:, :len(shape)]
        output = shape * gradient * self.dynamics(features)
        output = util.blur(output, options["blur"] * 2)
        return np.minimum(255, output)
