import random
from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util
from time import sleep

from effects.effect import Effect

fire = [255, 96, 12]

class Fire(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Fire"

        
    def visualize(self, board, y):

        output = np.array([
            [fire[0] for i in range(board.config["N_PIXELS"])],
            [fire[1] for i in range(board.config["N_PIXELS"])],
            [fire[2] for i in range(board.config["N_PIXELS"])]
        ])

#        flicker = [random.randomint(0, 70) for i in range(board.config("N_PIXELS"))]
        flicker = np.random.randint(60, size=board.config["N_PIXELS"])

        flicker = np.array([
            [flicker[i] for i in range(board.config["N_PIXELS"])],
            [flicker[i] for i in range(board.config["N_PIXELS"])],
            [flicker[i] for i in range(board.config["N_PIXELS"])],
        ])

        output[0] = np.subtract(output[0], flicker[0]+40)
        output[1] = np.subtract(output[1], flicker[1]+40)
        output[2] = np.subtract(output[2], flicker[2]+40)

        r = np.clip(output[0], 0, 255)
        g = np.clip(output[1], 0, 255)
        b = np.clip(output[2], 0, 255)


        r = np.rint(r)
        g = np.rint(g)
        b = np.rint(b)


        r = gaussian_filter1d(r, sigma=board.effectConfig["Spectrum"]["blur"]*8)
        g = gaussian_filter1d(g, sigma=board.effectConfig["Spectrum"]["blur"]*8)
        b = gaussian_filter1d(b, sigma=board.effectConfig["Spectrum"]["blur"]*8)
        

       
        output = np.array([r,g,b])

        return output