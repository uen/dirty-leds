"""Generate synthetic test tracks into music/test with ffmpeg

Each track exercises a different part of the audio pipeline, so effects can
be checked against known input instead of whatever happens to be playing.
"""
import os
import shutil
import subprocess

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music", "test")
RATE = 48000

# aevalsrc expressions, t is time in seconds
KICK = "sin(2*PI*(45+110*exp(-25*mod(t,{beat})))*mod(t,{beat}))*exp(-7*mod(t,{beat}))"
HAT = "(random(0)*2-1)*exp(-70*mod(t+{beat}/2,{beat}))*0.25"

TRACKS = {
    "01 Four on the floor 120bpm": (30, "0.9*{kick}+{hat}".format(
        kick=KICK.format(beat=0.5), hat=HAT.format(beat=0.5))),
    "02 Breakdown and drop": (32, "if(lt(t,12),0.25*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.25*t)),"
                                  "if(lt(t,16),0.5*sin(2*PI*(200+(t-12)*400)*t)*(t-12)/4,0.95*{kick}+{hat}))".format(
        kick=KICK.format(beat=0.4688), hat=HAT.format(beat=0.4688))),
    "03 Frequency sweep 20Hz-16kHz": (20, "0.6*sin(2*PI*20*20/log(800)*(pow(800,t/20)-1))"),
    "04 Lows mids highs": (24, "0.7*sin(2*PI*if(lt(mod(t,6),2),70,if(lt(mod(t,6),4),1000,7000))*t)"
                               "*(0.5+0.5*sin(2*PI*2*t))"),
    "05 Silence then noise": (16, "if(lt(mod(t,8),4),0,(random(0)*2-1)*0.5)"),
}


def generate(force=False):
    if not shutil.which("ffmpeg"):
        print("dirty-leds: ffmpeg not found, skipping test tracks")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, (duration, expression) in TRACKS.items():
        path = os.path.join(OUT_DIR, name + ".wav")
        if os.path.exists(path) and not force:
            continue
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "aevalsrc='{}':s={}:d={}".format(expression, RATE, duration),
                        "-ac", "1", path], check=True)
        print("dirty-leds: generated test track " + name)


if __name__ == "__main__":
    generate(force=True)
