import numpy as np
import util

from effects.effect import Effect


class Energy(Effect):
    """Red, green and blue bars whose lengths follow the bass, mids and treble"""
    def __init__(self, visualizer):
        self.effectName = "Energy"
        self.output = np.zeros((3, visualizer.board.config["N_PIXELS"]))

    def visualize(self, board, y):
        options = board.effectConfig["Energy"]
        features = board.features
        n = board.config["N_PIXELS"]
        # Bars reach at most `scale` of the strip, and only in the biggest parts of the song
        reach = options["scale"] * n * self.dynamics(features, floor=0.4)
        lengths = np.array([features.bass * options["r_multiplier"],
                            features.mid * options["g_multiplier"],
                            features.treble * options["b_multiplier"]]) * reach
        self.output[:] = np.where(np.arange(n) < np.clip(lengths, 0, n)[:, np.newaxis], 255.0, 0.0)
        output = util.blur(self.output, options["blur"])
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
