import numpy as np
import util

from effects.effect import Effect


class Scroll(Effect):
    """Colour flows out from the start of the strip, with the bass, mids and treble
    taking the start, middle and end colours of the palette"""
    def __init__(self, visualizer):
        self.output = np.zeros((3, visualizer.board.config["N_PIXELS"]))

    def visualize(self, board, y):
        options = board.effectConfig["Scroll"]
        features = board.features
        n = board.config["N_PIXELS"]
        gradient = board.visualizer.gradient(options["color_mode"])
        colours = gradient[:, [0, n // 2, n - 1]].T.astype(float)  # bass, mids, treble
        # Squared so a band only shows when it is actually pushing, not idling mid-range
        bands = np.array([features.bass, features.mid, features.treble]) ** 2
        new = np.minimum(bands @ colours * self.dynamics(features), 255)

        speed = options["speed"]
        self.output[:, speed:] = self.output[:, :-speed] * self.fade(options["trail"])
        self.output[:, :speed] = new[:, np.newaxis]
        output = util.blur(self.output, options["blur"])
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
