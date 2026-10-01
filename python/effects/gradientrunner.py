from scipy.ndimage import gaussian_filter1d
import numpy as np

from effects.effect import Effect


class Runner(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Runner"
        self.position = 0
        self.pixels = np.arange(visualizer.board.config["N_PIXELS"])

    def visualize(self, board, y):
        options = board.effectConfig["Runner"]
        # A sine wave travelling along the strip, coloured by the gradient
        wave = (np.sin(self.pixels * options["times"] + self.position / options["divide"]) + options["add"]) * 255
        gradient = board.visualizer.gradient(options["color_mode"])[:, :board.config["N_PIXELS"]]
        output = wave * (gradient / 255)
        if options["blur"] > 0:
            output = gaussian_filter1d(output, sigma=options["blur"])
        self.position += 1
        return output
