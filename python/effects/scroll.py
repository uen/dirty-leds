from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import lib.config  as config
import util


from effects.effect import Effect

class Scroll(Effect):
    def __init__(self, board):        
        pass

    def visualize(self, board, y):
        y = y**4.0
        # signal_processers[board.board].gain.update(y)
        # y /= signal_processers[board.board].gain.value
        # y *= 255.0

        n_pixels = config.settings["devices"][board.board]["configuration"]["N_PIXELS"]
        y = np.copy(util.interpolate(y, n_pixels // 2))
        board.signalProcessor.common_mode.update(y)
        diff = y - board.visualizer.prev_spectrum
        board.visualizer.prev_spectrum = np.copy(y)
        # split spectrum up
        # r = signal_processers[board.board].r_filt.update(y - signal_processers[board.board].common_mode.value)
        # g = np.abs(diff)
        # b = signal_processers[board.board].b_filt.update(np.copy(y))
        y = np.clip(y, 0, 1)
        lows = y[:len(y) // 6]
        mids = y[len(y) // 6: 2 * len(y) // 5]
        high = y[2 * len(y) // 5:]
        # max values
        lows_max = np.max(lows)#*config.settings["devices"][board.board]["effect_opts"]["Scroll"]["lows_multiplier"])
        mids_max = float(np.max(mids))#*config.settings["devices"][board.board]["effect_opts"]["Scroll"]["mids_multiplier"])
        high_max = float(np.max(high))#*config.settings["devices"][board.board]["effect_opts"]["Scroll"]["high_multiplier"])
        # indexes of max values
        # map to colour gradient
        lows_val = (np.array(config.settings["colors"][config.settings["devices"][board.board]["effect_opts"]["Scroll"]["lows_color"]]) * lows_max).astype(int)
        mids_val = (np.array(config.settings["colors"][config.settings["devices"][board.board]["effect_opts"]["Scroll"]["mids_color"]]) * mids_max).astype(int)
        high_val = (np.array(config.settings["colors"][config.settings["devices"][board.board]["effect_opts"]["Scroll"]["high_color"]]) * high_max).astype(int)
        # Scrolling effect window
        speed = config.settings["devices"][board.board]["effect_opts"]["Scroll"]["speed"]
        board.visualizer.output[:, speed:] = board.visualizer.output[:, :-speed]
        board.visualizer.output = (board.visualizer.output * config.settings["devices"][board.board]["effect_opts"]["Scroll"]["decay"]).astype(int)
        board.visualizer.output = gaussian_filter1d(board.visualizer.output, sigma=config.settings["devices"][board.board]["effect_opts"]["Scroll"]["blur"])
        # Create new color originating at the center
        board.visualizer.output[0, :speed] = lows_val[0] + mids_val[0] + high_val[0]
       	board.visualizer.output[1, :speed] = lows_val[1] + mids_val[1] + high_val[1]
        board.visualizer.output[2, :speed] = lows_val[2] + mids_val[2] + high_val[2]
        # Update the LED strip
        #return np.concatenate((vis.prev_spectrum[:, ::-speed], vis.prev_spectrum), axis=1)
        if config.settings["devices"][board.board]["effect_opts"]["Scroll"]["mirror"]:
            p = np.concatenate((board.visualizer.output[:, ::-2], board.visualizer.output[:, ::2]), axis=1)
        else:
            p = visualizer.output
        return p

        