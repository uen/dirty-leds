import numpy as np

from effects.effect import Effect

class Wave(Effect):
    def __init__(self, visualizer):
        self.effectName = "Wave"
        self.wave_wipe_count = 0

    def visualize(self, board, y):
        outputGradient = np.array(
            [
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][0][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][1][:board.config["N_PIXELS"]],
                board.visualizer.multicolor_modes[board.effectConfig["Wave"]["color_mode"]][2][:board.config["N_PIXELS"]],
            ]
        )
        if board.visualizer.current_freq_detects["beat"]:
            output = np.zeros((3,board.config["N_PIXELS"]))
            output[0][:] = np.divide(outputGradient[2], 2)
            output[1][:] = np.divide(outputGradient[1], 2)
            output[2][:] = np.divide(outputGradient[0], 2)

            self.wave_wipe_count = board.effectConfig["Wave"]["wipe_len"]
        else:
            output = np.multiply(board.visualizer.prev_output,board.effectConfig["Wave"]["decay"])
            self._wipe(output, outputGradient, self.wave_wipe_count)
            
            if self.wave_wipe_count > board.config["N_PIXELS"]//2:
                self.wave_wipe_count = board.config["N_PIXELS"]//2
            self.wave_wipe_count += board.effectConfig["Wave"]["wipe_speed"]
 
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



