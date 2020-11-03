from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util


from effects.effect import Effect

class Mood(Effect):
    nonReactive = True
    def __init__(self, visualizer):
        self.effectName = "Mood"
        self.delay = 0.05

    def visualize(self, board, y):
        output = np.array([
            board.visualizer.multicolor_modes[board.effectConfig["Mood"]["color_mode"]][0][:board.config["N_PIXELS"]],
            board.visualizer.multicolor_modes[board.effectConfig["Mood"]["color_mode"]][1][:board.config["N_PIXELS"]],
            board.visualizer.multicolor_modes[board.effectConfig["Mood"]["color_mode"]][2][:board.config["N_PIXELS"]]
        ])

        board.visualizer.multicolor_modes[board.effectConfig["Mood"]["color_mode"]] = np.roll(
            board.visualizer.multicolor_modes[board.effectConfig["Mood"]["color_mode"]],
            board.effectConfig["Mood"]["roll_speed"]*(-1 if board.effectConfig["Mood"]["reverse"] else 1),
            axis=1
        )

        
        if board.effectConfig["Mood"]["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output




    