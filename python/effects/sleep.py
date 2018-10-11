from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import datetime
import util

from effects.effect import Effect

class Sleep(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Sleep"

    def visualize(self, board, y):
        brightness = 0
        now = datetime.datetime.now()
        activateAt = datetime.datetime(now.year, now.month, now.day, config.settings["devices"][board.board]["effect_opts"]["Sleep"]["hour"], config.settings["devices"][board.board]["effect_opts"]["Sleep"]["minute"], 0)

        secondsActive = config.settings["devices"][board.board]["effect_opts"]["Sleep"]["minutes_fade"]*60

        secondsAfter = (now - activateAt).total_seconds()
        if secondsAfter > 0 and secondsAfter <= secondsActive:
            brightness = 150 * (secondsAfter / secondsActive)

        output = np.array([
            [brightness for i in range(board.config["N_PIXELS"])],
            [brightness for i in range(board.config["N_PIXELS"])],
            [brightness for i in range(board.config["N_PIXELS"])],
        ])

        return output