from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import random
import util
import copy

from effects.effect import Effect


class Stars(Effect):
    nonReactive = True

    star_brightness = 0
    stars = {}
    dead_stars = []
    def __init__(self, visualizer):
        self.effectName = "Stars"
        
    def visualize(self, board, y):
        output = np.zeros((3,board.config["N_PIXELS"]))
        output[0][10] = 255

        if random.random() < board.effectConfig["Stars"]["star_rate"]:
           self.stars[random.randint(0, board.config["N_PIXELS"]-1)] = 0

        for star in copy.copy(self.stars):
            self.stars[star] += board.effectConfig["Stars"]["star_speed"]
            brightness = ((((((self.stars[star]) if self.stars[star]<1 else 1-(self.stars[star]-1))))) ** 10)
            output[0][star] = round(255 * brightness)
            output[1][star] = round(255 * brightness)
            output[2][star] = round(255 * brightness)

            #output[1][star] = 255 * ((-1*(-1+(self.stars[star] % 1))) if self.stars[star] > 1 else self.stars[star])
            #output[2][star] = 255 * ((-1*(-1+(self.stars[star] % 1))) if self.stars[star] > 1 else self.stars[star])

            if(self.stars[star] >= 2):
                del self.stars[star]

        # print(output)
        return output

