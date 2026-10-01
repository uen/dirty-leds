import numpy as np

from effects.effect import Effect


class Calibration(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Calibration"

    def visualize(self, board, y):
        options = board.effectConfig["Calibration"]
        colour = np.array([options["r"], options["g"], options["b"]])
        return np.tile(colour[:, np.newaxis], (1, board.config["N_PIXELS"]))
