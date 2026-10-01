from scipy.ndimage import gaussian_filter1d
import numpy as np

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
            output = gaussian_filter1d(output, sigma=options["blur"])
        self.position += 1
        return output
