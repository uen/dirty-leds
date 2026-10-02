import numpy as np
import config

from effects.effect import Effect

MAX_RIPPLES = 12


class Ripple(Effect):
    """Every kick sends a ripple from the centre to the ends, crossing in time with the tempo"""
    def __init__(self, visualizer):
        self.effectName = "Ripple"
        # Each ripple: [distance travelled 0-1, strength, colour]
        self.ripples = []

    def visualize(self, board, y):
        options = board.effectConfig["Ripple"]
        features = board.features
        n = board.config["N_PIXELS"]
        half = n - n // 2
        if features.kick_hit or (options["on_beat"] and features.beat):
            # Bright sounds pick colours from further along the gradient
            gradient = board.visualizer.gradient(options["color_mode"])
            colour = gradient[:, int(features.brightness * (n - 1))]
            self.ripples.append([0.0, self.dynamics(features), colour])
            self.ripples = self.ripples[-MAX_RIPPLES:]

        positions = np.arange(half)
        output = np.zeros((3, half))
        for ripple in self.ripples:
            travelled, strength, colour = ripple
            front = travelled * half
            # A bright front with a glowing tail behind it, fading as it travels
            behind = positions <= front
            shape = np.where(behind,
                             np.exp(-(front - positions) / (3 * options["width"])),
                             np.exp(-((positions - front) / options["width"]) ** 2))
            shape *= strength * np.sqrt(1 - travelled)
            output += colour[:, np.newaxis] * shape
        # options["beats"] beats to reach the end of the strip
        step = features.tempo / 60 / config.settings["configuration"]["FPS"] / options["beats"]
        for ripple in self.ripples:
            ripple[0] += step
        self.ripples = [r for r in self.ripples if r[0] < 1]
        output = np.minimum(output, 255)
        return np.concatenate((output[:, ::-1], output), axis=1)[:, :n]
