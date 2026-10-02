import numpy as np
import util
from lib.features import Envelope

from effects.effect import Effect


# A bar is a bright head with a dim glow behind it, like a level meter, so long
# strips don't turn into a wall of light
BODY = 0.25


class Energy(Effect):
    """Bars for the bass, mids and treble that grow from the start of the strip,
    in three colours from the palette"""
    def __init__(self, visualizer):
        self.effectName = "Energy"
        # Bars shoot out on hits and sink back gently instead of snapping
        self.lengths = Envelope(0.03, 0.3, 1 / 60, value=np.zeros(3))

    def visualize(self, board, y):
        options = board.effectConfig["Energy"]
        features = board.features
        n = board.config["N_PIXELS"]
        reach = options["scale"] * n * self.dynamics(features, floor=0.4)
        bands = np.array([features.bass * options["r_multiplier"],
                          features.mid * options["g_multiplier"],
                          features.treble * options["b_multiplier"]])
        # Squared so bars only reach far on strong hits
        lengths = self.lengths.update(np.clip(bands ** 2 * reach, 0, n))

        position = np.arange(n)
        behind = lengths[:, np.newaxis] - position  # pixels from each bar's head, back toward the start
        head = max(2.0, 0.04 * n)
        levels = np.where(behind >= 0,
                          BODY + (1 - BODY) * np.exp(-behind / head),
                          np.exp(-(behind / head) ** 2))
        levels *= lengths[:, np.newaxis] > 0.5
        gradient = board.visualizer.gradient(options["color_mode"])
        colours = gradient[:, [0, n // 2, n - 1]].T  # bass, mids, treble colours
        # Brightest bar wins where they overlap, so the start doesn't wash out to white
        output = (colours[:, :, np.newaxis] * levels[:, np.newaxis, :]).max(axis=0)
        output = util.blur(output * (0.5 + 0.5 * self.dynamics(features)), options["blur"])
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
