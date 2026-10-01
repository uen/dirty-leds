import numpy as np
import config
import random
import util

from effects.effect import Effect


class Power(Effect):
    """Spectrum glow with a bass bar at the start and sparks on hi-hats and cymbals"""
    def __init__(self, visualizer):
        self.effectName = "Power"
        self.power_brightness = 0
        self.power_indexes = []

    def visualize(self, board, y):
        options = board.effectConfig["Power"]
        features = board.features
        n = board.config["N_PIXELS"]
        gradient = board.visualizer.gradient(options["color_mode"])[:, :n]
        levels = np.repeat(util.interpolate(features.bins, n // 2), 2) ** 2
        output = gradient * levels * self.dynamics(features)

        if features.hat_hit:
            self.power_brightness = 1.0
            self.power_indexes = random.sample(range(n), min(n, options["s_count"]))
        if self.power_indexes:
            spark = np.array(config.settings["colors"][options["s_color"]]) * self.power_brightness
            output[:, self.power_indexes] = spark[:, np.newaxis]
        # Remove a quarter of the sparks for next time and fade the rest
        self.power_indexes = random.sample(self.power_indexes, len(self.power_indexes) - len(self.power_indexes) // 4)
        self.power_brightness = max(0.0, self.power_brightness - 0.05)

        # Bass bar from the start of the strip, coloured by how far it reaches
        bar = int(n // 3 * features.bass * self.dynamics(features))
        output[:, :bar] = gradient[:, bar:bar + 1]
        if options["flip_lr"]:
            output = np.fliplr(output)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output
