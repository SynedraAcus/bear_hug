"""
An event system.
"""

from bear_utilities import BearLoopException, BearException
from collections import deque


class BearEvent:
    """
    Event data class. Supports two params: event_type and event_value
    event_type should be one of BearHugEvent.event_types
    """
    event_types = {'tick', # Emitted every tick
                   'key_down', # Key or mouse button down
                   'key_up', # Key or mouse button up
                   'misc_input', # Other input, eg MOUSE_MOVE or CLOSE
                   'service'} #To do with queue
    
    def __init__(self, event_type='tick', event_value=None):
        self.event_type = event_type
        self.event_value = event_value
        

class BearEventDispatcher:
    """
    The BearEvent queue and dispatcher class
    """
    def __init__(self):
        self.listeners = {x: [] for x in BearEvent.event_types}
        self.last_tick_time = None
        self.deque = deque()
    
    def register_listener(self, listener, event_types='all'):
        """
        Add a listener to this event_dispatcher.
        :param object listener: a listener to add. Any object with an `on_event`
        callback can be added. The callback should accept a BearEvent instance
        as a single parameter.
        :param iterable|str event_types: either a list of event_types or 'all'.
        Defaults to 'all'
        :return:
        """
        if not hasattr(listener, 'on_event'):
            raise BearLoopException('Cannot add an object without on_event' +
                                    ' method as a listener')
        if isinstance(event_types, str):
            if event_types == 'all':
                event_types = self.listeners.keys()
            else:
                # Let's think about incorrect types a bit later
                event_types = [event_types]
        for event_type in event_types:
            try:
                self.listeners[event_type].append(listener)
            except KeyError:
                raise BearLoopException('Unknown event class {}'.format(
                                            event_type))
    
    def unregister_listener(self, listener, event_types='all'):
        """
        Remove a listener from the event_dispatcher or some of its event types.
        :param object listener: listener to remove
        :param iterable|str event_types: event types to unsubscribe from or
        'all'. Defaults to 'all'
        :return:
        """
        if event_types == 'all':
            event_types = self.listeners.keys()
        for event_type in event_types:
            if listener in self.listeners[event_type]:
                self.listeners[event_type].remove(listener)
    
    def add_event(self, event):
        """
        Add a BearEvent to the queue.
        :param event:
        :return:
        """
        if not isinstance(event, BearEvent):
            raise BearLoopException('Only BearEvents can be added to queue')
        self.deque.append(event)
    
    def start_queue(self):
        """
        Sends the queue initialization event to deque
        :return:
        """
        self.deque.append(BearEvent(event_type='service',
                                    event_value='Queue started'))
    
    def dispatch_events(self):
        """
        Dispatch all the events to their listeners
        :return:
        """""
        while len(self.deque) > 0:
            e = self.deque.popleft()
            for listener in self.listeners[e.event_type]:
                listener.on_event(e)
