import numpy as np

from effects.effect import Effect


class Fade(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Fade"
        self.offset = 0

    def visualize(self, board, y):
        options = board.effectConfig["Fade"]
        # The whole strip shows one colour, walking along the gradient
        colour = board.visualizer.gradient(options["color_mode"], self.offset)[:, 0]
        self.offset += options["roll_speed"] * (-1 if options["reverse"] else 1)
        return np.tile(colour[:, np.newaxis], (1, board.config["N_PIXELS"]))
