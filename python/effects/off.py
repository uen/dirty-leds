from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util

from effects.effect import Effect

class Off(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Off"

    def visualize(self, board, y):
        output = np.zeros((3, board.config["N_PIXELS"]))

        return output