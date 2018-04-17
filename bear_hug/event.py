"""
An event system.
All events are passed around on every tick to listeners' `on_event` method according
to their `event_type` subscriptions.
`on_event` may return either a BearEvent or a list of BearEvents to be added to
the queue. If a list is returned, the events are added (and will be processed)
in the same order as they are in that list.
"""

from bear_hug.bear_utilities import BearLoopException
from collections import deque


class BearEvent:
    """
    Event data class. Has two params: event_type and event_value
    """
    def __init__(self, event_type='tick', event_value=None):
        self.event_type = event_type
        self.event_value = event_value
        

class BearEventDispatcher:
    """
    The BearEvent queue and dispatcher class.
    Iterates until someone emits the 'shutdown' event of type 'service'. Widgets
    may expect the 'shutdown_ready' event of the same type to be emitted a tick
    before that, so that they could finish processing the last tick and save
    their data or whatever. But this is not enforced by the queue.
    """
    def __init__(self):
        self.last_tick_time = None
        # All these event types need to be supported by the queue in order for
        # the engine to function.
        self.event_types = {'tick', # Emitted every tick
                            'key_down', # Key or mouse button down
                            'key_up', # Key or mouse button up
                            'misc_input', # Other input, eg MOUSE_MOVE or CLOSE
                            'text_input', #InputField returns something
                            'service', # To do with queue or engine in general
                            'ecs_create', # A creation of entity
                            'ecs_move', # Movement of entities
                            'ecs_collision', # Collision of entities
                            'ecs_add', # Addition of entity to ECSLayout
                            'ecs_remove', # Removal of entites from ECSLayout
                            'ecs_update' # Someone needs to update ecs screen
                            }
        self.listeners = {x: [] for x in self.event_types}
        self.deque = deque()
    
    def register_listener(self, listener, event_types='all'):
        """
        Add a listener to this event_dispatcher.
        :param object listener: a listener to add. Any object with an `on_event`
        callback can be added. The callback should accept a BearEvent instance
        as a single parametickter.
        :param iterable|str event_types: either a string or an iterable of
        strings. If an iterable, its elements are event types the listener
        subscribes to.
        
        If a string, the following rules apply:
        * If a string equals 'all', the listener is subscribed to all currently
        registered event types.
        * Elif a string starts with '*', the listener is subscribed to all
        currently registered event types for whose name event_types[1:] is a
        substring.
        * Else a string is interpreted as a single event type.
        
        In all cases incorrect event types raise BearLoopException.
        Defaults to 'all'
        :return:
        """
        if not hasattr(listener, 'on_event'):
            raise BearLoopException('Cannot add an object without on_event' +
                                    ' method as a listener')
        if isinstance(event_types, str):
            if event_types == 'all':
                # Subscribing to all events
                types = self.listeners.keys()
            elif event_types[0] == '*':
                # Subscribing to a group of events
                types = []
                mask = event_types[1:]
                for event_type in self.listeners:
                    if mask in event_type:
                        types.append(event_type)
            else:
                # Subscribing to a single event type
                types = [event_types]
        else:
            # Subscribing to a list of event types
            types = event_types
        for event_type in types:
            try:
                self.listeners[event_type].append(listener)
            except KeyError:
                # The incorrect list elements or single value processed here
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
                
    def register_event_type(self, event_type):
        """
        Add a new event type to be processed by queue.
        
        This makes passing (and subscribing to) a new event type possible. No
        listeners are automatically subscribed to it, even those that were
        initially registered with 'all' or fitting '*'-types.
        :param event_type:
        :return:
        """
        if not isinstance(event_type, str):
            raise ValueError('Event type must be a string')
        self.event_types.add(event_type)
        self.listeners[event_type] = []
    
    def add_event(self, event):
        """
        Add a BearEvent to the queue.
        :param event:
        :return:
        """
        if not isinstance(event, BearEvent):
            raise BearLoopException('Only BearEvents can be added to queue')
        if event.event_type not in self.event_types:
            raise BearLoopException('Incorrect event type \"{}\"'.format(
                event.event_type))
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
        Dispatch all the events to their listeners, adding whatever they have to
        say about it to the queue.
        :return:
        """""
        while len(self.deque) > 0:
            e = self.deque.popleft()
            for listener in self.listeners[e.event_type]:
                r = listener.on_event(e)
                if r:
                    if isinstance(r, BearEvent):
                        self.add_event(r)
                    elif isinstance(r, list):
                        for event in r:
                            self.add_event(event)
                    else:
                        raise BearLoopException('on_event returns something ' +
                                                'other than BearEvent')
