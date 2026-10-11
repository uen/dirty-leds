"""Constants for the Dirty LEDs integration"""
DOMAIN = "dirty_leds"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6923

# Fallback poll, in case the event stream drops without the connection closing
POLL_SECONDS = 30
# The server streams music features at 60 fps; sensors only need a reading now and then
FEATURES_SECONDS = 2
RECONNECT_SECONDS = 5

OFF_EFFECT = "Off"
AUTO_EFFECT = "Auto"
# What a strip goes back to when turned on without an effect and nothing to restore
DEFAULT_EFFECT = "Scroll"
