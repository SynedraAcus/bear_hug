"""
A sound system.

Currently it exports a single class called `SoundListener`. It's a Listener
wrapper around simpleaudio and wave libraries. While later the backend is likely
to change (at least to support sound formats other than `.wav`), event API is
probably gonna remain backward-compatible.
"""

from bear_hug.bear_utilities import BearSoundException
from bear_hug.widgets import Listener

import simpleaudio as sa
import wave


class SoundListener(Listener):
    """
    It doesn't listen to sounds. It listens to the *events* and plays sounds.
    
    This class is expected to be used as a singleton, *ie* there is no reason to
    have two SoundListeners active at the same time and therefore no API for it.
    
    Accepts events like this:
    
    `BearEvent(event_type='play_sound', event_value=sound_name)`
    
    If sound_name is a known sound ID, this sound is (asynchronously) played.
    Otherwise, BearSoundException is raised. Sounds can be either supplied in a
    single arg, or added later via register_sound.
    """
    def __init__(self, sounds):
        pass
    
    def register_sound(self, sound, sound_name):
        pass
    
    def on_event(self, event):
        pass
