import numpy as np
import util

from effects.effect import Effect

FIRE = np.array([255, 96, 12])


class Fire(Effect):
    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Fire"
        self.output = None

    def visualize(self, board, y):
        # A new flicker every `delay` seconds, holding the last one in between
        if self.output is None or self.steps(board.effectConfig["Fire"]["delay"]):
            # Every pixel dims the same random amount on all channels, like a flame flickering
            flicker = np.random.randint(60, size=board.config["N_PIXELS"])
            output = np.rint(np.clip(FIRE[:, np.newaxis] - (flicker + 40), 0, 255))
            self.output = util.blur(output, board.effectConfig["Spectrum"]["blur"] * 8)
        return self.output
