#! /usr/bin/env python3.6

# Manual test for bearhug. Tests addition and removal of various widgets,
# loading images from TXT and XP, loop and animation system. Does not use ECS.

import random

from bear_hug.bear_hug import BearTerminal, BearLoop
from bear_hug.bear_utilities import copy_shape
from bear_hug.event import BearEventDispatcher
from bear_hug.resources import Atlas, TxtLoader, XpLoader
from bear_hug.widgets import Widget, FPSCounter, ClosingListener, Label, Layout,\
    MousePosWidget, SimpleAnimationWidget, ScrollableLayout, InputField,\
    Animation


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
        self.firework_size = size
    
    def on_event(self, event):
        if event.event_type == 'tick':
            self.ticks_skipped += 1
            if self.ticks_skipped >= self.ticks_to_wait:
                index = random.randint(0, len(self.asterisks)-1)
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = ' '
                self.asterisks[index] = (random.randint(0, self.firework_size-1),
                                         random.randint(0, self.firework_size-1))
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = '*'
                self.colors[self.asterisks[index][0]][self.asterisks[index][1]] = \
                        random.choice(('red', 'blue', 'white'))
                if self.parent is self.terminal:
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
loader = TxtLoader('bear_hug/demo_assets/tank.txt')
tank1 = Widget(*loader.get_image_region(0, 0, 5, 6))
tank2 = Widget(*loader.get_image_region(6, 0, 5, 6))

# XPLoader tests
# A tree without layer2 apples
xploader = XpLoader('bear_hug/demo_assets/tree_lamp.xp')
lamp = Widget(*xploader.get_image_region(7, 1, 7, 8))

# Monitor, with BG loaded from XP atlas and widgets added in monitor.__init__
atlas = Atlas(XpLoader('bear_hug/demo_assets/test_atlas.xp'),
              'bear_hug/demo_assets/test_atlas.json')
monitor = DevMonitor(*atlas.get_element('dev_bg'), dispatcher)
dispatcher.register_listener(monitor, ['tick', 'service'])

# Barrel, an animation test
anim = Animation((atlas.get_element('barrel_1'),
                                atlas.get_element('barrel_2')), 2)
barrel = SimpleAnimationWidget(anim)
dispatcher.register_listener(barrel, ['tick', 'service'])

# A multi-lined text label
label = Label(
    """
    This is a simple bear_hug test/demo.
    If you can see the three images above
    (a barrel, a tank, and a lamppost), all
    atlases load OK. The barrel should be
    animated.
    
    Try using L/R arrow keys
    to change the number of fireworks in
    the block below. Spacebar randomly changes
    block colour.
    
    The block at bottom left should show FPS
    and mouse position (in tiles).
    """
)
t.start()
t.add_widget(barrel, (1, 1))
t.add_widget(tank1, (20, 1))
t.add_widget(monitor, pos=(0, 35), layer=1)
t.add_widget(label, pos=(1, 15))
t.add_widget(box, (12, 35), layer=1)
t.add_widget(lamp, (43, 1), layer=2)
loop.run()
