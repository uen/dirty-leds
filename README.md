# dirty-leds
Music reactive WS2812b LEDs with an ESP8266. 


Sorry for lack of documentation, more is coming soon. Please add me on Discord manol#7762 if you have problems / want to help me test. 
You need an ESP8266 / ESP01 (others might work too), WS2812 or WS2812b LED strips (others might work too) and a 5V power supply with enough amps.


**ESP SETUP**

Flash the program onto your ESP8266 using Arduino IDE. Make sure you are using this fork of FastLED: https://github.com/coryking/FastLED

Change the settings in ws2812_controller.ino to match your network settings

Change NUM_LEDS to the amount of LEDs you have. Don't change DATA_PIN if you are using an ESP8266 and have the fork above.

You may need to change COLOR_ORDER depending on your LED strip.


**ESP WIRING**

POWER SUPPLY VCC to LED STRIP VCC

POWER SUPPLY VCC TO ESP VCC

POWER SUPPLY GND TO LED STRIP GND

POWER SUPPLY GND TO ESP GND

LED STRIP DATA TO ESP RX


**SERVER SETUP **

Extract the python folder somewhere on your PC.

Open python/config.py. Scroll down to "devices", add your ESP8266 details -- AUTO_DETECT does not work, so you don't need to change that or enter your MAC address.

Run the server

** SUPPORT **

I'm working on making this better. Add me on Discord (manol#7762) for help

##
