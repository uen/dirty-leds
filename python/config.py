"""Default settings and configuration for audio reactive LED strip"""
from __future__ import print_function
from __future__ import division
import copy
import json
import os

effectOptions = {"Energy":    {"blur": 1,                       # Amount of blur to apply
                                                   "scale":0.9,                     # Width of effect on strip
                                                   "r_multiplier": 1.0,             # How much red
                                                   "mirror": True,                  # Reflect output down centre of strip
                                                   "g_multiplier": 1.0,             # How much green
                                                   "b_multiplier": 1.0},            # How much blue
                                     "Wave":      {"color_wave": "Red",             # Colour of moving bit
                                                   "color_flash": "White",          # Colour of flashy bit
                                                   "wipe_len":7,                    # Initial length before beat
                                                   "color_mode": "Spectral",        # Color of gradient
                                                   "decay": 0.9,                    # How quickly the flash fades away 
                                                   "wipe_speed":1},                 # Number of pixels added to colour bit every frame
                                    
                                       "Spectrum":{"blur": 1.0, "color_mode":"Spectral"},
                                
                                       
                                     "Wavelength":{"roll_speed": 0,                 # How fast (if at all) to cycle colour overlay across strip
                                                   "color_mode": "Spectral",        # Colour gradient to display
                                                   "mirror": False,                 # Reflect output down centre of strip
                                                   "reverse_grad": False,           # Flip (LR) gradient
                                                   "reverse_roll": False,           # Reverse movement of gradient roll
                                                   "blur": 1.0,                     # Amount of blur to apply
                                                   "flip_lr":False},                # Flip output left-right
                                     "Scroll":    {"lows_color": "Red",             # Colour of low frequencies
                                                   "mids_color": "Green",           # Colour of mid frequencies
                                                   "high_color": "Blue",            # Colour of high frequencies
                                                   "decay": 0.995,                  # How quickly the colour fades away as it moves
                                                   "speed": 1,                      # Speed of scroll
                                                   "mirror": True,                  # Reflect output down centre of strip
                                                   "r_multiplier": 1.0,             # How much red
                                                   "g_multiplier": 1.0,             # How much green
                                                   "b_multiplier": 1.0,             # How much blue
                                                   "blur": 0.2},                    # Amount of blur to apply
                                     "Power":     {"color_mode": "Spectral",        # Colour gradient to display
                                                   "s_count": 20,                   # Initial number of sparks
                                                   "s_color": "White",              # Color of sparks
                                                   "mirror": True,                  # Mirror output down central axis
                                                   "flip_lr":False},                # Flip output left-right
                                     "Single":    {"color": "Purple"},              # Static color to show
                                     "Auto":      {"timer": 500},
                                     "Bars":      {"resolution":4,                  # Number of "bars"
                                                   "color_mode":"Spectral",         # Multicolour mode to use
                                                   "roll_speed":0,                  # How fast (if at all) to cycle colour colours across strip
                                                   "mirror": False,                 # Mirror down centre of strip
                                                   "reverse_roll": False,           # Reverse movement of gradient roll
                                                   "flip_lr":False},                # Flip output left-right
                                        "Stars":   {"star_rate" : 0.29,
                                                    "star_decay" : 9,
                                                    "star_speed" : 0.0006},
                                      "Mood":  {"color_mode":"Spectral",         # Colour gradient to display
                                                   "roll_speed": 1,
                                                   "delay" : 0.1,                 # Seconds between steps of the colour roll
                                                   "fast": False,                   # Fast/Slow
                                                   "mirror": False,                 # Mirror gradient down central axis
                                                   "reverse": False},               # Reverse movement of gradient

                                     "Gradient":  {"color_mode":"Spectral",         # Colour gradient to display
                                                   "roll_speed": 0,
                                                   "fast": False,                   # Fast/Slow
                                                   "mirror": False,                 # Mirror gradient down central axis
                                                   "reverse": False},               # Reverse movement of gradient
                                     "Fade":      {"color_mode":"Spectral",         # Colour gradient to fade through
                                                   "roll_speed": 1,                 # How fast (if at all) to fade through colours
                                                   "reverse": False},               # Reverse "direction" of fade (r->g->b or r<-g<-b)
                                     "Calibration":{"r": 100,
                                                    "g": 100,
                                                    "b": 100},
                                     
                                      "Sleep": {"hour":6, "minute":9, "minutes_fade": 30},
                                      "Fire": {"delay":0.04},                                    # Seconds between flickers
                                      "Runner": {"color_mode":"Spectral", "times":0.15, "add":0.1, "divide":4.7,"blur":0},
                                      "RunnerReactive": {"color_mode":"Fruity", "times":0.90, "add":0.8, "divide":18,"blur":1}
                                     }

devices = {}
# DIRTY_LEDS_CONFIG picks another device list, e.g. a room preset in rooms/
with open(os.environ.get("DIRTY_LEDS_CONFIG", "config.json")) as configFile:
  data = json.load(configFile)
  for device in data["devices"]:
    devices[device["name"]] = {
        "configuration": {
          "TYPE": device["type"],
          "UDP_IP": device["ip"],
          "UDP_PORT": device["port"],
          "maxBrightness": 255, 
          "N_PIXELS": device["leds"],
          "N_FFT_BINS": 24,
          "MIN_FREQUENCY": 20,
          "MAX_FREQUENCY": 18000,
          "current_effect": "Scroll"
        },
        "effect_opts": copy.deepcopy(effectOptions),
        # Optional 3D path of the strip, [[x, y, z], ...] in metres, for the room view
        "layout": device.get("path"),
    }
    print("Loaded device: ", device["name"])


settings = {                                                      # All settings are stored in this dict
    "sync" : True,
    "brightness" : 0.8,
    "currentProfile": "",
    "server": {"host": "127.0.0.1", "port": 8000, **data.get("server", {})},  # Web interface
    "room": data.get("room"),                     # Optional room box and furniture for the room view
    "pipes": data.get("pipes", []),               # Optional named PCM FIFOs offered as audio sources

    "configuration":{
      'displayFPS': False,
      'MIC_RATE': 48000, 
      'FPS': 60,                                   # Desired refresh rate of the visualization (frames per second)
      'maxBrightness': 255,                        # Max brightness sent to LED strip
      'N_ROLLING_HISTORY': 1,                      # Number of past audio frames to include in the rolling window
      'MIN_VOLUME_THRESHOLD': 0.001,               # No music visualization displayed if recorded audio volume below threshold
    },

    "devices":devices,
    "colors":{
                "Red":(255,0,0),
                "Orange":(255,40,0),
                "Yellow":(255,255,0),
                "Green":(0,255,0),
                "Blue":(0,0,255),
                "Light blue":(1,247,161),
                "Purple":(80,5,252),
                "Bright pink":(255,0,178),


                "White":(255,255,255),

                "Bright red": (204, 40, 64),
                "Pink": (255, 126, 157),
                "Dark pink": (121, 36, 83),
                "Dark purple": (51, 0, 39),

                "Darker green": (7, 38, 2),
                "Dark green": (28, 64, 2),
                "Medium green": (70, 115, 2),
                "Light green": (114, 166, 3),

                "Romantic red": (191, 21, 24),
                "Romantic dark red": (115, 13, 14),
                "Romantic brown": (191, 127, 98),
                "Romantic orange": (115, 76, 59),
                "Romantic pink": (191, 115, 115),

                "Rasta red": (242, 65, 80),
                "Rasta green": (75, 242, 86),
                "Rasta yellow": (242, 211, 56),
                "Rasta dark red": (140, 54, 54),


},

    # Multicolour gradients. Colours must be in list above
    "gradients":{"Spectral"  : ["Red", "Orange", "Yellow", "Green", "Light blue", "Blue", "Purple", "Bright pink"],
                 "Dancefloor": ["Red", "Bright pink", "Purple", "Blue"],
                 "Sunset"    : ["Red", "Orange", "Yellow"],
                 "Ocean"     : ["Green", "Light blue", "Blue"],
                 "Jungle"    : ["Green", "Red", "Orange"],
                 "Sunny"     : ["Yellow", "Light blue", "Orange", "Blue"],
                 "Fruity"    : ["Orange", "Blue"],
                 "Peach"     : ["Orange", "Bright pink"],
                 "Rust"      : ["Orange", "Red"],


                 "Marijuana" : ["Darker green", "Dark green", "Medium green", "Light green"],
                 "Sexy"  : ["Bright red", "Pink", "Dark pink", "Dark purple"],
                 "Romantic": ["Romantic red", "Romantic dark red", "Romantic brown", "Romantic orange", "Romantic pink"],
                 "Rasta": ["Rasta red", "Rasta green", "Rasta yellow", "Rasta dark red"],
                 
                 }

}


for board in settings["devices"]:
    if settings["devices"][board]["configuration"]["TYPE"] == 'ESP8266':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = False
        # Set to False because the firmware handles gamma correction + dither
    elif settings["devices"][board]["configuration"]["TYPE"] == 'RaspberryPi':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = True
        # Set to True because Raspberry Pi doesn't use hardware dithering
    elif settings["devices"][board]["configuration"]["TYPE"] == 'BlinkStick':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = True
    elif settings["devices"][board]["configuration"]["TYPE"] == 'DotStar':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = False
    elif settings["devices"][board]["configuration"]["TYPE"] == 'Fadecandy':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = False
    elif settings["devices"][board]["configuration"]["TYPE"] == 'Stripless':
        settings["devices"][board]["configuration"]["SOFTWARE_GAMMA_CORRECTION"] = False
    else:
        raise ValueError("Invalid device selected. Device {} not known.".format(settings["devices"][board]["configuration"]["TYPE"]))
    settings["devices"][board]["effect_opts"]["Power"]["s_count"] =  settings["devices"][board]["configuration"]["N_PIXELS"]//6
    # Cheeky lil fix in case the user sets an odd number of LEDs
    if settings["devices"][board]["configuration"]["N_PIXELS"] % 2:
        settings["devices"][board]["configuration"]["N_PIXELS"] -= 1
