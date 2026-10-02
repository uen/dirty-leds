import numpy as np

from effects.effect import Effect


class Stack(Effect):
    """The bar counts itself: each beat lights the next segment of the strip in the
    next colour, and the whole stack clears on the first beat of the next bar"""
    def __init__(self, visualizer):
        self.effectName = "Stack"
        n = visualizer.board.config["N_PIXELS"]
        self.output = np.zeros((3, n))
        self.beats = 0
        self.flash = 0.0

    def visualize(self, board, y):
        options = board.effectConfig["Stack"]
        features = board.features
        n = board.config["N_PIXELS"]
        segments = options["segments"]
        if features.beat:
            # With the song's bar grid known, count from its first beat; otherwise count beats
            beat_in_bar = features.bar_step // 4 if features.bar_step >= 0 else self.beats % 4
            self.beats += 1
            step = beat_in_bar * segments // 4
            if step == 0:
                self.output[:] = 0
            gradient = board.visualizer.gradient(options["color_mode"])
            colour = gradient[:, int(step / segments * (n - 1))].astype(float)
            bounds = np.linspace(0, n, segments + 1).astype(int)
            for k in range(step, step + max(1, segments // 4)):
                if k < segments:
                    self.output[:, bounds[k]:bounds[k + 1]] = colour[:, np.newaxis]
            self.flash = 1.0
        self.flash *= self.fade(0.12)
        # The newest segment lands bright, the stack sits a little lower
        output = self.output * (0.65 + 0.35 * self.flash)
        if options["mirror"]:
            output = np.concatenate((output[:, ::-2], output[:, ::2]), axis=1)
        return output * self.dynamics(features, floor=0.4)
