from collections import deque
import numpy as np
import config as config
import time

class Visualizer():
    def __init__(self, board):
        # Name of board this for which this visualizer instance is visualising
        self.board = board
        # Dictionary linking names of effects to their respective functions
        self.effects = {}
        """{"Scroll":self.visualize_scroll,
                        "Energy":self.visualize_energy,
                        "Spectrum":self.visualize_spectrum,
                        "Power":self.visualize_power,
                        "Wavelength":self.visualize_wavelength,
                        "Beat":self.visualize_beat,
                        "Wave":self.visualize_wave,
                        "Bars":self.visualize_bars,
                        #"Pulse":self.visualize_pulse,
                        #"Auto":self.visualize_auto,
                        "Single":self.visualize_single,
                        "Fire":self.visualize_fire,
                        "Fade":self.visualize_fade,
                        "Gradient":self.visualize_gradient,
                        "Calibration": self.visualize_calibration}"""

        from effects.off import Off
        self.effects["Off"] = Off(self)

        from effects.scroll import Scroll
        self.effects["Scroll"] = Scroll(self)

        from effects.energy import Energy
        self.effects["Energy"] = Energy(self)

        from effects.wavelength import Wavelength
        self.effects["Wavelength"] = Wavelength(self)

        from effects.spectrum import Spectrum
        self.effects["Spectrum"] = Spectrum(self)

        from effects.wave import Wave
        self.effects["Wave"] = Wave(self)

        from effects.runner import RunnerReactive
        self.effects["Reactive Runner"] = RunnerReactive(self)

        from effects.auto import Auto
        self.effects["Auto"] = Auto(self)

        from effects.calibration import Calibration
        self.effects["Calibration"] = Calibration(self)

        from effects.multiple import Multiple
        self.effects["Multiple"] = Calibration(self)

        from effects.fade import Fade
        self.effects["Fade"] = Fade(self)

        from effects.gradient import Gradient
        self.effects["Gradient"] = Gradient(self)

        from effects.single import Single
        self.effects["Single"] = Single(self)

        from effects.fire import Fire
        self.effects["Fire"] = Fire(self)

        from effects.gradientrunner import Runner
        self.effects["Runner"] = Runner(self)

        from effects.power import Power
        self.effects["Power"] = Power(self)

        from effects.bars import Bars
        self.effects["Bars"] = Bars(self)

        from effects.sleep import Sleep
        self.effects["Sleep"] = Sleep(self)


        # List of all the visualisation effects that aren't audio reactive.
        # These will still display when no music is playing.
        self.non_reactive_effects = ["Single", "Fire", "Gradient", "Fade", "Runner", "Sleep" "Calibration"]
        # Setup for frequency detection algorithm
        self.freq_channel_history = 40
        self.beat_count = 0
       
        self.freq_channels = [deque(maxlen=self.freq_channel_history) for i in range(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"])]
        self.prev_output = np.array([[0 for i in range(config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"])] for i in range(3)])
        self.output = np.array([[0 for i in range(config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"])] for i in range(3)])
        self.prev_spectrum = np.array([config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"] // 2])
        self.current_freq_detects = {"beat":False,
                                     "low":False,
                                     "mid":False,
                                     "high":False}
        self.prev_freq_detects = {"beat":0,
                                  "low":0,
                                  "mid":0,
                                  "high":0}
        self.detection_ranges = {"beat":(0,int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.11)),
                                 "low":(int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.13),
                                        int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.4)),
                                 "mid":(int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.4),
                                        int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.7)),
                                 "high":(int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]*0.8),
                                         int(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]))}
        self.min_detect_amplitude = {"beat":0.7,
                                     "low":0.5,
                                     "mid":0.3,
                                     "high":0.3}
        self.min_percent_diff = {"beat":70,
                                 "low":100,
                                 "mid":50,
                                 "high":30}
        # Configurations for dynamic ui generation. Effect options can be changed by widgets created at runtime,
        # meaning that you don't need to worry about the user interface - it's all done for you. All you need to
        # do is add items to this dict below.
        #
        # First line of code below explained (as an example):
        #   "Energy" is the visualization we're doing options for
        #   "blur" is the key in the options dict (config.settings["devices"][self.board.board]["effect_opts"]["Energy"]["blur"])
        #   "Blur" is the string we show on the GUI next to the slider
        #   "float_slider" is the GUI element we want to use
        #   (0.1,4.0,0.1) is a tuple containing all the details for setting up the slider (see above)
        #
        # Each effect key points to a list. Each list contains lists giving config for each option.
        # Syntax: effect:[key, label_text, ui_element, opts]
        #   effect     - the effect which you want to change options for. MUST have a key in config.settings["devices"][self.board.board]["effect_opts"]
        #   key        - the key of thing you want to be changed. MUST be in config.settings["devices"][self.board.board]["effect_opts"][effect], otherwise it won't work.
        #   label      - the text displayed on the ui
        #   ui_element - how you want the variable to be changed
        #   opts       - options for the ui element. Must be a tuple.
        # UI Elements + opts:
        #   slider, (min, max, interval)                   (for integer values in a given range)
        #   float_slider, (min, max, interval)             (for floating point values in a given range)
        #   checkbox, ()                                   (for True/False values)
        #   dropdown, (dict or list)                       (dict/list, example see below. Keys will be displayed in the dropdown if dict, otherwise just list items)
        #
        # Hope this clears things up a bit for you! GUI has never been easier..? The reason for doing this is
        # 1 - To make it easy to add options to your effects for the user
        # 2 - To give a consistent GUI for the user. If every options page was set out differently it would all be a mess
        allEffects = {}
        for key in self.effects.keys():
            allEffects[key] = key

        print(allEffects)

        self.dynamic_effects_config = {"Energy":[["blur", "Blur", "float_slider", (0.1,4.0,0.1)],
                                                 ["scale", "Scale", "float_slider", (0.4,1.0,0.05)],
                                                 ["r_multiplier", "Red", "float_slider", (0.05,1.0,0.05)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["g_multiplier", "Green", "float_slider", (0.05,1.0,0.05)],
                                                 ["b_multiplier", "Blue", "float_slider", (0.05,1.0,0.05)]],
                                         "Wave":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["wipe_len", "Wave Start Length", "slider", (0,config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"]//4,1)],
                                                 ["wipe_speed", "Wave Speed", "slider", (1,10,1)],
                                                 ["decay", "Flash Decay", "float_slider", (0.1,1.0,0.05)]],
                                     "Spectrum":[
                                                    ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                    ["blur", "Blur", "float_slider", (0.1,4.0,0.1)]
                                                ],
                                    "Multiple": [
                                                    ["a", "Effect A", "dropdown", allEffects],
                                                    ["b", "Effect B", "dropdown", allEffects],
                                                    ["c", "Effect C", "dropdown", allEffects]
                                                ],
                                        "Auto": [
                                                    ["timer", "Timer", "slider", (100, 20000, 100)]
                                                ],
                                   "Wavelength":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["blur", "Blur", "float_slider", (0.1,4.0,0.1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["reverse_grad", "Reverse Gradient", "checkbox"],
                                                 ["reverse_roll", "Reverse Roll", "checkbox"],
                                                 ["flip_lr", "Flip LR", "checkbox"]],
                                       "Scroll":[["lows_color", "Lows Color", "dropdown", config.settings["colors"]],
                                                 ["mids_color", "Mids Color", "dropdown", config.settings["colors"]],
                                                 ["high_color", "Highs Color", "dropdown", config.settings["colors"]],
                                                 ["blur", "Blur", "float_slider", (0.05,4.0,0.05)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["decay", "Decay", "float_slider", (0.97,1.0,0.0005)],
                                                 ["speed", "Speed", "slider", (1,5,1)]],
                                        "Power":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["s_color", "Spark Color ", "dropdown", config.settings["colors"]],
                                                 ["s_count", "Spark Amount", "slider", (0,config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"]//6,1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["flip_lr", "Flip LR", "checkbox"]],
                                       "Single":[["color", "Color", "dropdown", config.settings["colors"]]],
                                         "Beat":[["color", "Color", "dropdown", config.settings["colors"]],
                                                 ["decay", "Flash Decay", "float_slider", (0.3,0.98,0.005)]],
                                         "Bars":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["resolution", "Resolution", "slider", (1, config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"], 1)],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["flip_lr", "Flip LR", "checkbox"],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["reverse_roll", "Reverse Roll", "checkbox"]],
                                     "Gradient":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["reverse", "Reverse", "checkbox"]],
                                         "Runner":[["times", "times", "slider", (0.05,1,0.05)],
                                                 ["divide", "divide", "slider", (1,15,1)],
                                                 ["add", "add", "slider", (0,2, 0.1)],
                                                 ["blur", "blur", "slider", (0,5,1)],
                                                 ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]]],

                               "RunnerReactive":[["times", "Trail Size", "slider", (0.0,1,0.005)],
                                                 ["divide", "Speed", "slider", (5,50,1)],
                                                 ["add", "add", "slider", (0,1, 0.001)],
                                                 ["blur", "blur", "slider", (0,5,1)],
                                                 ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]]],

                                         "Fade":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Fade Speed", "slider", (0,8,1)],
                                                 ["reverse", "Reverse", "checkbox"]],
                                  "Calibration":[["r", "Red value", "slider", (0,255,1)],
                                                 ["g", "Green value", "slider", (0,255,1)],
                                                 ["b", "Blue value", "slider", (0,255,1)]],
                                        "Sleep":[["hour", "Hour to start fade", "slider", (0,23,1)],
                                                 ["minute", "Minute to start fade", "slider", (0,60,0)],
                                                 ["minutes_fade", "How long to fade for", "slider", (0,60,30)]]
                                       }
        # Setup for fps counter
        self.frame_counter = 0
        self.start_time = time.time()
        # Setup for "Wave" (don't change these)
        self.wave_wipe_count = 0
        # Setup for "Power" (don't change these)
        self.power_indexes = []
        self.power_brightness = 0
        # Setup for multicolour modes (don't mess with this either unless you want to add in your own multicolour modes)
        # If there's a multicolour mode you would like to see, let me know on GitHub! 

        #def _vect_easing_func_gen(slope=2.5, length=1):
        #    return np.vectorize(_easing_func)

        def _easing_func(x, length, slope=2.5):
            # returns a nice eased curve with defined length and curve
            xa = (x/length)**slope
            return xa / (xa + (1 - (x/length))**slope)


        def _easing_gradient_generator(colors, length):
            """
            returns np.array of given length that eases between specified colours

            parameters:
            colors - list, colours must be in config.settings["colors"]
                eg. ["Red", "Orange", "Blue", "Purple"]
            length - int, length of array to return. should be from config.settings
                eg. config.settings["devices"]["my strip"]["configuration"]["N_PIXELS"]
            """
            colors = colors[::-1] # needs to be reversed, makes it easier to deal with
            n_transitions = len(colors) - 1
            ease_length = length // n_transitions
            pad = length - (n_transitions * ease_length)
            output = np.zeros((3, length))
            ease = np.array([_easing_func(i, ease_length, slope=2.5) for i in range(ease_length)])
            # for r,g,b
            for i in range(3):
                # for each transition
                for j in range(n_transitions):
                    # Starting ease value
                    start_value = config.settings["colors"][colors[j]][i]
                    # Ending ease value
                    end_value = config.settings["colors"][colors[j+1]][i]
                    # Difference between start and end
                    diff = end_value - start_value
                    # Make array of all start value
                    base = np.empty(ease_length)
                    base.fill(start_value)
                    # Make array of the difference between start and end
                    diffs = np.empty(ease_length)
                    diffs.fill(diff)
                    # run diffs through easing function to make smooth curve
                    eased_diffs = diffs * ease
                    # add transition to base values to produce curve from start to end value
                    base += eased_diffs
                    # append this to the output array
                    output[i, j*ease_length:(j+1)*ease_length] = base
            # cast to int
            output = np.asarray(output, dtype=int)
            # pad out the ends (bit messy but it works and looks good)
            if pad:
                for i in range(3):
                    output[i, -pad:] = output[i, -pad-1]
            return output

        self.multicolor_modes = {}
        for gradient in config.settings["gradients"]:
            self.multicolor_modes[gradient] = _easing_gradient_generator(config.settings["gradients"][gradient],
                                                                         config.settings["devices"][self.board.board]["configuration"]["N_PIXELS"])

        for i in self.multicolor_modes:
            self.multicolor_modes[i] = np.concatenate((self.multicolor_modes[i][:, ::-1],
                                                       self.multicolor_modes[i]), axis=1)

    def get_vis(self, y, audio_input):
   

        self.update_freq_channels(y)
        self.detect_freqs()
        currentEffect = self.board.config["current_effect"]
        if self.effects[currentEffect].nonReactive:
            self.prev_output = self.effects[self.board.config["current_effect"]].visualize(self.board, y)
        elif audio_input:
            #self.prev_output = self.effects[config.settings["devices"][self.board.board]["configuration"]["current_effect"]](self.effects[config.settings["devices"][self.board.board]["configuration"]["current_effect"]], self.board, y)

            self.prev_output = self.effects[self.board.config["current_effect"]].visualize(self.board, y)
        else:
            self.prev_output = np.multiply(self.prev_output, 0.95)
        
        self.frame_counter += 1
        elapsed = time.time() - self.start_time
        if elapsed >= 1.0:
            self.start_time = time.time()
            fps = self.frame_counter//elapsed
            latency = elapsed/self.frame_counter
            self.frame_counter = 0

            #if config.settings["configuration"]["USE_GUI"]:
            #    gui.label_latency.setText("{:0.3f} ms Processing Latency   ".format(latency))
            #    gui.label_fps.setText('{:.0f} / {:.0f} FPS   '.format(fps, config.settings["configuration"]["FPS"]))

        return self.prev_output

    def _split_equal(self, value, parts):
        value = float(value)
        return [int(round(i*value/parts)) for i in range(1,parts+1)]

    def update_freq_channels(self, y):
        for i in range(len(y)):
            self.freq_channels[i].appendleft(y[i])

    def detect_freqs(self):
        """
        Function that updates current_freq_detects. Any visualisation algorithm can check if
        there is currently a beat, low, mid, or high by querying the self.current_freq_detects dict.
        """
        channel_avgs = []
        differences = []
        for i in range(config.settings["devices"][self.board.board]["configuration"]["N_FFT_BINS"]):
            channel_avgs.append(sum(self.freq_channels[i])/len(self.freq_channels[i]))
            differences.append(((self.freq_channels[i][0]-channel_avgs[i])*100)//channel_avgs[i])
        for i in ["beat", "low", "mid", "high"]:
            if any(differences[j] >= self.min_percent_diff[i]\
                   and self.freq_channels[j][0] >= self.min_detect_amplitude[i]\
                            for j in range(*self.detection_ranges[i]))\
                        and (time.time() - self.prev_freq_detects[i] > 0.2)\
                        and len(self.freq_channels[0]) == self.freq_channel_history:
                self.prev_freq_detects[i] = time.time()
                self.current_freq_detects[i] = True
                #print(i)
            else:
                self.current_freq_detects[i] = False    


    

