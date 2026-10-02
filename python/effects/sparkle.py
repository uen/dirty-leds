import numpy as np
import config

from effects.effect import Effect


class Sparkle(Effect):
    """Hi-hats and snares scatter sparkles over a background that breathes with the bass"""
    def __init__(self, visualizer):
        self.effectName = "Sparkle"
        n = visualizer.board.config["N_PIXELS"]
        self.sparks = np.zeros(n)
        self.rng = np.random.default_rng()

    def visualize(self, board, y):
        options = board.effectConfig["Sparkle"]
        features = board.features
        n = board.config["N_PIXELS"]
        dynamics = self.dynamics(features)
        background = board.visualizer.gradient(options["color_mode"])[:, :n] * (0.04 + 0.3 * features.bass ** 2) * dynamics

        if features.hat_hit or features.snare_hit:
            count = max(1, int(n * options["density"] * (0.3 + 0.7 * features.intensity)))
            self.sparks[self.rng.choice(n, size=min(count, n), replace=False)] = 1.0
        self.sparks *= self.fade(options["fade"])

        spark_colour = np.array(config.settings["colors"][options["spark_color"]], dtype=float)
        output = background + spark_colour[:, np.newaxis] * self.sparks * (0.4 + 0.6 * dynamics)
        return np.minimum(output, 255)
