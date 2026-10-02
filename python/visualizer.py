import numpy as np
import config

class Visualizer():
    def __init__(self, board):
        # Name of board this for which this visualizer instance is visualising
        self.board = board
        # Dictionary linking names of effects to their respective functions
        self.effects = {}

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

        from effects.fade import Fade
        self.effects["Fade"] = Fade(self)

        from effects.gradient import Gradient
        self.effects["Gradient"] = Gradient(self)

        from effects.mood import Mood
        self.effects["Mood"] = Mood(self)

        from effects.stars import Stars
        self.effects["Stars"] = Stars(self)

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

        from effects.pulse import Pulse
        self.effects["Pulse"] = Pulse(self)

        from effects.ripple import Ripple
        self.effects["Ripple"] = Ripple(self)

        from effects.sparkle import Sparkle
        self.effects["Sparkle"] = Sparkle(self)

        from effects.sleep import Sleep
        self.effects["Sleep"] = Sleep(self)


        self.prev_output = np.array([[0 for i in range(self.board.config["N_PIXELS"])] for i in range(3)])
        # Configurations for dynamic ui generation. Effect options can be changed by widgets created at runtime,
        # meaning that you don't need to worry about the user interface - it's all done for you. All you need to
        # do is add items to this dict below.
        #
        # First line of code below explained (as an example):
        #   "Energy" is the visualization we're doing options for
        #   "blur" is the key in the options dict (self.board.effectConfig["Energy"]["blur"])
        #   "Blur" is the string we show on the GUI next to the slider
        #   "float_slider" is the GUI element we want to use
        #   (0.1,4.0,0.1) is a tuple containing all the details for setting up the slider (see above)
        #
        # Each effect key points to a list. Each list contains lists giving config for each option.
        # Syntax: effect:[key, label_text, ui_element, opts]
        #   effect     - the effect which you want to change options for. MUST have a key in self.board.effectConfig
        #   key        - the key of thing you want to be changed. MUST be in self.board.effectConfig[effect], otherwise it won't work.
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

        self.dynamic_effects_config = {"Energy":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["blur", "Blur", "float_slider", (0.1,4.0,0.1)],
                                                 ["scale", "Scale", "float_slider", (0.4,1.0,0.05)],
                                                 ["r_multiplier", "Bass reach", "float_slider", (0.05,1.0,0.05)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["g_multiplier", "Mids reach", "float_slider", (0.05,1.0,0.05)],
                                                 ["b_multiplier", "Treble reach", "float_slider", (0.05,1.0,0.05)]],
                                         "Wave":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["wipe_len", "Wave Start Length", "slider", (0,self.board.config["N_PIXELS"]//4,1)],
                                                 ["wipe_speed", "Wave Speed", "slider", (1,10,1)],
                                                 ["fade", "Flash Fade (s)", "float_slider", (0.05,1.5,0.05)]],
                                     "Spectrum":[
                                                    ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                    ["blur", "Blur", "float_slider", (0.1,4.0,0.1)]
                                                ],
                                        "Pulse": [["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                  ["colours", "Colours to step through", "slider", (1, 16, 1)],
                                                  ["sharpness", "Flash sharpness", "float_slider", (0.5, 4.0, 0.1)]],
                                       "Ripple": [["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                  ["width", "Ripple width", "float_slider", (1.0, 20.0, 0.5)],
                                                  ["beats", "Beats to cross", "float_slider", (0.25, 4.0, 0.25)],
                                                  ["on_beat", "Ripple on every beat", "checkbox"]],
                                      "Sparkle": [["color_mode", "Background", "dropdown", config.settings["gradients"]],
                                                  ["spark_color", "Spark colour", "dropdown", config.settings["colors"]],
                                                  ["density", "Density", "float_slider", (0.01, 0.3, 0.01)],
                                                  ["fade", "Fade (s)", "float_slider", (0.05, 1.0, 0.05)]],
                                        "Auto": [
                                                    ["bars", "Bars per effect", "slider", (1, 32, 1)]
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
                                                 ["blur", "Blur", "float_slider", (0,3,0.1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["trail", "Trail (s)", "float_slider", (0.1,4.0,0.1)],
                                                 ["speed", "Speed", "slider", (1,5,1)]],
                                        "Power":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["s_color", "Spark Color ", "dropdown", config.settings["colors"]],
                                                 ["s_count", "Spark Amount", "slider", (0,self.board.config["N_PIXELS"]//6,1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["flip_lr", "Flip LR", "checkbox"]],
                                       "Single":[["color", "Color", "dropdown", config.settings["colors"]]],
                                         "Bars":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["resolution", "Resolution", "slider", (1, self.board.config["N_FFT_BINS"], 1)],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["flip_lr", "Flip LR", "checkbox"],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["reverse_roll", "Reverse Roll", "checkbox"]],
                                        "Stars":[["star_rate", "Star amount", "float_slider", (0.01, 1.0, 0.01)],
                                                 ["star_decay", "Star Decay", "float_slider", (1.0, 10.0, 0.1)],
                                                 ["star_speed", "Star Speed", "float_slider", (0.0001, 0.001, 0.0001)]],
                                      "Mood":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["fast", "Fast", "checkbox"],
                                                 ["reverse", "Reverse", "checkbox"]],

                                     "Gradient":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Roll Speed", "slider", (0,8,1)],
                                                 ["mirror", "Mirror", "checkbox"],
                                                 ["fast", "Fast", "checkbox"],
                                                 ["reverse", "Reverse", "checkbox"]],
                                         "Runner":[["times", "times", "float_slider", (0.05,1,0.05)],
                                                 ["divide", "divide", "float_slider", (1,15,0.1)],
                                                 ["add", "add", "float_slider", (0,2, 0.1)],
                                                 ["blur", "blur", "slider", (0,5,1)],
                                                 ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]]],

                               "RunnerReactive":[["times", "Trail Size", "float_slider", (0.0,1,0.005)],
                                                 ["divide", "Speed", "slider", (5,50,1)],
                                                 ["add", "add", "float_slider", (0,1, 0.001)],
                                                 ["blur", "blur", "slider", (0,5,1)],
                                                 ["color_mode", "Color Mode", "dropdown", config.settings["gradients"]]],

                                         "Fade":[["color_mode", "Color Mode", "dropdown", config.settings["gradients"]],
                                                 ["roll_speed", "Fade Speed", "slider", (0,8,1)],
                                                 ["reverse", "Reverse", "checkbox"]],
                                  "Calibration":[["r", "Red value", "slider", (0,255,1)],
                                                 ["g", "Green value", "slider", (0,255,1)],
                                                 ["b", "Blue value", "slider", (0,255,1)]],
                                        "Sleep":[["hour", "Hour to start fade", "slider", (0,23,1)],
                                                 ["minute", "Minute to start fade", "slider", (0,59,1)],
                                                 ["minutes_fade", "How long to fade for", "slider", (0,60,1)]]
                                       }
        # Setup for multicolour modes (don't mess with this either unless you want to add in your own multicolour modes)
        # If there's a multicolour mode you would like to see, let me know on GitHub! 

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
                                                                         self.board.config["N_PIXELS"])

        for i in self.multicolor_modes:
            self.multicolor_modes[i] = np.concatenate((self.multicolor_modes[i][:, ::-1],
                                                       self.multicolor_modes[i]), axis=1)

    def gradient(self, name, offset=0):
        """Colour gradient `name` as a (3, 2 * N_PIXELS) array, rotated by `offset` pixels

        The tables are shared by every effect, so effects keep their own offset
        rather than rolling the tables in place.
        """
        return np.roll(self.multicolor_modes[name], offset, axis=1)

    @property
    def current_freq_detects(self):
        """Beat / low / mid / high hit flags for this frame, from the music features"""
        features = self.board.features
        return {"beat": features.beat, "low": features.kick_hit, "mid": features.snare_hit, "high": features.hat_hit}

    def get_vis(self, y, audio_input):
        effect = self.effects[self.board.config["current_effect"]]
        if effect.nonReactive or audio_input:
            self.prev_output = effect.visualize(self.board, y)
        else:
            # No music: let the last frame fade out
            self.prev_output = np.multiply(self.prev_output, 0.95)
        return self.prev_output
