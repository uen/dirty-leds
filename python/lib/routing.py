"""Route the computer's audio through the app (PipeWire), for lookahead

VirtualOutput creates a "dirty-leds" output device and makes it the default,
so whatever is playing (Spotify, a browser...) goes to the app instead of the
speakers. The app records it from there and plays it on to the speakers that
were the default before, a few seconds late (lib/lookahead.py). close() puts
the old default back. The virtual output belongs to a pw-cli process, so if
the app dies it disappears and PipeWire falls back to the speakers by itself.
"""
import json
import shutil
import subprocess
import time

NODE_NAME = "dirty-leds"


def available():
    return all(shutil.which(tool) for tool in ("pw-cli", "pw-dump", "pw-record", "pw-play", "wpctl"))


def _sinks():
    """{node.name: id} of every output device"""
    nodes = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, check=True).stdout)
    return {o["info"]["props"].get("node.name"): o["id"] for o in nodes
            if o.get("type", "").endswith("Node") and o.get("info", {}).get("props", {}).get("media.class") == "Audio/Sink"}


def default_sink():
    """(id, node.name) of the current default output"""
    output = subprocess.run(["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True, check=True).stdout
    node_id = int(output.split(",", 1)[0].split()[1])
    name = next(line.split("=", 1)[1].strip().strip('"') for line in output.splitlines() if "node.name" in line)
    return node_id, name


class VirtualOutput:
    def __init__(self, make_default=True):
        self.previous = default_sink()
        if self.previous[1] == NODE_NAME:
            raise RuntimeError("the dirty-leds output is already the default; is another copy running?")
        self.owner = subprocess.Popen(["pw-cli"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, text=True)
        self.owner.stdin.write(
            "create-node adapter { factory.name=support.null-audio-sink node.name=" + NODE_NAME +
            ' node.description="dirty-leds (lights)" media.class=Audio/Sink'
            " audio.channels=2 audio.position=[ FL FR ] }\n")
        self.owner.stdin.flush()
        self.node_id = None
        for _ in range(50):
            self.node_id = _sinks().get(NODE_NAME)
            if self.node_id is not None:
                break
            time.sleep(0.1)
        if self.node_id is None:
            self.close()
            raise RuntimeError("couldn't create the dirty-leds output")
        self.made_default = make_default
        if make_default:
            subprocess.run(["wpctl", "set-default", str(self.node_id)], check=True)

    @property
    def speakers(self):
        """node.name of the output to play to: the default before this one"""
        return self.previous[1]

    def close(self):
        try:
            if getattr(self, "made_default", False):
                subprocess.run(["wpctl", "set-default", str(self.previous[0])], check=False)
        finally:
            if self.owner.poll() is None:
                self.owner.kill()
                self.owner.wait()
