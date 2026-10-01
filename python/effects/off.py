import numpy as np

from effects.effect import Effect

class Off(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Off"

    def visualize(self, board, y):
        output = np.zeros((3, board.config["N_PIXELS"]))

        return output