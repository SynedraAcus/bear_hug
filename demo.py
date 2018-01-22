#! /usr/bin/env python3.6

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random
from copy import deepcopy

from bear_hug import BearTerminal, BearLoop
from bear_utilities import copy_shape
from event import BearEventDispatcher
from resources import TxtLoader, XpLoader
from widgets import Widget, FPSCounter, ClosingListener, Label, Layout,\
    MousePosWidget


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
    def __init__(self, chars, colors, dispatcher, loop):
        super().__init__(chars, colors)
        self.dispatcher = dispatcher
        self.loop = loop
        self.fireworks = []
        self.fps = 30
        
    def update_bg(self, color):
        new_bg = Widget(copy_shape(self.chars, '.'),
                        copy_shape(self.colors, color))
        self.background = new_bg
    
    def add_firework(self):
        pos = (random.randint(5, len(self.chars[0])-5),
               random.randint(5, len(self.chars)-5))
        f = Firework(size=3, freq=3)
        self.dispatcher.register_listener(f, 'tick')
        self.fireworks.append(f)
        self.add_child(f, pos)

    def remove_firework(self):
        if self.fireworks:
            self.dispatcher.unregister_listener(self.fireworks[-1])
            self.remove_child(self.fireworks[-1])
            del(self.fireworks[-1])
    
    def on_event(self, event):
        super().on_event(event)
        if event.event_type == 'key_down':
            # Changing background
            if event.event_value == 'TK_SPACE':
                self.update_bg(random.choice(['green', 'yellow', 'gray',
                                              'purple', 'magenta']))
            # Adding and removing fireworks
            elif event.event_value == 'TK_LEFT':
                self.remove_firework()
            elif event.event_value == 'TK_RIGHT':
                self.add_firework()
            # Changing FPS
            elif event.event_value == 'TK_UP':
                self.loop.fps = self.loop.fps + 5
            elif event.event_value == 'TK_DOWN':
                self.loop.fps -= 5


t = BearTerminal(size='50x45', title='Test window', filter=['keyboard', 'mouse'])
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
dispatcher.register_listener(layout, ['service', 'tick'])
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
mouser = MousePosWidget()
dispatcher.register_listener(mouser, ['tick', 'misc_input'])
# Fireworks box
# Remember dispatcher to subscribe children
box = FireworkBox([['.' for x in range(50)] for x in range(15)],
                  [['gray' for x in range(50)] for x in range(15)],
                  dispatcher, loop)
dispatcher.register_listener(box, ['key_down', 'service'])
# A tank, TXTLoader test
loader = TxtLoader('tank.txt')
tank1 = Widget(*loader.get_image_region(0, 0, 5, 6))
tank2 = Widget(*loader.get_image_region(6, 0, 5, 6))
# Tree and lamp, XPLoader test
xploader = XpLoader('tree_lamp.xp')
# A tree without layer2 apples
tree2 = Widget(*xploader.get_layer_region(0, 0, 1, 6, 8))
# Multilayered tree and single-layered lamp
tree = Widget(*xploader.get_image_region(0, 1, 6, 8))
lamp = Widget(*xploader.get_image_region(7, 1, 7, 8))
t.start()
t.add_widget(layout, pos=(1, 1), layer=0)
t.add_widget(mouser, pos=(1, 5), layer=5)
t.add_widget(box, (0, 30), layer=1)
t.add_widget(tank2, (15, 10), layer=3)
t.add_widget(tank1, (20, 23), layer=3)
t.add_widget(tree, (5, 5), layer=2)
t.add_widget(tree2, (40, 12), layer=2)
t.add_widget(lamp, (32, 3), layer=2)
loop.run()
