"""
Entity-component system.

Entities are just the sets of components, nothing more. The major way for them
to be used should be components calling something like
`self.owner.that_other_component.do_stuff` or emitting `ecs_*` events.

The creation of a new Entity is announced by the following event:
`BearEvent(event_type='ecs_create', event_value=entity)`

It is the only event type that uses the actual entity object, not its ID, as the
event_value. When this event is emitted, the entity should be ready to work,
in particular, all its components should be subscribed to the appropriate events
"""

from bear_hug.bear_utilities import BearECSException
from bear_hug.widgets import Widget, Listener
from bear_hug.event import BearEvent


class Entity:
    """
    A root entity class.
    """
    
    def __init__(self, id='Default ID', components=[]):
        self.components = []
        self.id = id
        for component in components:
            self.add_component(component)
        
    def add_component(self, component):
        """
        Adds component to the Entity __dict__
        Raises exception if the Component.name corresponds to one of the already
        existing elements of __dict__ and isn't in self.components. The latter
        check is to allow overwriting components while preventing them from
        overwriting the builtin properties.
        :param component:
        :return:
        """
        if not isinstance(component, Component):
            raise BearECSException('Only Component instance can be added' +
                                   ' as an entity\'s component')
        if component.name not in self.components and \
                component.name in self.__dict__:
            raise BearECSException('Cannot add component' +
                   '{} that shadows builtin attribute'.format(component.name))
        self.__dict__[component.name] = component
        self.components.append(component.name)
        component.owner = self
    
    def remove_component(self, component_name):
        if component_name in self.components:
            del(self.components[component_name])
        else:
            raise BearECSException('Cannot remove component ' +
                          '{} that Entity doesn\'t have'.format(component_name))
        
    
class Component(Listener):
    """
    A root component class.
    
    Component name is expected to be the same between all components of the same
    class.
    
    Component inherits from Listener and is therefore able to receive and return
    BearEvents. Of course, it needs the correct subscriptions to actually get
    them.
    """
    def __init__(self, dispatcher, name='Root component', owner=None):
        super().__init__()
        if not name:
            raise BearECSException('Cannot create a component without a name')
        self.dispatcher = dispatcher
        self.name = name
        self.owner = None
        self.set_owner(owner)
            
    def set_owner(self, owner):
        """
        Registers a component owner.
        
        This is only useful if the component is passed from one owner to
        another, or if the component is created with the `owner` argument.
        This method calls owner's `add_component`
        :param owner:
        :return:
        """
        if owner:
            if not isinstance(owner, Entity):
                raise BearECSException('Only an Entity can be Component owner')
            owner.add_component(self)
        
    def on_event(self, event):
        """
        Component's event callback.
        :param event:
        :return:
        """
        pass


class WidgetComponent(Component):
    """
    Widget as a component.
    
    This component is an ECS wrapper around the Widget object. Since Widgets
    can accept events and it is sometimes reasonable to keep some event logic in
    the Widget instead of Components (ie to keep animation running), its
    `on_event` method simply passes the events to the Widget. It also supports
    `height`, `width` and `size` properties, also by calling widget's ones.
    """
    
    def __init__(self, dispatcher, widget, owner=None):
        if not isinstance(widget, Widget):
            raise TypeError('A widget is not actually a Widget')
        super().__init__(dispatcher=dispatcher, name='widget', owner=owner)
        self.widget = widget
        if self.dispatcher:
            self.dispatcher.register_listener(self.widget, 'tick')

    def on_event(self, event):
        return self.widget.on_event(event)

    @property
    def height(self):
        return self.widget.height

    @property
    def width(self):
        return self.widget.width

    @property
    def size(self):
        return self.widget.size


class PositionComponent(Component):
    """
    A component responsible for positioning Widget on ECSLayout.
    
    It has x and y coordinates, as well as vx and vy speed components.
    Coordinates are given in tiles and speed is in tiles per second.
    """
    def __init__(self, dispatcher, x=0, y=0, vx=0, vy=0, owner=None):
        super().__init__(dispatcher, name='position', owner=owner)
        self._x = x
        self._y = y
        self.vx = vx
        if self.vx:
            self.x_delay = abs(1/self.vx)
        self.x_waited = 0
        self.vy = vy
        if self.vy:
            self.y_delay = abs(1/self.vy)
        self.y_waited = 0
        if self.dispatcher:
            dispatcher.register_listener(self, 'tick')
        
    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y
    
    def move(self, x, y, emit_event=True):
        """
        Move the Entity to a specified position.
        :param x: x
        :param y: y
        :param emit_event: Whether to emit an 'esc_move' event. There are a few
        cases (ie setting the coordinates after the component is created, but
        before the entity is added to the terminal) where this is undesirable.
        :return:
        """
        self._x = x
        self._y = y
        if emit_event:
            self.dispatcher.add_event(BearEvent(event_type='ecs_move',
                                                event_value=(self.owner.id,
                                                             self._x,
                                                             self._y)))

    def relative_move(self, dx, dy, emit_event=True):
        """
        Move the Entity to a specified position.
        :param x: x
        :param y: y
        :param emit_event: Whether to emit an 'esc_move' event. There are a few
        cases (ie setting the coordinates after the component is created, but
        before the entity is added to the terminal) where this is undesirable.
        :return:
        """
        self.move(self.x+dx, self.y+dy, emit_event=emit_event)
        
    def on_event(self, event):
        if event.event_type == 'tick':
            # Move
            if self.vx or self.vy:
                self.x_waited += event.event_value
                self.y_waited += event.event_value
                if self.vx and self.x_waited > self.x_delay:
                    new_x = self.x + 1 if self.vx > 0 else self.x - 1
                    self.x_waited = 0
                else:
                    new_x = self.x
                if self.vy and self.y_waited > self.y_delay:
                    new_y = self.y + 1 if self.vy > 0 else self.y - 1
                    self.y_waited = 0
                else:
                    new_y = self.y
                if not self.x == new_x or not self.y == new_y:
                    self.move(new_x, new_y)
                

class SpawnerComponent(Component):
    """
    A component responsible for creating other entities. A current
    implementation can produce only a single Entity type; this will be fixed
    when entity factories are up and running.
    
    :param to_spawn: A callable that returns an Entity to be created. The entity
    needs to have `widget` and `position` components.
    :param relative_pos: a starting position of a spawned Entity, relative to
    self.
    """
    # TODO: accept entity factories
    def __init__(self, dispatcher, to_spawn, relative_pos=(0, 0), owner=None):
        super().__init__(dispatcher, name='spawner', owner=owner)
        self.to_spawn = to_spawn
        self.relative_pos = relative_pos
        self.id_count = 0
        
    def create_entity(self):
        entity = self.to_spawn()
        for component in (entity.__dict__[c] for c in entity.components):
            component.dispatcher = self.dispatcher
        entity.id += str(self.id_count)
        self.id_count += 1
        entity.position.move(self.owner.position.x + self.relative_pos[0],
                             self.owner.position.y + self.relative_pos[1],
                             emit_event=False)
        self.dispatcher.add_event(BearEvent(event_type='ecs_create',
                                            event_value=entity))
        self.dispatcher.add_event(BearEvent(event_type='ecs_add',
                                            event_value=(entity.id,
                                                         entity.position.x,
                                                         entity.position.y)))
