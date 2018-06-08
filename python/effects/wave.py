from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import lib.config  as config
import util

from effects.effect import Effect

class Wave(Effect):
    wave_wipe_count = 0
    def __init__(self, board):
        self.effectName = "Wave"

    def visualize(self, board, y):
       # print('Beat vis called')
        outputGradient = np.array(
            [
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][0][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][1][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][2][:board.config["N_PIXELS"]],
            ]
        )
        if board.visualizer.current_freq_detects["beat"]:
            output = np.zeros((3,board.config["N_PIXELS"]))
            output[0][:] = np.divide(outputGradient[2], 2)
            output[1][:] = np.divide(outputGradient[1], 2)
            output[2][:] = np.divide(outputGradient[0], 2)

            self.wave_wipe_count = board.effectConfig["Wave"]["wipe_len"]
        else:
            output = np.copy(board.visualizer.prev_output)
            #for i in range(len(board.visualizer.prev_output)):
            #    output[i] = np.hsplit(board.visualizer.prev_output[i],2)[0]
            output = np.multiply(board.visualizer.prev_output,board.effectConfig["Wave"]["decay"])

            for i in range(self.wave_wipe_count):
                output[0][i] = outputGradient[0][i]
                output[0][-i] = outputGradient[0][i]
                output[1][i] = outputGradient[1][i]
                output[1][-i] = outputGradient[1][i]
                output[2][i] = outputGradient[2][i]
                output[2][-i] = outputGradient[2][i]
            
            if self.wave_wipe_count > board.config["N_PIXELS"]//2:
                self.wave_wipe_count = board.config["N_PIXELS"]//2
            self.wave_wipe_count += board.effectConfig["Wave"]["wipe_speed"]
 
        return output



