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


**SERVER SETUP**

Needs Python 3, Node 20+ with yarn, and ffmpeg (for playing tracks). On Linux, PipeWire's `pw-record` lets the lights follow whatever your PC is playing.

```
cd python
pip install -r requirements.txt
cd ../web
yarn install
yarn build
```

Open `python/config.json` and add your ESP8266s:
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

Start it and open http://127.0.0.1:8000
```
cd python
python3 main.py --audio system
```

`--audio` picks where the music comes from, and you can switch it in the web interface too:
* `off`: no audio. Ambient effects still run
* `mic`: the default microphone
* `system`: whatever is playing on this PC (PipeWire)
* `track:<file>`: a file in `python/music/`, looped and played through your speakers. Test tracks are generated in `python/music/test/` on start
* `pipe:<path>`: raw 16-bit mono PCM at 48kHz from a FIFO, e.g. from librespot or shairport-sync on a headless box

To control it from your phone, add `"server": {"host": "0.0.0.0"}` to `config.json`. Anyone on your network can then change the lights.


**SIMULATOR**

You don't need any LEDs to work on effects. The presets in `python/rooms/` are configs whose strips point at `127.0.0.1`, with a 3D layout of the room:
```
cd python
python3 main.py --config rooms/living-room.json --audio "track:test/01 Four on the floor 120bpm.wav"
```
The web interface shows the room in 3D with the strips lit exactly as the app sends them. To lay out your real room, add a `"room"` and a `"path"` per device to your `config.json` (see the presets).

**DEVELOPING**

Run both with live reload: the web interface hot-reloads on save (React Fast Refresh), and the Python app restarts when a `.py` file changes. The page reconnects by itself.
```
cd python
pip install -r requirements-dev.txt
watchfiles --filter python "python3 main.py --config rooms/flat.json" .

cd web
yarn dev    # http://localhost:5173, proxies /api to the Python app
```


**PROFILING**

Time every effect stage by stage (DSP, render, send) against the 16.7 ms frame budget:
```
cd python
python3 tools/benchmark.py --track "test/01 Four on the floor 120bpm.wav" --no-sync
```

See where the running app spends its time, including the web server, as a flame graph:
```
py-spy record -o profile.svg -- python3 main.py --config rooms/flat.json --audio "track:test/01 Four on the floor 120bpm.wav"
```

**SUPPORT**

I'm working on making this better. Add me on Discord (manol#7762) for help
