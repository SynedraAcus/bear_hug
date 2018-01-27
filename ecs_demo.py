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
from widgets import ClosingListener, Widget


def create_punk(atlas, dispatcher, x, y):
    """
    Create a punk entity
    :param dispatcher:
    :return:
    """
    punk_entity = Entity(id='punk1')
    widget = Widget(*atlas.get_element('nunchaku_punk'))
    widget_component = WidgetComponent(widget)
    dispatcher.register_listener(widget_component, 'tick')
    position_component = PositionComponent(x=x, y=y)
    dispatcher.register_listener(position_component, 'tick')
    punk_entity.add_component(widget_component)
    punk_entity.add_component(position_component)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=punk_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('punk1', x, y)))

    
t = BearTerminal(size='50x45', title='Test window',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
atlas = Atlas(XpLoader('test_atlas.xp'), 'test_atlas.json')
chars = [['.' for x in range(50)] for x in range(45)]
colors = copy_shape(chars, 'gray')
layout = ECSLayout(chars, colors)
dispatcher.register_listener(layout, 'all')

create_punk(atlas, dispatcher, 5, 5)

t.start()
t.add_widget(layout, (0, 0), layer=1)
loop.run()


