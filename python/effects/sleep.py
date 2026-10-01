import numpy as np
import datetime

from effects.effect import Effect

class Sleep(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Sleep"

    def visualize(self, board, y):
        brightness = 0
        now = datetime.datetime.now()
        activateAt = datetime.datetime(now.year, now.month, now.day, board.effectConfig["Sleep"]["hour"], board.effectConfig["Sleep"]["minute"], 0)

        secondsActive = board.effectConfig["Sleep"]["minutes_fade"]*60

        secondsAfter = (now - activateAt).total_seconds()
        if secondsAfter > 0 and secondsAfter <= secondsActive:
            brightness = 150 * (secondsAfter / secondsActive)

        return np.full((3, board.config["N_PIXELS"]), brightness)