# dirty-leds
Music reactive WS2812b LEDs with an ESP8266. 



Sorry for lack of documentation, more is coming soon. Please add me on Discord manol#7762 if you have problems / want to help me test. This uses https://viot.uk - an IoT service I am developing - to let you control the lights from anywhere.

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



**CONTROL PANEL SETUP:**

Go to https://viot.py and login with your GitHub account

Click 'Me' then click 'New API Key' - make note of this.

Click 'IoT', then create an environment by clicking 'New Environment'. An environment is a place eg your house

Under your environment on the IoT page, you should see a + button. Click the button to add a space. A space is a specific part of your environment eg your kitchen.

Enter a name for your space, and click an image, then submit. Uploading your own header images isn't implemented yet :(

Then click your new space, and add the lights module by clicking 'Add module', entering a display name, and selecting the dirty-leds module. 

Next, copy the the code beginning with # next to the name (eg #fe97ka) of your space.


**SERVER SETUP **

Extract the python folder somewhere on your PC.

Open python/config.py. Scroll down to "devices", add your ESP8266 details -- AUTO_DETECT does not work, so you don't need to change that or enter your MAC address.

Open python/lib/api.py. Change YOUR SPACE IDENTIFIER to the space identifier from earlier. Do not include the #.

Open python/lib/viot.py. Change 'YOUR VIOT.UK API KEY' to the API key you made earlier.

**DONE**

Run python main.py. It should successfully connect to viot. Then go to viot and click your space, you should see the module with a green icon, showing it is conneckted.

Click the module. You should be able to change the effect and options.


** SUPPORT **
I'm working on making this better. Add me on Discord (manol#7762) for help
