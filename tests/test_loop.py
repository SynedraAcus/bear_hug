# Pytest-compatible tests for loop system

import pytest
from loop import BearLoop, BearLoopException

@pytest.fixture
def loop():
    l = BearLoop()
    yield l

@pytest.fixture
def listener():
    class L:
        def __init__(self):
            self.accepted = None
        
        def on_event(self, event):
            self.accepted = event
    return L()


def test_listener_sets(loop, listener):
    # Assert that the listeners get registered correctly
    loop.register_listener(listener, event_types='all')
    assert all([listener in loop.listeners[x] for x in loop.listeners.keys()])
    # And unregistered, as well
    loop.unregister_listener(listener, event_types=['input'])
    assert listener not in loop.listeners['input']
    assert all([listener in loop.listeners[x] for x in loop.listeners.keys()
                if x != 'input'])
    loop.unregister_listener(listener, event_types='all')
    assert all([listener not in loop.listeners[x] for x in loop.listeners.keys()])
    with pytest.raises(BearLoopException):
        loop.register_listener(listener, event_types=['nonexistent_type'])
    
def test_tick_events(loop):
    # Check that loop does indeed emit test events
    pass
