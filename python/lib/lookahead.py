"""Lookahead for live music: analyse audio a few seconds before it is heard

Live audio (system audio, a mic) can't be analysed ahead like a track, so the
show only learns about a drop as it happens. If the audio is routed through
the app and played to the speakers a few seconds late, the app hears it
first. RollingAnalysis takes the audio as it arrives, analyses the current
song so far every few seconds (lib.analysis, in a background process), and
answers for the moment being heard: the analysis covers up to `delay`
seconds past it, so drops are known before they land.

Songs are told apart by silence: two seconds of it ends a song, and the next
sound starts a new one with a fresh analysis. The previous song's analysis is
kept while its tail is still playing.
"""
import concurrent.futures
import multiprocessing

import numpy as np

import config
from lib.analysis import analyse_audio
from lib.features import SILENCE_DBFS

# A new song needs this much audio before the first analysis is worth running
MIN_SONG_SECONDS = 8.0
# ...and this much before it is trusted: judged against only a few seconds of a
# song, its loudest part so far looks like a peak. Until then the live show runs
TRUST_SECONDS = 25.0
SONG_GAP_SECONDS = 2.0


class Song:
    def __init__(self, start):
        self.start = start  # absolute frame the song started at
        self.end = None  # absolute frame it ended at, once known
        self.chunks = []
        self.analysis = None
        self.analysed_frames = 0  # how much audio the current analysis covers
        self.pending = None  # a running analysis

    @property
    def frames(self):
        return len(self.chunks)


class RollingAnalysis:
    def __init__(self, delay_seconds=8.0, every_seconds=3.0, background=True):
        self.fps = config.settings["configuration"]["FPS"]
        self.delay = int(delay_seconds * self.fps)
        self.every = int(every_seconds * self.fps)
        self.received = 0  # absolute frames received
        self.silent_run = 0
        self.songs = []  # newest last; only the last two are kept
        self.executor = None
        self.background = background
        if background:
            self.executor = self._new_executor()

    @staticmethod
    def _new_executor():
        return concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))

    @property
    def heard(self):
        """Absolute frame being heard now"""
        return self.received - self.delay

    def push(self, samples):
        """One frame of incoming audio (mono float, int16 scale), before the delay"""
        level = 20 * np.log10(np.sqrt(np.mean((samples / 2.0**15) ** 2)) + 1e-9)
        silent = level < SILENCE_DBFS
        self.silent_run = self.silent_run + 1 if silent else 0
        song = self.songs[-1] if self.songs else None
        if song is not None and song.end is None and self.silent_run >= SONG_GAP_SECONDS * self.fps:
            song.end = self.received
        if not silent and (song is None or song.end is not None):
            song = Song(self.received)
            self.songs = self.songs[-1:] + [song]
        if song is not None and song.end is None:
            song.chunks.append(np.asarray(samples, dtype=np.float32) / 2.0**15)
            self._maybe_analyse(song)
        self.received += 1

    def _maybe_analyse(self, song):
        if song.pending is not None:
            if not song.pending.done():
                return
            try:
                song.analysis, song.analysed_frames = song.pending.result()
            except concurrent.futures.process.BrokenProcessPool:
                # The analysis process died: start another and try again next time
                print("dirty-leds: lookahead analysis process stopped, restarting it")
                self.executor = self._new_executor()
            except Exception as error:
                print("dirty-leds: lookahead analysis failed, " + str(error))
            song.pending = None
        if song.frames < MIN_SONG_SECONDS * self.fps or song.frames - song.analysed_frames < self.every:
            return
        audio = np.concatenate(song.chunks)
        if self.executor is None:
            song.analysis, song.analysed_frames = _analyse(audio, song.frames)
        else:
            song.pending = self.executor.submit(_analyse, audio, song.frames)

    def current(self):
        """(analysis, frame within its song) for the moment being heard, or (None, None)
        when it isn't covered yet (start of a song, or audio arriving faster than analysis)"""
        heard = self.heard
        for song in reversed(self.songs):
            if song.start <= heard and (song.end is None or heard < song.end):
                frame = heard - song.start
                if song.analysis is not None and frame < song.analysis.frames \
                        and song.analysed_frames >= TRUST_SECONDS * self.fps:
                    return song.analysis, frame
                return None, None
        return None, None

    def ahead(self):
        """Seconds of the current song analysed beyond what is being heard"""
        analysis, frame = self.current()
        return 0.0 if analysis is None else (analysis.frames - frame) / self.fps

    def close(self):
        if self.executor is not None:
            self.executor.shutdown(wait=False, cancel_futures=True)


def _analyse(audio, frames):
    analysis = analyse_audio(audio)
    # Only part of the song: the newest drop known so far isn't necessarily the last
    analysis.partial = True
    return analysis, frames
