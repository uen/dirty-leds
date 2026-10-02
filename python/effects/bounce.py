import math

import numpy as np

from effects.effect import Effect


class Bounce(Effect):
    """A bright block bouncing end to end, touching an end exactly on every beat,
    leaving a fading trail; it takes the next palette colour every bar"""
    def __init__(self, visualizer):
        self.effectName = "Bounce"
        n = visualizer.board.config["N_PIXELS"]
        self.trail = np.zeros((3, n))
        self.beats = 0

    def visualize(self, board, y):
        options = board.effectConfig["Bounce"]
        features = board.features
        n = board.config["N_PIXELS"]
        self.beats += features.beat
        # One end to the other per beat: position is a triangle wave of beats
        progress = (self.beats + features.beat_phase) % 2.0
        position = progress if progress <= 1.0 else 2.0 - progress
        # Ease into the ends so it reads as bouncing off them
        position = 0.5 - 0.5 * math.cos(math.pi * position)
        bar = self.beats // 4
        colour = board.visualizer.gradient(options["color_mode"])[:, int((bar % 4) / 4 * (n - 1))].astype(float)
        size = max(2.0, options["size"] * n)
        centre = position * (n - 1)
        block = np.clip(1.0 - np.abs(np.arange(n) - centre) / size, 0, 1) ** 0.5
        self.trail = np.maximum(self.trail * self.fade(options["trail"]), colour[:, np.newaxis] * block)
        return self.trail * self.dynamics(features, floor=0.4)
