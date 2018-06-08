from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import lib.config  as config
import util

from effects.effect import Effect


class Fade(Effect):
	nonReactive = True
	def __init__(self, visualizer):
	    self.effectName = "Fade"

	def visualize(self, board, y):
		output = np.array([
        	[
        		board.visualizer.multicolor_modes[board.effectConfig["Fade"]["color_mode"]][0][0] 
        		for i in range(board.config["N_PIXELS"])
        	],
        	[
        		board.visualizer.multicolor_modes[board.effectConfig["Fade"]["color_mode"]][1][0]
        		for i in range(board.config["N_PIXELS"])
        	],
            
            [
            	board.visualizer.multicolor_modes[board.effectConfig["Fade"]["color_mode"]][2][0] 
            	for i in range(board.config["N_PIXELS"])
            ]
        ])

		board.visualizer.multicolor_modes[board.effectConfig["Fade"]["color_mode"]] = np.roll(
			board.visualizer.multicolor_modes[board.effectConfig["Fade"]["color_mode"]],
			board.effectConfig["Fade"]["roll_speed"]*(-1 if board.effectConfig["Fade"]["reverse"] else 1),
			axis=1
        )
	    
		return output

