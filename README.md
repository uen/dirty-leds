# dirty-leds
Music reactive WS2812b LEDs with an ESP8266. 


Sorry for lack of documentation, more is coming soon. Please add me on Discord manol#7762 if you have problems / want to help me test. 
You need an ESP8266 / ESP01 (others might work too), WS2812 or WS2812b LED strips (others might work too) and a 5V power supply with enough amps.


**ESP SETUP**

Copy `arduino/ws2812_controller/secrets.h.example` to `secrets.h` and fill in your WiFi (it isn't committed). Each strip's LED count, IP (last number) and name are set when building, so the sketch doesn't need editing. With [arduino-cli](https://arduino.github.io/arduino-cli/), the esp8266 core and the FastLED library:
```
cd arduino/ws2812_controller
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 \
  --build-property 'compiler.cpp.extra_flags=-DNUM_LEDS=150 -DIP_LAST=174 -DSENSOR_NAME="Strip5"' .
arduino-cli upload --fqbn esp8266:esp8266:nodemcuv2 -p /dev/ttyUSB0 .
```
The network in the sketch is 192.168.1.x with the router at .254; change it there if yours differs. Then add the strip to `python/config.json` with the same IP and LED count.

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

Start it and open http://127.0.0.1:6923
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


**AUTO SHOW**

Press **Auto show** in the web interface and the app directs every strip itself. How well it can plan depends on where the music comes from:

* **Tracks in `python/music/`** are pre-analysed (a second or two, cached): the show knows the whole song, builds into drops, goes dark just before them and hits exactly on the beat they land on.
* **System audio with lookahead** routes whatever the computer plays (Spotify, a browser...) through the app and plays it on to your speakers 8 seconds late (`"lookahead": 8` in config.json). The show hears it first, so live music gets the same builds and drops after the first ~25 seconds of each song. Your normal output comes back when you switch away or stop the app.
* **Mic and plain system audio** react live: drops land on the bass coming in, but there is no darkness before them.

Auto's settings have a show style: `mixed` (default), `freestyle` or `effects`. Scenes mostly put every strip on one effect together, sometimes split them up, and sometimes light one strip at a time, passing it around the room on the beat.

To judge a show without watching it, render it to an image and a score card:
```
python3 tools/show_report.py "song.mp3" [--live | --lookahead 8] [--looks]
```

**HOME ASSISTANT**

`home-assistant/` runs Home Assistant in Docker with the Dirty LEDs integration mounted in:
```
cd home-assistant
sudo docker compose up -d
```
Open http://localhost:8123, then Settings > Devices & services > Add integration > Dirty LEDs (host `127.0.0.1`, port `6923`). You get:

* an **LEDs** page in the sidebar with the full web interface
* a light for all strips (on/off, master brightness, effect including Auto) and one per strip (on/off, effect, and what the auto show picked as its `showing` attribute)
* per strip Effect and Colours dropdowns, and Minimum brightness and Calm sliders
* a Music player: the track and its playhead, seeking, the audio sources as its sources, off stops listening
* switches for Auto show and Sync, selects for show style and profile
* Tempo and Intensity sensors (Bass, Mid and Treble are there but disabled by default)
* a `dirty_leds.set_option` action for any other effect setting, e.g. `{option: speed, value: 7}`

Changes from the web interface show up in Home Assistant straight away. Keep the server running with the user service in `systemd/`:
```
cp systemd/dirty-leds.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now dirty-leds
```

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
