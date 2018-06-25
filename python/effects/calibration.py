from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util


from effects.effect import Effect

class Calibration(Effect):
	nonReactive = True
	def __init__(self, visualizer):
	    self.effectName = "Calibration"

	def visualize(self, board, y):
	    output = np.array([
	  		[board.effectConfig["Calibration"]["r"] for i in range(board.config["N_PIXELS"])],
      		[board.effectConfig["Calibration"]["g"] for i in range(board.config["N_PIXELS"])],
       		[board.effectConfig["Calibration"]["b"] for i in range(board.config["N_PIXELS"])]
        ])

	    return output
