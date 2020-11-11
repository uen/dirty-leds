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

* Extract the python folder somewhere on your PC.
* Open python/config.json and input your ESP8266 details
```
{
    "devices": [
        {
            "name": "Name of your lights (such as Bedroom or Window)",
            "type": "ESP8266",
            "ip": "IP of your ESP",
            "port": 7778,
            "leds": Number of LEDs you have
        }
     ]
}
```

* Go to https://viot.co.uk
* Sign in with GitHub (top right)
* Click the "Devices" tab (top)
* Click "Add device" (top right)
* Enter a name (such as "Lights"), a unique identifier (such as "lights-bedroom-1"), select an image and press "Create"
* Once your device is created, click "View details" and copy the api key

* Click the "Home" tab (top)
* Press "New Environment" (top right)
* Enter environment name & submit. An environment is a place like your house
* Press the + button under your environment to add a space
* Enter space name, select an image and submit. A space is a 'space' in your environment, such as your kitchen, bedroom etc.
* Click on your newly created space
* Click "Link device" (top right)
* Link your device

* Open python/config.py and find "apikey" and enter your API key from earlier such as
```
    "apikey": "7e48bbb922e8a2oa25a873bb815291157120537972938082c08bgiwxasf6d6ab5",    
```

run to start the server. You should see the device as online on VIoT
```
python3 main.py
```


** SUPPORT **

I'm working on making this better. Add me on Discord (manol#7762) for help

##
