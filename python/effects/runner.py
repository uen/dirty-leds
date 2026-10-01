import numpy as np
import util

from effects.effect import Effect


class RunnerReactive(Effect):
    """A shimmering wave that travels in time with the music and glows with the bass"""
    def __init__(self, visualizer):
        self.effectName = "Reactive Runner"
        self.position = 0.0
        self.pixels = np.arange(visualizer.board.config["N_PIXELS"])

    def visualize(self, board, y):
        options = board.effectConfig["RunnerReactive"]
        features = board.features
        n = board.config["N_PIXELS"]
        # A travelling sine wave with a fixed per-pixel shimmer (|cos| of the pixel index)
        wave = (np.sin(self.pixels * options["times"] + self.position / options["divide"]) + options["add"]) \
            * np.abs(np.cos(self.pixels))
        gradient = board.visualizer.gradient(options["color_mode"])[:, :n]
        # Lit where its part of the spectrum is loud, flaring on kicks
        levels = np.repeat(util.interpolate(features.bins, n // 2), 2)
        glow = (0.3 + 0.7 * levels) * (0.6 + 0.4 * features.kick) * self.dynamics(features)
        output = wave * gradient * glow
        if options["blur"] > 0:
            output = util.blur(output, options["blur"])
        # Moves three steps a frame at 120 bpm, faster or slower with the tempo
        self.position += 3 * features.tempo / 120
        return output
