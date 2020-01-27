"""
An event system.

Contains a base event class (``BearEvent``) and a queue.

All events are added to the queue and passed around to listeners' ``on_event``
methods according to their ``event_type`` subscriptions. This happens when
``dispatcher.dispatch_events()`` is called, normally every tick.
`on_event` callback may return either nothing, a BearEvent, or a list of
BearEvents. If any events are returned, they are added to the queue (preserving
the order, if there were multiple events within a single return list).

In order to be processed, an event needs to have a correct ``event_type``.
Builtin types are the following:

'tick', emitted every tick. ``event_value`` stores time since the previous such
event.

'service', emitted for various events related to the queue or loop functioning.
Example event_types are 'tick_over' and 'shutdown', emitted during the end of
tick and for shutting down the queue.

'key_down', emitted whenever a key or mouse button is pressed. ``event_value``
stores TK code for the button.

'key_up', emitted whenever a key or mouse button is released. ``event_value``
stores TK code for the button.

'misc_input', emitted whenever there is some non-keyboard input, for example
mouse movement or game window closed via OS UI. ``event_value`` stores TK code
for the input event.

'text_input', emitted when InputField widget wants to return something.
``event_value`` stores the user-entered string.

'play_sound', emitted when someone has requested a sound to be played.
``event_value`` stores the sound ID.

ECS events:

'ecs_create', 'ecs_add', 'ecs_move','ecs_collision', 'ecs_destroy',
'ecs_remove', 'ecs_scroll_by', 'ecs_scroll_to', 'ecs_update'.  These are
described in detail within bear_hug.ecs_widgets docs.

Any user-defined ``event_type`` needs to be registered before use via
``dispatcher.register_event_type()``. Unknown event types can not be added to
the queue. Event values, on the other hand, are not validated at all.
"""

from bear_hug.bear_utilities import BearLoopException
from collections import deque


class BearEvent:
    """
    Event data class.
    """
    __slots__ = ('event_type', 'event_value')
    
    def __init__(self, event_type='tick', event_value=None):
        self.event_type = event_type
        self.event_value = event_value
        

class BearEventDispatcher:
    """
    The BearEvent queue and dispatcher class.

    Stores the events sent to it, then emits them to subscribers in
    chronological order. To start getting events, a Listener needs to subscribe
    via ``dispatcher.register_listener()``.
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
                            'play_sound', # Something requests a sound
                            'set_bg_sound', # Set a sound in the background
                                            # None to disable BG music
                            'service', # To do with queue or engine in general
                            'ecs_create', # A creation of entity
                            'ecs_move', # Movement of entities
                            'ecs_collision', # Collision of entities
                            'ecs_add', # Addition of entity to ECSLayout
                            'ecs_destroy', # Removal of entites from ECSLayout
                            'ecs_remove', # Removal of widgets from ECSLayout
                            'ecs_scroll_by', #Rel scroll for ScrollableECSLayout
                            'ecs_scroll_to', #Abs scroll for ScrollableECSLayout
                            'ecs_update' # Someone needs to update ecs screen
                            }
        self.listeners = {x: [] for x in self.event_types}
        self.deque = deque()
    
    def register_listener(self, listener, event_types='all'):
        """
        Add a listener to this event_dispatcher.

        Any object with an ``on_event`` method can be added as a listener. This
        method should accept BearEvent as a single argument and return either
        nothing, or a single BearEvent, or a list of BearEvents.

        To choose event types to subscribe to, ``event_types`` kwarg can be
        set to a string or an iterable of strings. If an iterable, its elements
        should be event types the listener subscribes to.

        If a string, the following rules apply:

        1. If a string equals 'all', the listener is subscribed to all currently
        registered event types.

        2. Elif a string starts with '*', the listener is subscribed to all
        currently registered event types for whose type ``event_types[1:]`` is a
        substring (regardless of its position). For example, '*ecs' subscribes
        to all ECS events, like 'ecs_add', 'ecs_move', 'ecs_remove' and so on;
        '*move' would subscribe only to 'ecs_move' and 'ecs_remove'.

        3. Else a string is interpreted as a single event type.

        Whether in list or string, unregistered event types raise
        BearLoopException.

        :param listener: a listener to add.

        :param event_types: event types to which it wants to subscribe
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
        Unsubscribe a listener from all or some of its event types.

        :param listener: listener to unsubscribe

        :param event_types: a list of event types to unsubscribe from or 'all'. Defaults to 'all'
        """
        if event_types == 'all':
            event_types = self.listeners.keys()
        for event_type in event_types:
            if listener in self.listeners[event_type]:
                try:
                    self.listeners[event_type].remove(listener)
                except KeyError:
                    raise BearLoopException(f'Attempting to unsubscribe from nonexistent event type {event_type}')
                
    def register_event_type(self, event_type):
        """
        Add a new event type to be processed by queue.
        
        This makes passing (and subscribing to) a new event type possible. No
        listeners are automatically subscribed to it, even those that were
        initially registered with 'all' or fitting '*'-types.

        :param event_type: A string to be used as an event type.
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
        Send the queue initialization event.
        :return:
        """
        self.deque.append(BearEvent(event_type='service',
                                    event_value='Queue started'))
    
    def dispatch_events(self):
        """
        Dispatch all the events to their listeners.
         
        Whatever they return is added to the queue.
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
