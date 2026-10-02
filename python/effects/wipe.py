import numpy as np

from effects.effect import Effect


class Wipe(Effect):
    """On every beat the next palette colour sweeps across the strip, covering the
    last one, so each beat lands as a visible change of colour"""
    def __init__(self, visualizer):
        self.effectName = "Wipe"
        n = visualizer.board.config["N_PIXELS"]
        self.beats = 0
        self.since_beat = 1e9
        self.previous = np.zeros((3, n))
        self.current = np.zeros((3, n))

    def visualize(self, board, y):
        options = board.effectConfig["Wipe"]
        features = board.features
        n = board.config["N_PIXELS"]
        dt = 1.0 / 60
        if features.beat:
            self.beats += 1
            self.since_beat = 0.0
            self.previous = self.current
            colour = board.visualizer.gradient(options["color_mode"])[:, int((self.beats % options["colours"]) / options["colours"] * (n - 1))]
            self.current = np.tile(colour[:, np.newaxis].astype(float), (1, n))
        else:
            self.since_beat += dt

        beat = 60.0 / max(features.tempo, 60)
        front = min(1.0, self.since_beat / max(options["speed"] * beat, 1e-3))
        index = np.arange(n) / max(n - 1, 1)
        if options["direction"] == "centre":
            distance = np.abs(2 * index - 1)
        elif options["direction"] == "right":
            distance = 1.0 - index
        else:
            distance = index
        # Pixels the front has passed show the new colour, with a soft edge
        covered = np.clip((front - distance) * 12 + 0.5, 0, 1)
        output = 0.85 * self.current * covered + 0.3 * self.previous * (1 - covered)
        return output * self.dynamics(features, floor=0.4)
