from scipy.ndimage import gaussian_filter1d
import numpy as np
import util

from effects.effect import Effect


class Wavelength(Effect):
    def __init__(self, visualizer):
        self.effectName = "Wavelength"
        self.offset = 0

    def visualize(self, board, y):
        y = np.copy(util.interpolate(y, board.config["N_PIXELS"] // 2))
        board.signalProcessor.common_mode.update(y)
        # Color channel mappings
        r = board.signalProcessor.r_filt.update(y - board.signalProcessor.common_mode.value)
        r = np.array([j for i in zip(r,r) for j in i])
        gradient = board.visualizer.gradient(board.effectConfig["Wavelength"]["color_mode"], self.offset)
        output = np.array([gradient[0][
                                    (board.config["N_PIXELS"] if board.effectConfig["Wavelength"]["reverse_grad"] else 0):
                                    (None if board.effectConfig["Wavelength"]["reverse_grad"] else board.config["N_PIXELS"]):]*r,
                           gradient[1][
                                    (board.config["N_PIXELS"] if board.effectConfig["Wavelength"]["reverse_grad"] else 0):
                                    (None if board.effectConfig["Wavelength"]["reverse_grad"] else board.config["N_PIXELS"]):]*r,
                           gradient[2][
                                    (board.config["N_PIXELS"] if board.effectConfig["Wavelength"]["reverse_grad"] else 0):
                                    (None if board.effectConfig["Wavelength"]["reverse_grad"] else board.config["N_PIXELS"]):]*r])
        self.offset += board.effectConfig["Wavelength"]["roll_speed"]*(-1 if board.effectConfig["Wavelength"]["reverse_roll"] else 1)
        output[0] = gaussian_filter1d(output[0], sigma=board.effectConfig["Wavelength"]["blur"])
        output[1] = gaussian_filter1d(output[1], sigma=board.effectConfig["Wavelength"]["blur"])
        output[2] = gaussian_filter1d(output[2], sigma=board.effectConfig["Wavelength"]["blur"])
        if board.effectConfig["Wavelength"]["flip_lr"]:
            output = np.fliplr(output)
        if board.effectConfig["Wavelength"]["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output