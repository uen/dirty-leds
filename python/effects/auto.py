from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import lib.config  as config
import util
from effects.effect import Effect


class Auto(Effect):
    autoTimer = 0
    autoEffect = 0
    effectKeys = []
    def __init__(self, visualizer):
        self.effectName = "Auto"
        self.effectKeys = list(visualizer.effects.keys())

    def visualize(self, board, y):
        k = self.effectKeys[self.autoEffect % len(self.effectKeys)]

        if(k == 'Auto' or board.visualizer.effects[k].nonReactive):
            self.autoEffect+=1;
            return self.visualize(board, y)

        if(board.visualizer.current_freq_detects["beat"] and self.visuaself.autoTimer > 500):
            self.autoTimer = 0
            self.autoEffect += 1

        self.autoTimer += 1

        return board.visualizer.effects[k].visualize(board, y)
