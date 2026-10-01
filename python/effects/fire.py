import numpy as np
import util

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
        return util.blur(output, board.effectConfig["Spectrum"]["blur"] * 8)
