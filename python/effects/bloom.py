import numpy as np

from effects.effect import Effect


class Bloom(Effect):
    """Kicks bloom out from the centre, snares close in from the edges, each in
    its own palette colour: the strip plays the drum pattern back"""
    def __init__(self, visualizer):
        self.effectName = "Bloom"
        n = visualizer.board.config["N_PIXELS"]
        self.kick_age = 1e9
        self.snare_age = 1e9
        self.output = np.zeros((3, n))

    def visualize(self, board, y):
        options = board.effectConfig["Bloom"]
        features = board.features
        n = board.config["N_PIXELS"]
        dt = 1.0 / 60
        kick = features.groove_hit if features.groove_strength else features.kick_hit
        self.kick_age = 0.0 if kick else self.kick_age + dt
        self.snare_age = 0.0 if features.snare_hit else self.snare_age + dt
        gradient = board.visualizer.gradient(options["color_mode"])
        kick_colour = gradient[:, 0].astype(float)
        snare_colour = gradient[:, int(0.7 * (n - 1))].astype(float)
        distance = np.abs(2 * np.arange(n) / max(n - 1, 1) - 1)  # 0 at the centre, 1 at the ends
        decay = options["decay"]
        # Bloom: grows out to `size` of the strip, fading as it goes
        radius = options["size"] * min(1.0, self.kick_age / 0.12)
        kick = np.clip((radius - distance) * 8, 0, 1) * np.exp(-self.kick_age / decay)
        # Snare: a band closing in from the ends
        edge = 1.0 - 0.5 * min(1.0, self.snare_age / 0.15)
        snare = np.exp(-((distance - edge) / 0.08) ** 2) * np.exp(-self.snare_age / (decay * 0.7))
        output = np.maximum(kick_colour[:, np.newaxis] * kick, snare_colour[:, np.newaxis] * snare)
        self.output = np.maximum(output, self.output * self.fade(0.05))
        return self.output * self.dynamics(features, floor=0.4)
