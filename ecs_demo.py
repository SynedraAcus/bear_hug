#! /usr/bin/env python3.6

"""
An ECS test.
"""
from bear_hug import BearTerminal, BearLoop
from bear_utilities import copy_shape
from ecs import Entity, Component, WidgetComponent, PositionComponent
from ecs_widgets import ECSLayout
from event import BearEventDispatcher, BearEvent
from resources import Atlas, XpLoader
from widgets import ClosingListener, Widget, FPSCounter, MousePosWidget, Layout


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
        

class WalkerComponent(PositionComponent):
    """
    A simple PositionComponent that can change x;y on keypress
    """
    def on_event(self, event):
        if event.event_type == 'key_down':
            moved = False
            if event.event_value in ('TK_D', 'TK_RIGHT'):
                self.x += 1
                moved = True
            elif event.event_value in ('TK_A', 'TK_LEFT'):
                self.x -= 1
                moved = True
            elif event.event_value in ('TK_S', 'TK_DOWN'):
                self.y += 1
                moved = True
            elif event.event_value in ('TK_W', 'TK_UP'):
                self.y -= 1
                moved = True
            if moved:
                return BearEvent(event_type='ecs_move',
                                 event_value=(self.owner.id, self.x, self.y))
        super().on_event(event)


def create_cop(atlas, dispatcher, x, y):
    """
    Create a punk entity
    :param dispatcher:
    :return:
    """
    punk_entity = Entity(id='cop')
    widget = Widget(*atlas.get_element('cop'))
    widget_component = WidgetComponent(widget)
    dispatcher.register_listener(widget_component, 'tick')
    position_component = WalkerComponent(x=x, y=y)
    dispatcher.register_listener(position_component, ['tick', 'key_down'])
    punk_entity.add_component(widget_component)
    punk_entity.add_component(position_component)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=punk_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('cop', x, y)))

    
t = BearTerminal(size='85x60', title='Test window',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
atlas = Atlas(XpLoader('test_atlas.xp'), 'test_atlas.json')
chars = [['.' for x in range(85)] for y in range(50)]
colors = copy_shape(chars, 'gray')
layout = ECSLayout(chars, colors)
dispatcher.register_listener(layout, 'all')

create_cop(atlas, dispatcher, 5, 5)

# Dev monitor, works outside ECS
monitor = DevMonitor(*atlas.get_element('dev_bg'), dispatcher)
dispatcher.register_listener(monitor, ['tick', 'service'])

t.start()
t.add_widget(monitor, (0, 50), layer=1)
t.add_widget(layout, (0, 0), layer=1)
loop.run()


