import numpy as np
import config
import random
import util

from effects.effect import Effect


class Power(Effect):
    def __init__(self, visualizer):
        self.effectName = "Power"
        self.power_brightness = 0
        self.power_indexes = []

    def visualize(self, board, y):
        #board.effectConfig["Power"]["color_mode"]
        # Bit of fiddling with the y values
        y = np.copy(util.interpolate(y, board.config["N_PIXELS"] // 2))
        board.signalProcessor.common_mode.update(y)
        # Color channel mappings
        r = board.signalProcessor.r_filt.update(y - board.signalProcessor.common_mode.value)
        r = np.repeat(r, 2)
        output = np.array([board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][0, :board.config["N_PIXELS"]]*r,
                           board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][1, :board.config["N_PIXELS"]]*r,
                           board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][2, :board.config["N_PIXELS"]]*r])
        # if there's a high (eg clap):
        if board.visualizer.current_freq_detects["high"]:
            self.power_brightness = 1.0
            # Generate random indexes
            self.power_indexes = random.sample(range(board.config["N_PIXELS"]), board.config["N_PIXELS"]//6)
            #print("ye")
        # Assign colour to the random indexes
        if self.power_indexes:
            spark = np.array(config.settings["colors"][board.effectConfig["Power"]["s_color"]]) * self.power_brightness
            output[:, self.power_indexes] = spark.astype(int)[:, np.newaxis]
        # Remove a quarter of the sparks for next time
        self.power_indexes = random.sample(self.power_indexes, len(self.power_indexes) - len(self.power_indexes) // 4)
        if len(self.power_indexes) <= 4:
            self.power_indexes = []
        # Fade the colour of the sparks out a bit for next time
        if self.power_brightness > 0:
            self.power_brightness -= 0.05
        # Calculate length of bass bar based on max bass frequency volume and length of strip
        strip_len = int((board.config["N_PIXELS"]//3)*max(y[:int(board.config["N_FFT_BINS"]*0.2)]))
        # Add the bass bars into the output. Colour proportional to length
        output[0][:strip_len] = board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][0][strip_len]
        output[1][:strip_len] = board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][1][strip_len]
        output[2][:strip_len] = board.visualizer.multicolor_modes[board.effectConfig["Power"]["color_mode"]][2][strip_len]
        if board.effectConfig["Power"]["flip_lr"]:
            output = np.fliplr(output)
        if board.effectConfig["Power"]["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output

