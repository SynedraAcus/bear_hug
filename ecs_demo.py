#! /usr/bin/env python3.6

"""
An ECS test.
"""
from bear_hug.bear_hug import BearTerminal, BearLoop
from bear_hug.bear_utilities import copy_shape
from bear_hug.ecs import Entity, Component, WidgetComponent,\
    PositionComponent, SpawnerComponent
from bear_hug.ecs_widgets import ECSLayout
from bear_hug.event import BearEventDispatcher, BearEvent
from bear_hug.resources import Atlas, XpLoader
from bear_hug.sound import SoundListener
from bear_hug.widgets import ClosingListener, Widget, FPSCounter, MousePosWidget,\
    Layout, LoggingListener, SimpleAnimationWidget, Animation,\
    MultipleAnimationWidget, deserialize_widget, SwitchingWidget

import sys


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher.register_listener(self, ['key_down'])
        
    def on_event(self, event):
        r = []
        if event.event_type == 'key_down':
            moved = False
            if event.event_value in ('TK_D', 'TK_RIGHT'):
                self.move(self.x + 1, self.y, emit_event=False)
                moved = True
            elif event.event_value in ('TK_A', 'TK_LEFT'):
                self.move(self.x - 1, self.y, emit_event=False)
                moved = True
            elif event.event_value in ('TK_S', 'TK_DOWN'):
                self.relative_move(0, 1, emit_event=False)
                moved = True
            elif event.event_value in ('TK_W', 'TK_UP'):
                self.relative_move(0, -1, emit_event=False)
                moved = True
            elif event.event_value in ('TK_SPACE'):
                self.owner.spawner.create_entity()
                r.append(BearEvent(event_type='play_sound',
                                   event_value='shot'))
            if moved:
                # events
                r.append(BearEvent(event_type='ecs_move',
                                   event_value=(self.owner.id, self.x, self.y)))
                r.append(BearEvent(event_type='play_sound',
                                   event_value='step'))
        x = super().on_event(event)
        if x:
            if isinstance(x, BearEvent):
                r.append(x)
            else:
                #multiple return
                r += x
        return r


def create_bullet(atlas):
    """
    Create a bullet
    :return:
    """
    bullet_entity = Entity(id='bullet')
    bullet_fat = Animation((atlas.get_element('bullet_1'),
                           atlas.get_element('bullet_2'),
                            atlas.get_element('bullet_3'),
                            atlas.get_element('bullet_2')), 15)
    widget = MultipleAnimationWidget({'a': bullet_fat}, 'a', cycle=True)
    widget_component = WidgetComponent(None, widget, owner=bullet_entity)
    dispatcher.register_listener(widget_component, 'tick')
    position = PositionComponent(None, vx=50, vy=0, owner=bullet_entity)
    dispatcher.register_listener(position, 'tick')
    return bullet_entity
    

def create_cop(atlas, dispatcher, x, y):
    """
    Create a cop entity
    :param dispatcher:
    :return:
    """
    punk_entity = Entity(id='cop')
    t = Widget(*atlas.get_element('cop_r'))
    widget = deserialize_widget(repr(t))
    # widget = deserialize_widget('{"class": "Widget", "chars": ["  _          ", " (_))        ", " //\"\\        ", " /% _        ", " \\_./        ", " | |____\u2554\u2566\u2550\u2550\u2567", "/ \\\u2502____\u255a\u255d   ", "\\\u2502.\u03a6\u2562        ", "[\\__\u2562/       ", "\\____\u263c       ", "\u255f _\u03a6\u2562/       ", " \u2593\u2593\u2593>/       ", " \u2551\u255f\u2562         ", "\u2554\u2569\u255f\u2562\u2557        ", "\u2560\u2569\u255a\u256c\u2562        ", "\u2560\u2563 \u2560\u2563        ", "\u2560\u2563 \u255a\u2569        ", "\u255a\u2569           "], "colors": ["#000,#000,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000,#000,#000", "#000,#0000d9,#0000d9,#0000d9,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000", "#000,#333333,#333333,#9e8664,#9e8664,#000,#000,#000,#000,#000,#000,#000,#000", "#000,#333333,#333333,#9e8664,#9e8664,#000,#000,#000,#000,#000,#000,#000,#000", "#000,#9e8664,#9e8664,#9e8664,#9e8664,#000,#000,#000,#000,#000,#000,#000,#000", "#000,#9e8664,#9e8664,#9e8664,#0000d9,#0000d9,#0000d9,#0000d9,#9e8664,#9e8664,#9e8664,#9e8664,#9e8664", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#9e8664,#9e8664,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#808080,#0000d9,#000040,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#4d3d26,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#dedede,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#808080,#0000d9,#4d3d26,#000,#000,#000,#000,#000,#000,#000", "#000,#4d3d26,#4d3d26,#4d3d26,#9e8664,#4d3d26,#000,#000,#000,#000,#000,#000,#000", "#000,#0000d9,#0000d9,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#0000d9,#0000d9,#0000d9,#000,#000,#000,#000,#000,#000,#000,#000", "#0000d9,#0000d9,#000040,#4d3d26,#4d3d26,#000,#000,#000,#000,#000,#000,#000,#000", "#4d3d26,#4d3d26,#4d3d26,#4d3d26,#4d3d26,#000,#000,#000,#000,#000,#000,#000,#000"]}')
    widget_component = WidgetComponent(dispatcher, widget, owner=punk_entity)
    position_component = WalkerComponent(dispatcher, x=x, y=y,
                                         owner=punk_entity)
    spawner = SpawnerComponent(dispatcher, lambda: create_bullet(atlas),
                               relative_pos=(13, 5),
                               owner=punk_entity)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=punk_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('cop', x, y)))


class TestTickerComponent(Component):
    """
    A test component that keeps owner's SwitchingWidget
    (assuming that's what is in `owner.widget.widget`) switching between
    'a' and 'b'. Designed for quick-and-dirty testing of SwitchingWidget in ECS
    framework and will break when these image names are unsupported
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_image = 'a'
        
    def on_event(self, event):
        if event.event_type == 'tick':
            self.owner.widget.widget.switch_to_image(self.next_image)
            if self.next_image == 'a':
                self.next_image = 'b'
            else:
                self.next_image = 'a'
            print(self.next_image)
            
            
def create_barrel(atlas, dispatcher, x, y):
    barrel_entity = Entity(id='Barrel')
    widget = SimpleAnimationWidget(Animation((atlas.get_element('barrel_1'),
                                    atlas.get_element('barrel_2')), 2),
                                    emit_ecs= True)
    # Testing JSON dump of SwitchingWidget
    # w = SwitchingWidget(images_dict={'a': atlas.get_element('barrel_1'),
    #                                  'b': atlas.get_element('barrel_2')},
    #                     initial_image='a')
    # widget = deserialize_widget(repr(w))
    # ticker = TestTickerComponent(dispatcher, owner=barrel_entity)
    # dispatcher.register_listener(ticker, 'tick')
    
    widget_component = WidgetComponent(dispatcher, widget, owner=barrel_entity)
    position_component = PositionComponent(dispatcher, x=x, y=y,
                                           owner=barrel_entity)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=barrel_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('Barrel', x, y)))

    
t = BearTerminal(font_path='bear_hug/demo_assets/cp437_12x12.png',
                 size='85x60', title='Brutality',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
atlas = Atlas(XpLoader('bear_hug/demo_assets/test_atlas.xp'),
              'bear_hug/demo_assets/test_atlas.json')
chars = [[' ' for x in range(85)] for y in range(50)]
colors = copy_shape(chars, 'gray')
layout = ECSLayout(chars, colors)
dispatcher.register_listener(layout, 'all')

create_cop(atlas, dispatcher, 5, 5)
create_barrel(atlas, dispatcher, 20, 6)
# Dev monitor, works outside ECS
monitor = DevMonitor(*atlas.get_element('dev_bg'), dispatcher=dispatcher)
dispatcher.register_listener(monitor, ['tick', 'service'])
# A sound player
jukebox = SoundListener({'step': 'dshoof.wav', 'shot': 'dsshotgn.wav'})
dispatcher.register_listener(jukebox, 'play_sound')
# Logger
logger = LoggingListener(handle=sys.stderr)
dispatcher.register_listener(logger, 'play_sound')
t.start()
t.add_widget(monitor, (0, 50), layer=1)
t.add_widget(layout, (0, 0), layer=1)
loop.run()


