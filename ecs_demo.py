#! /usr/bin/env python3.6

"""
An ECS test.
"""
from bear_hug.bear_hug import BearTerminal, BearLoop
from bear_hug.bear_utilities import copy_shape
from bear_hug.ecs import Entity, Component, WidgetComponent,\
    CollisionComponent, PositionComponent, WalkerCollisionComponent,\
    PassingComponent, EntityTracker
from bear_hug.ecs_widgets import ECSLayout
from bear_hug.event import BearEventDispatcher, BearEvent
from bear_hug.resources import Atlas, XpLoader
from bear_hug.sound import SoundListener
from bear_hug.widgets import ClosingListener, Widget, FPSCounter, MousePosWidget,\
    Layout, SimpleAnimationWidget, Animation, Label, \
    deserialize_widget


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
        self.last_move = None
        
    def on_event(self, event):
        r = []
        if event.event_type == 'key_down':
            moved = False
            if event.event_value in ('TK_D', 'TK_RIGHT'):
                self.last_move = (1, 0)
                moved = True
            elif event.event_value in ('TK_A', 'TK_LEFT'):
                self.last_move = (-1, 0)
                moved = True
            elif event.event_value in ('TK_S', 'TK_DOWN'):
                self.last_move = (0, 1)
                moved = True
            elif event.event_value in ('TK_W', 'TK_UP'):
                self.last_move = (0, -1)
                moved = True
            if moved:
                # events
                self.relative_move(*self.last_move, emit_event=False)
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

            
def create_barrel(atlas, dispatcher, x, y):
    barrel_entity = Entity(id='Barrel')
    widget = SimpleAnimationWidget(Animation((atlas.get_element('barrel_1'),
                                    atlas.get_element('barrel_2')), 2),
                                    emit_ecs= True)
    widget_component = WidgetComponent(dispatcher, widget, owner=barrel_entity)
    position_component = PositionComponent(dispatcher, x=x, y=y,
                                           owner=barrel_entity)
    passing = PassingComponent(dispatcher, shadow_pos=(0, 7),
                               shadow_size=None,
                               owner=barrel_entity)
    collision = CollisionComponent(dispatcher, owner=barrel_entity)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=barrel_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('Barrel', x, y)))


def create_cop(atlas, dispatcher, x, y):
    """
    Create a cop entity
    :param dispatcher:
    :return:
    """
    cop_entity = Entity(id='cop')
    t = Widget(*atlas.get_element('cop_r'))
    widget = deserialize_widget(repr(t))
    widget_component = WidgetComponent(dispatcher, widget, owner=cop_entity)
    position_component = WalkerComponent(dispatcher, x=x, y=y,
                                         owner=cop_entity)
    collision = WalkerCollisionComponent(dispatcher,
                                         owner=cop_entity)
    passing = PassingComponent(dispatcher,
                               shadow_pos=(0, 15),
                               shadow_size=(13, 3),
                               owner=cop_entity)
    dispatcher.add_event(BearEvent(event_type='ecs_create',
                                   event_value=cop_entity))
    dispatcher.add_event(BearEvent(event_type='ecs_add',
                                   event_value=('cop', x, y)))


t = BearTerminal(font_path='bear_hug/demo_assets/cp437_12x12.png',
                 size='85x60', title='Brutality',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
dispatcher.register_listener(EntityTracker(), ['ecs_create', 'ecs_destroy'])
atlas = Atlas(XpLoader('bear_hug/demo_assets/test_atlas.xp'),
              'bear_hug/demo_assets/test_atlas.json')
chars = [['.' for x in range(44)] for y in range(49)]
colors = copy_shape(chars, 'gray')
layout = ECSLayout(chars, colors)
dispatcher.register_listener(layout, 'all')

create_cop(atlas, dispatcher, 5, 5)
create_barrel(atlas, dispatcher, 20, 20)
# Dev monitor, works outside ECS
monitor = DevMonitor(*atlas.get_element('dev_bg'), dispatcher=dispatcher)
dispatcher.register_listener(monitor, ['tick', 'service'])
# A sound player
jukebox = SoundListener({'step': 'dshoof.wav', 'shot': 'dsshotgn.wav'})
dispatcher.register_listener(jukebox, 'play_sound')

# A label
label = Label(
    """
    This is a basic ECS test.
    
    Try walking around using WASD or
    arrow keys. The steps should make
    a (rather annoying) sound; the
    cop should be unable to walk
    outside the dotted area or through
    the barrel.""",
    just='right'
)
t.start()
t.add_widget(label, (45, 0), layer=1)
t.add_widget(monitor, (0, 50), layer=1)
t.add_widget(layout, (1, 1), layer=1)
loop.run()
