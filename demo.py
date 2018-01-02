#! /usr/bin/env python3.6

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random

from bear_hug import BearTerminal, BearLoop
from widgets import Widget, FPSCounter
from bear_utilities import copy_shape
from event import BearEventDispatcher


class Firework(Widget):
    """
    Draws a `size`*`size` square with some asterisks in it
    Moves asterisks and changes colours every `freq` ticks
    """
    def __init__(self, size=3, freq=10, **kwargs):
        self.asterisks=[(random.randint(0, size-1), random.randint(0, size-1))\
                        for x in range(size)]
        chars = [[' ' for x in range(size)] for x in range(size)]
        colors = copy_shape(chars, 'white')
        for asterisk in self.asterisks:
            chars[asterisk[0]][asterisk[1]] = '*'
            colors[asterisk[0]][asterisk[1]] = random.choice(('red', 'blue', 'white'))
        super().__init__(chars, colors, **kwargs)
        self.ticks_to_wait = freq
        self.ticks_skipped = 0
        self.size = size
    
    def on_event(self, event):
        if event.event_type == 'tick':
            self.ticks_skipped += 1
            if self.ticks_skipped >= self.ticks_to_wait:
                index = random.randint(0, len(self.asterisks)-1)
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = ' '
                self.asterisks[index] = (random.randint(0, self.size-1),
                                         random.randint(0, self.size-1))
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = '*'
                self.colors[self.asterisks[index][0]][self.asterisks[index][1]] = \
                        random.choice(('red', 'blue', 'white'))
                self.terminal.update_widget(self)
                self.ticks_skipped = 0


t = BearTerminal(size='30x30', title='Test window', filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
counter = FPSCounter()
dispatcher.register_listener(counter, ['tick'])
fireworks = [Firework(freq=1) for x in range(4)]
t.start()
t.add_widget(counter, pos=(1, 1), layer=0)
layer = 1
for f in fireworks:
    dispatcher.register_listener(f, ['tick'])
    t.add_widget(f, pos=(random.randint(0, 26), random.randint(0, 26)),
                 layer=layer)
    layer += 1 # To avoid collisions
loop.run()
