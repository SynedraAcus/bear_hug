#! /usr/bin/env python3.6

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random

from bear_hug import BearTerminal, BearLoop
from bear_utilities import copy_shape
from event import BearEventDispatcher
from resources import Atlas, TxtLoader, XpLoader
from widgets import Widget, FPSCounter, ClosingListener, Label, Layout,\
    MousePosWidget, SimpleAnimationWidget


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
        self.fireworks_count = Label('Fireworks: 000', color='red',
                                     width=20, height=3)
        self.add_child(self.fireworks_count, (15, 0))
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
        self.fireworks_count.text = 'Fireworks: {0}'.format(
                        str(len(self.fireworks)).rjust(3, '0'))

    def remove_firework(self):
        if self.fireworks:
            self.dispatcher.unregister_listener(self.fireworks[-1])
            self.remove_child(self.fireworks[-1])
            del(self.fireworks[-1])
        self.fireworks_count.text = 'Fireworks: {0}'.format(
            str(len(self.fireworks)).rjust(3, '0'))
    
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
                

class DevMonitor(Layout):
    """
    A monitor that shows FPS and mouse position
    Doesn't do any tracking by itself
    """
    def __init__(self, chars, colors, dispatcher):
        super().__init__(chars, colors)
        counter = FPSCounter()
        dispatcher.register_listener(counter, 'tick')
        self.add_child(counter, (2, 4))
        # Have to remember mouser for terminal setter
        self.mouser = MousePosWidget()
        dispatcher.register_listener(self.mouser, ['tick', 'misc_input'])
        self.add_child(self.mouser, (2, 7))
        
    @property
    def terminal(self):
        return self._terminal
    
    @terminal.setter
    def terminal(self, value):
        self.mouser.terminal = value
        self._terminal = value


class Flipper(Widget):
    """
    A flipping test
    """
    def __init__(self, chars, colors, flip_axis):
        super().__init__(chars, colors)
        self.flip_axis = flip_axis
        
    def on_event(self, event):
        if event.event_type == 'key_down' and event.event_value == 'TK_SPACE':
            self.flip(self.flip_axis)
        self.terminal.update_widget(self)
        
        
t = BearTerminal(size='50x45', title='Test window', filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])

# Fireworks box
box = FireworkBox([['.' for x in range(38)] for x in range(10)],
                  [['gray' for x in range(38)] for x in range(10)],
                  dispatcher)
dispatcher.register_listener(box, ['key_down', 'service'])

# A tank, TXTLoader test
loader = TxtLoader('tank.txt')
tank1 = Widget(*loader.get_image_region(0, 0, 5, 6))
tank2 = Widget(*loader.get_image_region(6, 0, 5, 6))

# XPLoader tests
# A tree without layer2 apples
xploader = XpLoader('tree_lamp.xp')
tree2 = Widget(*xploader.get_layer_region(0, 0, 1, 6, 8))
# Multilayered tree and single-layered lamp
tree = Widget(*xploader.get_image_region(0, 1, 6, 8))
lamp = Widget(*xploader.get_image_region(7, 1, 7, 8))

# Monitor, with BG loaded from XP atlas and widgets added in monitor.__init__
atlas = Atlas(XpLoader('test_atlas.xp'), 'test_atlas.json')
monitor = DevMonitor(*atlas.get_element('dev_bg'), dispatcher)
dispatcher.register_listener(monitor, ['tick', 'service'])

# Barrel, an animation test
barrel = SimpleAnimationWidget((atlas.get_element('barrel_1'),
                                atlas.get_element('barrel_2')), 2)
dispatcher.register_listener(barrel, ['tick', 'service'])

# Flipper
x_flipper = Flipper(*atlas.get_element('bottle_punk'), 'x')
y_flipper = Flipper(*atlas.get_element('bottle_punk'), 'y')
dispatcher.register_listener(x_flipper, ['key_down'])
dispatcher.register_listener(y_flipper, 'key_down')

t.start()
t.add_widget(monitor, pos=(0, 35), layer=1)
t.add_widget(box, (12, 35), layer=1)
t.add_widget(barrel, (5, 5), layer=2)
t.add_widget(lamp, (43, 1), layer=2)
t.add_widget(x_flipper, (20, 15), layer=3)
t.add_widget(y_flipper, (38, 15), layer=3)
loop.run()
