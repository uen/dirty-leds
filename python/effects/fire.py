from scipy.ndimage import gaussian_filter1d
import numpy as np

from effects.effect import Effect

FIRE = np.array([255, 96, 12])


class Fire(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Fire"

    def visualize(self, board, y):
        # Every pixel dims the same random amount on all channels, like a flame flickering
        flicker = np.random.randint(60, size=board.config["N_PIXELS"])
        output = np.rint(np.clip(FIRE[:, np.newaxis] - (flicker + 40), 0, 255))
        return gaussian_filter1d(output, sigma=board.effectConfig["Spectrum"]["blur"] * 8)
