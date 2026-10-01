import numpy as np
import config

from effects.effect import Effect


class Single(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Single"

    def visualize(self, board, y):
        colour = np.array(config.settings["colors"][board.effectConfig["Single"]["color"]])
        return np.tile(colour[:, np.newaxis], (1, board.config["N_PIXELS"]))
