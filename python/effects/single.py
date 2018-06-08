from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import lib.config  as config
import util

from effects.effect import Effect

class Single(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Single"

    def visualize(self, board, y):
        output = np.array([
            [config.settings["colors"][board.effectConfig["Single"]["color"]][0] for i in range(board.config["N_PIXELS"])],
            [config.settings["colors"][board.effectConfig["Single"]["color"]][1] for i in range(board.config["N_PIXELS"])],
            [config.settings["colors"][board.effectConfig["Single"]["color"]][2] for i in range(board.config["N_PIXELS"])]
        ])

        return output