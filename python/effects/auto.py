import numpy as np
import config

from effects.effect import Effect


class Auto(Effect):
    """The auto show: renders whatever the director picked for this strip,
    crossfading when the look changes"""
    def __init__(self, visualizer):
        self.effectName = "Auto"
        self.current = None
        self.previous = None
        self.blend_frames = 0
        self.blend_left = 0

    def visualize(self, board, y):
        assignment = board.show.assignment(board)
        if assignment is not self.current:
            self.previous, self.current = self.current, assignment
            self.blend_frames = int(assignment.transition * config.settings["configuration"]["FPS"])
            self.blend_left = self.blend_frames if self.previous else 0

        output = self._render(board, self.current, y)
        if self.blend_left > 0:
            mix = 1 - self.blend_left / self.blend_frames
            output = self._render(board, self.previous, y) * (1 - mix) + output * mix
            self.blend_left -= 1
        return output * board.show.level

    @staticmethod
    def _render(board, assignment, y):
        """Render an effect with the director's options in place of the strip's own"""
        effect = board.visualizer.effects[assignment.effect]
        own = board.effectConfig
        board.effectConfig = {**own, assignment.config_key: assignment.options}
        try:
            return np.asarray(effect.visualize(board, y), dtype=float)
        finally:
            board.effectConfig = own
