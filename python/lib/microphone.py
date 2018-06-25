import time
import numpy as np
import pyaudio
import config


def start_stream(callback):
    p = pyaudio.PyAudio()
    frames_per_buffer = int(config.settings["configuration"]["MIC_RATE"] / config.settings["configuration"]["FPS"])
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=config.settings["configuration"]["MIC_RATE"],
                    input=True,
                    frames_per_buffer=frames_per_buffer)
    overflows = 0
    prev_ovf_time = time.time()
    while True:
        try:
            y = np.frombuffer(stream.read(frames_per_buffer, exception_on_overflow=False), dtype=np.int16)
            y = y.astype(np.float32)
            callback(y)
        except IOError:
            overflows += 1
            if time.time() > prev_ovf_time + 1:
                prev_ovf_time = time.time()
                print('Audio buffer has overflowed {} times'.format(overflows))
    stream.stop_stream()
    stream.close()
    p.terminate()
