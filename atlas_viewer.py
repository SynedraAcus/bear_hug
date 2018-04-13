#! /usr/bin/python3.6

from bear_hug import BearTerminal, BearLoop
from event import BearEventDispatcher
from widgets import ScrollableLayout, ClosingListener, Listener

t = BearTerminal(size='50x45', title='Test window',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
