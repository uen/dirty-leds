import numpy as np
import config
import util


from effects.effect import Effect

class Scroll(Effect):
    def __init__(self, visualizer):
        self.output = np.zeros((3, visualizer.board.config["N_PIXELS"]))

    def visualize(self, board, y):
        y = y**4.0
        # signal_processers[board.board].gain.update(y)
        # y /= signal_processers[board.board].gain.value
        # y *= 255.0

        n_pixels = board.config["N_PIXELS"]
        y = np.copy(util.interpolate(y, n_pixels // 2))
        board.signalProcessor.common_mode.update(y)
        # split spectrum up
        # r = signal_processers[board.board].r_filt.update(y - signal_processers[board.board].common_mode.value)
        # g = np.abs(diff)
        # b = signal_processers[board.board].b_filt.update(np.copy(y))
        y = np.clip(y, 0, 1)
        lows = y[:len(y) // 6]
        mids = y[len(y) // 6: 2 * len(y) // 5]
        high = y[2 * len(y) // 5:]
        # max values
        lows_max = np.max(lows)#*board.effectConfig["Scroll"]["lows_multiplier"])
        mids_max = float(np.max(mids))#*board.effectConfig["Scroll"]["mids_multiplier"])
        high_max = float(np.max(high))#*board.effectConfig["Scroll"]["high_multiplier"])
        # indexes of max values
        # map to colour gradient
        lows_val = (np.array(config.settings["colors"][board.effectConfig["Scroll"]["lows_color"]]) * lows_max).astype(int)
        mids_val = (np.array(config.settings["colors"][board.effectConfig["Scroll"]["mids_color"]]) * mids_max).astype(int)
        high_val = (np.array(config.settings["colors"][board.effectConfig["Scroll"]["high_color"]]) * high_max).astype(int)
        # Scrolling effect window
        speed = board.effectConfig["Scroll"]["speed"]
        self.output[:, speed:] = self.output[:, :-speed]
        self.output = (self.output * board.effectConfig["Scroll"]["decay"]).astype(int)
        self.output = util.blur(self.output, board.effectConfig["Scroll"]["blur"])
        # Create new color originating at the center
        self.output[0, :speed] = lows_val[0] + mids_val[0] + high_val[0]
       	self.output[1, :speed] = lows_val[1] + mids_val[1] + high_val[1]
        self.output[2, :speed] = lows_val[2] + mids_val[2] + high_val[2]
        # Update the LED strip
        if board.effectConfig["Scroll"]["mirror"]:
            p = np.concatenate((self.output[:, ::-2], self.output[:, ::2]), axis=1)
        else:
            p = self.output
        return p

        