import numpy as np
import util

from effects.effect import Effect


class Spectrum(Effect):
    """The frequency spectrum mirrored out from the centre, bass in the middle"""
    def __init__(self, visualizer):
        self.effectName = "Spectrum"
        # Previous frame, the green channel shows how much each part changed
        self.prev = np.zeros(visualizer.board.config["N_PIXELS"] // 2)

    def visualize(self, board, y):
        options = board.effectConfig["Spectrum"]
        features = board.features
        n = board.config["N_PIXELS"]
        levels = util.interpolate(features.bins, n // 2)
        change = np.abs(levels - self.prev)
        self.prev = levels
        half = np.array([levels, np.minimum(1.0, change * 4), levels])
        # Mirror so bass sits in the middle of the strip
        shape = np.concatenate((half[:, ::-1], half), axis=1)
        gradient = board.visualizer.gradient(options["color_mode"])[:, :shape.shape[1]]
        output = shape * gradient * self.dynamics(features)
        output = util.blur(output, options["blur"] * 2)
        return np.minimum(255, output * 1.5)
