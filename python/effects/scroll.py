import numpy as np
import util

from effects.effect import Effect


class Scroll(Effect):
    """Colour flows out from the start of the strip, with the bass, mids and treble
    taking the start, middle and end colours of the palette

    Hits push a bright pulse into the flow. On a pre-analysed track they follow
    the song's repeating rhythm, each pulse coloured by its step in the bar, so
    the pattern repeats as the same run of colours bar after bar.
    """
    def __init__(self, visualizer):
        self.output = np.zeros((3, visualizer.board.config["N_PIXELS"]))
        self.pulse = 0.0
        self.pulse_colour = np.zeros(3)

    def visualize(self, board, y):
        options = board.effectConfig["Scroll"]
        features = board.features
        n = board.config["N_PIXELS"]
        gradient = board.visualizer.gradient(options["color_mode"])
        colours = gradient[:, [0, n // 2, n - 1]].T.astype(float)  # bass, mids, treble
        # Squared so a band only shows when it is actually pushing, not idling mid-range
        bands = np.array([features.bass, features.mid, features.treble]) ** 2
        new = bands @ colours * self.dynamics(features)

        if features.groove_hit:
            self.pulse = 1.0
            self.pulse_colour = gradient[:, int(max(features.bar_step, 0) / 16 * (n - 1))].astype(float)
        elif features.kick_hit and not features.groove_strength:
            # Live: no pattern known, so push a gentler pulse on kicks
            self.pulse = 0.6
            self.pulse_colour = colours[0]
        new = np.minimum(new + self.pulse_colour * self.pulse, 255)
        self.pulse *= self.fade(0.06)

        speed = options["speed"]
        self.output[:, speed:] = self.output[:, :-speed] * self.fade(options["trail"])
        self.output[:, :speed] = new[:, np.newaxis]
        output = util.blur(self.output, options["blur"])
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
