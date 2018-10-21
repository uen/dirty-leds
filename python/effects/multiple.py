from scipy.ndimage.filters import gaussian_filter1d
import numpy as np
import config  as config
import util
from effects.effect import Effect


class Multiple(Effect):
    autoTimer = 0
    autoEffect = 0
    effectKeys = []

    nonReactive = True

    def __init__(self, visualizer):
        self.effectName = "Multiple"
        self.effectKeys = list(visualizer.effects.keys())

    def visualize(self, board, y):
        output = np.zeros((3,board.config["N_PIXELS"]))
    
        aKey = config.settings["devices"][board.board]["effect_opts"]["Multiple"]["a"]
        bKey = config.settings["devices"][board.board]["effect_opts"]["Multiple"]["b"]
        cKey = config.settings["devices"][board.board]["effect_opts"]["Multiple"]["c"]


        aKey = aKey == "Multiple" and "" or aKey
        bKey = bKey == "Multiple" and "" or bKey
        cKey = cKey == "Multiple" and "" or cKey
        effectsUsed = 0


        if(aKey in board.visualizer.effects):
            effectsUsed+=1
            output = output + board.visualizer.effects[aKey].visualize(board, y)

        if(bKey in board.visualizer.effects):
            effectsUsed+=1
            vis = np.array(board.visualizer.effects[bKey].visualize(board, y))

            avg = vis[0] + vis[1] + vis[2]
            avg = avg / 3.0

            res = np.zeros((3,board.config["N_PIXELS"]))
            res[0] = avg
            res[1] = avg
            res[2] = avg

#            avg = vis.max(axis=1)
#            avg = np.divide(avg, 3)
       

#            avg = np.divide(avg, 3)


            ## need to find avertage of red,green,blue value

# take average of all 3 mask colors
# times that value by all of the values in the color (brighness)
            

            output[0] = np.multiply(output[0], res[0]/255)
            output[1] = np.multiply(output[1], res[1]/255)
            output[2] = np.multiply(output[2], res[2]/255)

        #if(cKey in board.visualizer.effects):
        #    effectsUsed+=1
        
        #    output = output + board.visualizer.effects[aKey].visualize(board, y)



        return output