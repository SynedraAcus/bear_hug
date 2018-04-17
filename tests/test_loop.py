# Pytest-compatible tests for loop system

import pytest
from bear_hug.event import BearEventDispatcher, BearLoopException, BearEvent

@pytest.fixture
def event_dispatcher():
    l = BearEventDispatcher()
    yield l

@pytest.fixture
def listener():
    class L:
        """
        Records the events
        """
        def __init__(self):
            self.accepted_types = []
        
        def on_event(self, event):
            self.accepted_types.append(event.event_type)
    return L()


def test_listener_sets(event_dispatcher, listener):
    # Assert that the listeners get registered correctly
    event_dispatcher.register_listener(listener, event_types='all')
    assert all([listener in event_dispatcher.listeners[x] for x in event_dispatcher.listeners.keys()])
    # And unregistered, as well
    event_dispatcher.unregister_listener(listener, event_types=['input'])
    assert listener not in event_dispatcher.listeners['input']
    assert all([listener in event_dispatcher.listeners[x] for x in event_dispatcher.listeners.keys()
                if x != 'input'])
    event_dispatcher.unregister_listener(listener, event_types='all')
    assert all([listener not in event_dispatcher.listeners[x] for x in event_dispatcher.listeners.keys()])
    # Registering to a single event type
    event_dispatcher.register_listener(listener, event_types='input')
    assert listener in event_dispatcher.listeners['input']
    with pytest.raises(BearLoopException):
        event_dispatcher.register_listener(listener, event_types=['nonexistent_type'])
    
def test_tick_events(event_dispatcher, listener):
    # Check that event_dispatcher does indeed emit test events
    event_dispatcher.register_listener(listener, event_types=['tick', 'input'])
    event_dispatcher.start_queue()
    event_dispatcher.add_event(BearEvent(event_type='tick'))
    event_dispatcher.add_event(BearEvent(event_type='input', event_value='A'))
    event_dispatcher.dispatch_events()
    assert 'tick' in listener.accepted_types
    assert 'service' not in listener.accepted_types
    assert 'input' in listener.accepted_types
    
