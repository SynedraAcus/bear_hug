"""
A loop and event system.
Does not currently support asyncio, nor is threaded.
"""

from bear_hug import BearException
import time

class BearEvent:
    """
    Event data class. Supports two params: event_type and event_value
    event_type should be one of BearHugEvent.event_types
    """
    event_types = {'tick', 'input'}
    
    def __init__(self, event_type='tick', event_value=None):
        self.event_type = event_type
        self.event_value = event_value
        

class BearLoop:
    """
    The event queue and loop class
    """
    def __init__(self, fps=60):
        self.listeners = {x: [] for x in BearEvent.event_types}
        self.last_tick_time = None
        self.fps = fps
    
    def register_listener(self, listener, event_types='all'):
        """
        Add a listener to this loop.
        :param object listener: a listener to add. This is any object with an `on_event`
        callback.
        :param iterable|str event_types: either a list of event_types or 'all'
        :return:
        """
        if not hasattr(listener, 'on_event'):
            raise BearLoopException('Cannot add an object without on_event method as a listener')
        if event_types == 'all':
            event_types = self.listeners.keys()
        if isinstance(event_types, str):
            raise BearLoopException('event_type shoud be \'all\' or a list')
        for event_type in event_types:
            try:
                self.listeners[event_type].append(listener)
            except KeyError:
                raise BearLoopException('Unknown event class {}'.format(
                                            event_type))
    
    def unregister_listener(self, listener, event_types='all'):
        """
        Remove a listener from the loop or some of its event streams.
        :param object listener: listener to remove
        :param iterable|str event_types: event types to unsubscribe from
        :return:
        """
        if event_types == 'all':
            event_types = self.listeners.keys()
        for event_type in event_types:
            if listener in self.listeners[event_type]:
                self.listeners[event_type].remove(listener)
    
    def add_event(self, event, pass_on='next_tick'):
        pass
    
    def start_loop(self):
        pass
    
    def stop_loop(self):
        pass
    
    def on_tick(self):
        pass
    
class BearLoopException(BearException):
    pass
