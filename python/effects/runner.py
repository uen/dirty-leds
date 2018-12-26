from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util

from effects.effect import Effect
from effects.wavelength import Wavelength

import math
class RunnerReactive(Effect):
    def __init__(self, board):
        self.effectName = "Wave"
        self.position = 0
    def visualize(self, board, y):
       # print('Beat vis called')
        output = np.array([
            [(((math.sin(i * board.effectConfig["RunnerReactive"]["times"] + (self.position/board.effectConfig["RunnerReactive"]["divide"]))+board.effectConfig["RunnerReactive"]["add"])*((math.cos(i))))) for i in range(board.config["N_PIXELS"])],
            [(((math.sin(i * board.effectConfig["RunnerReactive"]["times"] + (self.position/board.effectConfig["RunnerReactive"]["divide"]))+board.effectConfig["RunnerReactive"]["add"])*((math.cos(i))))) for i in range(board.config["N_PIXELS"])],
            [(((math.sin(i * board.effectConfig["RunnerReactive"]["times"] + (self.position/board.effectConfig["RunnerReactive"]["divide"]))+board.effectConfig["RunnerReactive"]["add"])*((math.cos(i))))) for i in range(board.config["N_PIXELS"])]
        ])


        outputGradient = np.array(
            [
                board.visualizer.multicolor_modes[board.effectConfig["RunnerReactive"]["color_mode"]][0][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["RunnerReactive"]["color_mode"]][1][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["RunnerReactive"]["color_mode"]][2][:board.config["N_PIXELS"]],
            ]
        )

        output[0] = np.multiply(output[0], outputGradient[0])
        output[1] = np.multiply(output[1], outputGradient[1])
        output[2] = np.multiply(output[2], outputGradient[2])


        wavelength = board.visualizer.effects["Wavelength"].visualize(board, y)
        output[0] = np.multiply(output[0], ((wavelength[0]+wavelength[1]+wavelength[1])/3)/10)
        output[1] = np.multiply(output[1], ((wavelength[0]+wavelength[1]+wavelength[1])/3)/10)
        output[2] = np.multiply(output[2], ((wavelength[0]+wavelength[1]+wavelength[1])/3)/10)




        if(board.effectConfig["RunnerReactive"]["blur"] > 0):
            output[0] = gaussian_filter1d(output[0], sigma=board.effectConfig["RunnerReactive"]["blur"])
            output[1] = gaussian_filter1d(output[1], sigma=board.effectConfig["RunnerReactive"]["blur"])
            output[2] = gaussian_filter1d(output[2], sigma=board.effectConfig["RunnerReactive"]["blur"])

        self.position+=1

        return output



