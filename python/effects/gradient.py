import numpy as np

from effects.effect import Effect


class Gradient(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Gradient"
        self.offset = 0

    def visualize(self, board, y):
        options = board.effectConfig["Gradient"]
        output = board.visualizer.gradient(options["color_mode"], self.offset)[:, :board.config["N_PIXELS"]]
        self.offset += options["roll_speed"] * (-1 if options["reverse"] else 1)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
