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
import inspect

from bear_hug.bear_utilities import BearECSException, BearJSONException
from bear_hug.widgets import Widget, Listener
from bear_hug.event import BearEvent, BearEventDispatcher

from json import dumps, loads


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
            del(self.__dict__[component_name])
            self.components.remove(component_name)
        else:
            raise BearECSException('Cannot remove component ' +
                          '{} that Entity doesn\'t have'.format(component_name))
        
    def __repr__(self):
        # TODO: Entity (de)serializer
        pass
        
    
class Component(Listener):
    """
    A root component class.
    
    Component name is expected to be the same between all components of the same
    class. Component inherits from Listener and is therefore able to receive and
    return BearEvents. Of course, it needs the correct subscriptions to actually
    get them.

    `repr(component)` is used for serialization and should generate a valid
    JSON-encoded dict. It should always include a 'class' key which
    should equal the class name for that component and will be used by a
    deserializer to determine what to create. All other keys will be
    deserialized and treated as kwargs to a newly-created object. To define the
    deserialization protocol, JSON dict may also contain keys formatted as
    '{kwarg_name}_type' which should be a string and will be eval-ed as during
    deserialization. Python's builtin converters (eg `str`, `int` or `float`)
    are perfectly safe, for the custom ones make sure that they are imported
    when the component is created.
    For example, the following is a valid JSON:

    {"class": "TestComponent",
    "x": 5,
    "y": 5,
    "direction": "r",
    "former_owners": ["asd", "zxc", "qwe"],
    "former_owners_type": "set"}

    Its deserialization is equivalent to the following call:
    `x = TestComponent(x=5, y=5, direction='r',
                       former_owners=set(['asd', 'zxc', 'qwe']))`

    The following keys are forbidden: 'name', 'owner', 'dispatcher'. Kwarg
    validity is not controlled except by `Component.__init__()`.

    """
    def __init__(self, dispatcher, name='Root component', owner=None):
        super().__init__()
        if not name:
            raise BearECSException('Cannot create a component without a name')
        if dispatcher and not isinstance(dispatcher, BearEventDispatcher):
            raise BearECSException(f'Attempted to use {type(dispatcher)} as dispatcher')
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

    def __repr__(self):
        raise NotImplementedError('Component __repr__ should be overloaded to generate a valid JSON')

    def __str__(self):
        owner = self.owner.id if self.owner else 'nobody'
        return f'{type(self).__name__} at {id(self)} attached to {owner}'


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
    
    def __repr__(self):
        #TODO: requires the widget serializer to work
        pass


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
                    new_x = self.x + round(self.x_waited/self.x_delay)\
                        if self.vx > 0\
                        else self.x - round(self.x_waited/self.x_delay)
                    self.x_waited = 0
                else:
                    new_x = self.x
                if self.vy and self.y_waited > self.y_delay:
                    new_y = self.y + round(self.x_waited/self.x_delay)\
                        if self.vy > 0\
                        else self.y - round(self.x_waited/self.x_delay)
                    self.y_waited = 0
                else:
                    new_y = self.y
                if not self.x == new_x or not self.y == new_y:
                    self.move(new_x, new_y)

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'x': self.x,
             'y': self.y,
             'vx': self.vx,
             'vy': self.vy}
        return dumps(d)
                

class SpawnerComponent(Component):
    """
    A component responsible for creating other entities. A current
    implementation is pretty much deprecated. It can produce only a single
    Entity type; in addition, it stores a callable to determine what to spawn
    and therefore can not be serialized via `repr()`. Attempt to serialize
    causes BearECSException to be raised.
    
    :param to_spawn: A callable that returns an Entity to be created. The entity
    needs to have `widget` and `position` components.
    :param relative_pos: a starting position of a spawned Entity, relative to
    self.
    """
    #TODO: rewrite demos to deprecate this piece of shit.
    # The BRUTALITY project has a better SpawnerComponent, but that one spawns
    # entities. See brutality/components.py and brutality/entities.py
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

    def __repr__(self):
        # See class docstring
        raise BearJSONException('Tried to dump SpawnerComponent')


class DestructorComponent(Component):
    """
    A component responsible for cleanly destroying its entity and everything
    that has to do with it.
    """
    def __init__(self, *args, is_destroying=False, **kwargs):
        super().__init__(*args, name='destructor', **kwargs)
        self.is_destroying = is_destroying
        self.dispatcher.register_listener(self, ['service', 'tick'])
    
    def destroy(self):
        """
        Destruct this component's owner.
        Unsubscribes owner and all its components from the queue and sends
        'ecs_remove'. Then all components are deleted. Entity itself is left at
        the mercy of garbage collector.
        :return:
        """
        self.dispatcher.add_event(BearEvent('ecs_destroy', self.owner.id))
        self.is_destroying = True
        # Destroys item on the 'tick_over', so that all
        # existing events involving owner (including 'ecs_remove' are processed
        # normally, but unsubscribes it right now to prevent new ones from forming
        for component in self.owner.components:
            if component != self.name:
                self.dispatcher.unregister_listener(
                    self.owner.__dict__[component])
    
    def on_event(self, event):
        if self.is_destroying and event.event_type == 'tick_over':
            # owner.components stores IDs, not component objects themselves.
            # Those are available only from owner.__dict__
            victims = [x for x in self.owner.components]
            for component in victims:
                if component is not self.name:
                    self.owner.remove_component(component)
            self.dispatcher.unregister_listener(self)
            self.owner.remove_component(self.name)

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'is_destroying': self.is_destroying} # Could be saved right in the middle of destruction
        return dumps(d)


def deserialize_component(json_string, dispatcher):
    """
    Provided a JSON string, creates a necessary object.
    :param json_string:
    :param dispatcher:
    :return:
    """
    d = loads(json_string)
    for forbidden_key in ('name', 'owner', 'dispatcher'):
        if forbidden_key in d.keys():
            raise BearJSONException(f'Forbidden key {forbidden_key} in component JSON')
    if 'class' not in d:
        raise BearJSONException('No class provided in component JSON')
    # Try to get the Component class from where the function was imported, or
    # the importers of *that* frame. Without this, the function would only see
    # classes from this very file, or ones imported into it, and that would
    # break the deserialization of custom components
    for frame in inspect.getouterframes(inspect.currentframe()):
        if d['class'] in frame.frame.f_globals:
            class_var = frame.frame.f_globals[d['class']]
            break
    del frame
    if not issubclass(class_var, Component):
        raise BearJSONException(f"Class name {d['class']}mapped to something other than a Component subclass")
    kwargs = {x: d[x] for x in d.keys() if x != 'class'}
    return class_var(dispatcher, **kwargs)


def deserialize_entity(json_string, dispatcher):
    pass

