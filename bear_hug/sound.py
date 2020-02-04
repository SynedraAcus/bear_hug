"""
A sound system.

Currently it exports a single class called `SoundListener`. It's a Listener
wrapper around ``simpleaudio`` and ``wave`` libraries. While later the backend
is likely to change (at least to support sound formats other than `.wav`), event
API is probably gonna remain backwards-compatible.
"""

from bear_hug.bear_utilities import BearSoundException
from bear_hug.ecs import Singleton
from bear_hug.widgets import Listener

import simpleaudio as sa
import wave

# TODO: support non-WAV sounds
# Probably easiest way is by moving sound backend into a separate class, while
# leaving interaction with queue to SoundListener. That way, backends may even
# be switched on the fly.


class SoundListener(Listener, metaclass=Singleton):
    """
    It doesn't listen to sounds. It listens to the *events* and plays sounds.
    
    This class is expected to be used as a singleton, ie there is no reason to
    have two SoundListeners active at the same time, and therefore no API for it.
    
    Accepts a single kind of event:
    
    `BearEvent(event_type='play_sound', event_value=sound_name)`
    
    If sound_name is a known sound ID, this sound is (asynchronously) played.
    Otherwise, BearSoundException is raised. Sounds can be either supplied in a
    single arg during creation, or added later via register_sound. In either
    case, for a sound either a `simpleaudio.WaveObject` or a string is expected.
    In the latter case, a string is treated as a path to a `.wav` file.

    :param sounds: a dict of ``{'sound_id': simlpleaudio.WaveObject}``
    """
    def __init__(self, sounds):
        if not isinstance(sounds, dict):
            raise BearSoundException(
                'Only a dict accepted at SoundListener creation')
        if any((not isinstance(x, str) for x in sounds)):
            raise BearSoundException('Only strings accepted as sound IDs')
        for sound_name in sounds:
            if isinstance(sounds[sound_name], sa.WaveObject):
                continue
            if isinstance(sounds[sound_name], str):
                sounds[sound_name] =  sa.WaveObject.from_wave_read(
                    wave.open(sounds[sound_name], 'rb'))
            else:
                raise BearSoundException(
                    'Sound should be either WaveObject or string')
        self.sounds = sounds
        self.bg_sound = None
        self.bg_buffer = None
        
    def register_sound(self, sound, sound_name):
        """
        Register a new sound for this listener

        :param sound: WaveObject or str. A sound to be registered. If str, this is treated as a path to a .wav file.

        :param sound_name: name of this sound.
        """
        if sound_name in self.sounds:
            raise BearSoundException(f'Duplicate sound name "{sound_name}"')
        if isinstance(sound, sa.WaveObject):
            self.sounds[sound_name] = sound
        elif isinstance(sound, str):
            self.sounds[sound_name] = sa.WaveObject.from_wave_read(
                    wave.open('dsstnmov.wav', 'rb'))
        else:
            raise BearSoundException(
                'Sound should be either WaveObject or string')
    
    def play_sound(self, sound_name):
        """
        Play a sound.
        
        In case you need to play the sound without requesting it through the
        event.

        :param sound_name: A sound to play.
        """
        if sound_name not in self.sounds:
            raise BearSoundException(
                f'Nonexistent sound {sound_name} requested')
        return self.sounds[sound_name].play()
    
    def on_event(self, event):
        if event.event_type == 'play_sound':
            self.play_sound(event.event_value)
        elif event.event_type == 'set_bg_sound':
            if self.bg_buffer:
                self.bg_buffer.stop()
            if event.event_value:
                self.bg_sound = event.event_value
                self.bg_buffer = self.play_sound(self.bg_sound)
            else:
                self.bg_buffer = None
                self.bg_sound = None
        elif event.event_type == 'tick' and self.bg_sound:
            if not self.bg_buffer.is_playing():
                self.bg_buffer = self.play_sound(self.bg_sound)
