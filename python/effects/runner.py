import numpy as np
import util

from effects.effect import Effect


class RunnerReactive(Effect):
    def __init__(self, visualizer):
        self.effectName = "Reactive Runner"
        self.position = 0
        self.pixels = np.arange(visualizer.board.config["N_PIXELS"])

    def visualize(self, board, y):
        options = board.effectConfig["RunnerReactive"]
        # A travelling sine wave, coloured by the gradient and scaled by the music via Wavelength
        wave = (np.sin(self.pixels * options["times"] + self.position / options["divide"]) + options["add"]) * np.cos(self.pixels)
        gradient = board.visualizer.gradient(options["color_mode"])[:, :board.config["N_PIXELS"]]
        output = wave * gradient
        wavelength = board.visualizer.effects["Wavelength"].visualize(board, y)
        output = output * (((wavelength[0] + wavelength[1] + wavelength[1]) / 3) / 10)
        if options["blur"] > 0:
            output = util.blur(output, options["blur"])
        self.position += 1
        return output
