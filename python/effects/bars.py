import numpy as np
import util

from effects.effect import Effect


class Bars(Effect):
    """The strip split into blocks, each lit by its part of the spectrum"""
    def __init__(self, visualizer):
        self.effectName = "Bars"
        self.offset = 0

    def visualize(self, board, y):
        options = board.effectConfig["Bars"]
        features = board.features
        n = board.config["N_PIXELS"]
        resolution = options["resolution"]
        levels = util.interpolate(features.bins, n)
        gradient = board.visualizer.gradient(options["color_mode"], self.offset)
        output = np.zeros((3, n))
        start = 0
        for block in np.array_split(np.arange(n), resolution):
            # Steep curve so blocks drop out between hits instead of idling half lit
            level = levels[block].max() ** 2.5
            output[:, block] = gradient[:, start, np.newaxis] * level
            start += len(block)
        output *= self.dynamics(features)
        self.offset += options["roll_speed"] * (-1 if options["reverse_roll"] else 1)
        if options["flip_lr"]:
            output = np.fliplr(output)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
