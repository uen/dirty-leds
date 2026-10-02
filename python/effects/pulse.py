import numpy as np
import util

from effects.effect import Effect


class Pulse(Effect):
    """The strip flashes out from the centre on every beat and shrinks back over it,
    stepping through the palette one colour per beat"""
    def __init__(self, visualizer):
        self.effectName = "Pulse"
        self.beats = 0

    def visualize(self, board, y):
        options = board.effectConfig["Pulse"]
        features = board.features
        n = board.config["N_PIXELS"]
        self.beats += features.beat
        gradient = board.visualizer.gradient(options["color_mode"])
        colour = gradient[:, int((self.beats % options["colours"]) / options["colours"] * n)]

        # 1 right on the beat, easing to 0 by the next one
        flash = (1.0 - features.beat_phase) ** options["sharpness"]
        level = (0.15 + 0.85 * flash) * (0.7 + 0.3 * features.kick) * self.dynamics(features)
        half_width = n / 2 * (0.2 + 0.8 * flash * (0.4 + 0.6 * features.intensity))
        distance = np.abs(np.arange(n) - (n - 1) / 2)
        lit = np.clip(half_width - distance, 0, 1)
        return util.blur(colour[:, np.newaxis] * lit * level, 2)
