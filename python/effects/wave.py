import numpy as np

from effects.effect import Effect


class Wave(Effect):
    """Flashes the strip on every beat, then a gradient wipes in from both ends"""
    def __init__(self, visualizer):
        self.effectName = "Wave"
        self.wave_wipe_count = 0

    def visualize(self, board, y):
        options = board.effectConfig["Wave"]
        features = board.features
        n = board.config["N_PIXELS"]
        gradient = board.visualizer.gradient(options["color_mode"])[:, :n]
        if features.beat:
            # Flash in the gradient's colours swapped, so it stands out from the wipe
            output = gradient[::-1] / 2 * self.dynamics(features, floor=0.5)
            self.wave_wipe_count = options["wipe_len"]
        else:
            output = board.visualizer.prev_output * self.fade(options["fade"])
            self._wipe(output, gradient * self.dynamics(features, floor=0.5), self.wave_wipe_count)
            self.wave_wipe_count = min(self.wave_wipe_count, n // 2) + options["wipe_speed"]
        return output

    @staticmethod
    def _wipe(output, gradient, count):
        """Paint gradient pixels 0..count-1 in from both ends of the strip

        Pixel i goes to position i and to position -i. Where the two ends
        overlap, the pixel with the larger i is the one that shows.
        """
        n = output.shape[1]
        position = np.arange(n)
        from_left = np.where(position < count, position, -1)
        from_right = np.where((position > 0) & (n - position < count), n - position, -1)
        source = np.maximum(from_left, from_right)
        painted = source >= 0
        output[:, painted] = gradient[:, source[painted]]
