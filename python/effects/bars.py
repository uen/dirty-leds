from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import random
import util


from effects.effect import Effect

class Bars(Effect):
    def __init__(self, visualizer):
        self.effectName = "Bars"

    def visualize(self, board, y):
        y = np.copy(util.interpolate(y, board.config["N_PIXELS"] // 2))
        board.signalProcessor.common_mode.update(y)
        board.prev_spectrum = np.copy(y)
        # Color channel mappings
        r = board.signalProcessor.r_filt.update(y - board.signalProcessor.common_mode.value)
        r = np.array([j for i in zip(r,r) for j in i])
        # Split y into [resulution] chunks and calculate the average of each
        max_values = np.array([max(i) for i in np.array_split(r, board.effectConfig["Bars"]["resolution"])])
        max_values = np.clip(max_values, 0, 1)
        color_sets = []
        for i in range(board.effectConfig["Bars"]["resolution"]):
            # [r,g,b] values from a multicolour gradient array at [resulution] equally spaced intervals
            color_sets.append([board.visualizer.multicolor_modes[board.effectConfig["Bars"]["color_mode"]]\
                              [j][i*(board.config["N_PIXELS"]//board.effectConfig["Bars"]["resolution"])] for j in range(3)])
        output = np.zeros((3,board.config["N_PIXELS"]))
        chunks = np.array_split(output[0], board.effectConfig["Bars"]["resolution"])
        n = 0
        # Assign blocks with heights corresponding to max_values and colours from color_sets
        for i in range(len(chunks)):
            m = len(chunks[i])
            for j in range(3):
                output[j][n:n+m] = color_sets[i][j]*max_values[i]
            n += m
        board.visualizer.multicolor_modes[board.effectConfig["Bars"]["color_mode"]] = np.roll(
                    board.visualizer.multicolor_modes[board.effectConfig["Bars"]["color_mode"]],
                    board.effectConfig["Bars"]["roll_speed"]*(-1 if board.effectConfig["Bars"]["reverse_roll"] else 1),
                    axis=1)
        if board.effectConfig["Bars"]["flip_lr"]:
            output = np.fliplr(output)
        if board.effectConfig["Bars"]["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output

