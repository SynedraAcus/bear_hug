#! /usr/bin/env python3.6

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random

from bear_hug import BearTerminal, BearLoop
from widgets import Widget, FPSCounter, ClosingListener, Label, Layout
from bear_utilities import copy_shape
from event import BearEventDispatcher


class Firework(Widget):
    """
    Draws a `size`*`size` square with some asterisks in it
    Moves asterisks and changes colours every `freq` ticks
    """
    def __init__(self, size=3, freq=15, **kwargs):
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
                if self.terminal:
                    self.terminal.update_widget(self)
                self.ticks_skipped = 0


class FireworkBox(Layout):
    """
    A box that can add and remove fireworks on keypress
    """
    def __init__(self, chars, colors, dispatcher):
        super().__init__(chars, colors)
        self.dispatcher = dispatcher
        self.fireworks = []
        
    def update_bg(self, color):
        new_bg = Widget(copy_shape(self.chars, '.'),
                        copy_shape(self.colors, color))
        self.background = new_bg
    
    def add_firework(self):
        pos = (random.randint(5, len(self.chars[0])-5),
               random.randint(5, len(self.chars[1])-5))
        f = Firework(size=3, freq=3)
        self.dispatcher.register_listener(f, 'tick')
        self.fireworks.append(f)
        self.add_child(f, pos)

    def remove_firework(self):
        if self.fireworks:
            self.remove_child(self.fireworks[-1])
            del(self.fireworks[-1])
    
    def on_event(self, event):
        super().on_event(event)
        if event.event_type == 'key_down':
            if event.event_value == 'TK_SPACE':
                self.update_bg(random.choice(['green', 'yellow', 'gray',
                                              'purple', 'magenta']))
            elif event.event_value == 'TK_LEFT':
                self.remove_firework()
            elif event.event_value == 'TK_RIGHT':
                self.add_firework()

t = BearTerminal(size='40x40', title='Test window', filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
# Setting up a layout for FPS counter
c = [['-', '-', '-', '-', '-'],
     ['|', '.', '.', '.', '|'],
     ['-', '-', '-', '-', '-']]
layout = Layout(c, copy_shape(c, 'green'))
counter = FPSCounter()
layout.add_child(counter, (1, 1))
dispatcher.register_listener(counter, 'tick')
dispatcher.register_listener(layout, 'tick')
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
# Fireworks box
# Remember dispatcher to subscribe children
box = FireworkBox([['.' for x in range(30)] for x in range(30)],
                  [['gray' for x in range(30)] for x in range(30)],
                  dispatcher)
dispatcher.register_listener(box, ['tick', 'key_down'])
t.start()
t.add_widget(box, (5, 5), layer=1)
t.add_widget(layout, pos=(1, 1), layer=0)
# fireworks = [Firework(freq=1) for x in range(4)]
# layer = 1
# for f in fireworks:
#     dispatcher.register_listener(f, ['tick'])
#     t.add_widget(f, pos=(random.randint(0, 26), random.randint(0, 26)),
#                  layer=layer)
#     layer += 1 # To avoid collisions
loop.run()
