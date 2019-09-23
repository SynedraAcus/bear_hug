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

from bear_hug.bear_utilities import BearECSException, BearJSONException, \
    rectangles_collide
from bear_hug.widgets import Widget, Listener, deserialize_widget
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
        d = {'id': self.id,
             'components': {x: repr(self.__dict__[x]) for x in self.components}}
        return dumps(d)
        
    
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
    deserialization. Only Python's builtin converters (eg `str`, `int` or
    `float`) are perfectly safe; custom ones are currently unsupported.
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
        # The most basic serialization. Just states that an Entity has a
        # component of this class, but stores no data
        d = {'class': self.__class__.__name__}
        return dumps(d)

    def __str__(self):
        owner = self.owner.id if self.owner else 'nobody'
        return f'{type(self).__name__} at {id(self)} attached to {owner}'


# Copypasting SO is the only correct way to program
# https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                 **kwargs)
        return cls._instances[cls]


class EntityTracker(Listener, metaclass=Singleton):
    """
    Listens to the ecs_add and ecs_destroy events and keeps track of all the
    currently existing entities.

    This tracker is used for entity lookup, eg by Components that need to find
    all possible entities that fulfill certain criteria
    """

    def __init__(self):
        super().__init__()
        self.entities = {}

    def on_event(self, event):
        if event.event_type == 'ecs_create':
            self.entities[event.event_value.id] = event.event_value
        elif event.event_type == 'ecs_destroy':
            del self.entities[event.event_value]

    def filter_entities(self, key=lambda x: x):
        """
        Return all entities for which key evaluates to True.

        Note that this method returns entity objects themselves, not the IDs.
        :param key: A single-arg callable
        :return:
        """
        if not hasattr(key, '__call__'):
            raise ValueError('EntityTracker requires callable for a key')
        for entity_id in self.entities:
            if key(self.entities[entity_id]):
                yield self.entities[entity_id]


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
            self.dispatcher.register_listener(self, 'tick')

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
        d = {'widget': loads(repr(self.widget)),
             'class': self.__class__.__name__}
        return dumps(d)


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
        self.x_delay = None
        self.y_delay = None
        self.x_waited = 0
        self.y_waited = 0
        self.vx = vx
        self.vy = vy
        if self.dispatcher:
            dispatcher.register_listener(self, 'tick')

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def vx(self):
        return self._vx

    @vx.setter
    def vx(self, value):
        self._vx = value
        if value != 0:
            self.x_delay = abs(1/self._vx)
        else:
            self.x_delay = None

    @property
    def vy(self):
        return self._vy

    @vy.setter
    def vy(self, value):
        self._vy = value
        if value != 0:
            self.y_delay = abs(1/self._vy)
        else:
            self.y_delay = None

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
                if self.x_delay and self.x_waited > self.x_delay:
                    new_x = self.x + round(self.x_waited/self.x_delay)\
                        if self.vx > 0\
                        else self.x - round(self.x_waited/self.x_delay)
                    self.x_waited = 0
                else:
                    new_x = self.x
                if self.y_delay and self.y_waited > self.y_delay:
                    new_y = self.y + round(self.y_waited/self.y_delay)\
                        if self.vy > 0\
                        else self.y - round(self.y_waited/self.y_delay)
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
        # existing events involving owner (including 'ecs_remove)' are processed
        # normally, but unsubscribes it right now to prevent new ones from forming
        for component in self.owner.components:
            if component != self.name:
                self.dispatcher.unregister_listener(
                    self.owner.__dict__[component])
    
    def on_event(self, event):
        if self.is_destroying and event.event_type == 'service' and event.event_value == 'tick_over':
            # owner.components stores IDs, not component objects themselves.
            # Those are available only from owner.__dict__
            victims = [x for x in self.owner.components]
            for component in victims:
                if component is not self.name:
                    self.dispatcher.unregister_listener(self.owner.__dict__[component])
                    self.owner.remove_component(component)
            self.dispatcher.unregister_listener(self)
            self.owner.remove_component(self.name)

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'is_destroying': self.is_destroying} # Could be saved right in the middle of destruction
        return dumps(d)


class CollisionComponent(Component):
    """
    A component responsible for processing collisions of this object
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name='collision', **kwargs)
        self.dispatcher.register_listener(self, 'ecs_collision')

    def on_event(self, event):
        if event.event_type == 'ecs_collision':
            if event.event_value[0] == self.owner.id:
                self.collided_into(event.event_value[1])
            elif event.event_value[1] == self.owner.id:
                self.collided_by(event.event_value[0])

    def collided_into(self, entity):
        pass

    def collided_by(self, entity):
        pass


class WalkerCollisionComponent(CollisionComponent):
    """
    A collision component that, upon colliding into something impassable,
    moves the entity to where it came from. Expects both entities involved to
    have a PassabilityComponent
    """

    def collided_into(self, entity):
        if entity is not None:
            other = EntityTracker().entities[entity]
            if 'passability' in self.owner.__dict__ and 'passability' in other.__dict__:
                if rectangles_collide((self.owner.position.x +
                                       self.owner.passability.shadow_pos[0],
                                       self.owner.position.y +
                                       self.owner.passability.shadow_pos[1]),
                                      self.owner.passability.shadow_size,
                                      (other.position.x +
                                       other.passability.shadow_pos[0],
                                       other.position.y +
                                       other.passability.shadow_pos[1]),
                                      other.passability.shadow_size):
                    self.owner.position.relative_move(
                        self.owner.position.last_move[0] * -1,
                        self.owner.position.last_move[1] * -1)
        else:
            # Processing collisions with screen edges without involving passability
            self.owner.position.relative_move(
                self.owner.position.last_move[0] * -1,
                self.owner.position.last_move[1] * -1)


class PassingComponent(Component):
    """
    A component responsible for knowing whether items can or cannot be walked
    through.

    Unlike collisions of eg projectiles, walkers can easily collide with screen
    items and each other provided they are "behind" or "ahead" of each other. To
    check for that, PassingComponent stores a sort of hitbox (basically the
    projection on the surface, something like lowest three rows for a
    human-sized object). Then, WalkerCollisionComponent uses those to define
    if walk attempt was unsuccessful.

    All entities that do not have this component are assumed to be passable.
    """

    def __init__(self, *args, shadow_pos=(0, 0), shadow_size=None, **kwargs):
        super().__init__(*args, name='passability', **kwargs)
        self.shadow_pos = shadow_pos
        self._shadow_size = shadow_size

    @property
    def shadow_size(self):
        # TODO: remove the ugly shadow size hack
        # The idea is that shadow size can be set to owner's widget size by
        # default. The only issue is that owner may not be set, or may not have
        # a widget yet, when this component is created. Thus, this hack.
        # Hopefully no one will try and walk into the object before it is shown
        # on screen. Alas, it requires calling a method for a frequently used
        # property and is generally pretty ugly. Remove this if I ever get to
        # optimizing and manage to think of something better.
        if self._shadow_size is None:
            self._shadow_size = self.owner.widget.size
        return self._shadow_size

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'shadow_size': self._shadow_size,
             'shadow_pos': self.shadow_pos}
        return dumps(d)


class DecayComponent(Component):
    """
    Attaches to an entity and destroys it when conditions are met.

    Currently supported destroy conditions are 'keypress' and 'timeout'. If the
    latter is set, you can supply the lifetime (defaults to 1.0 sec)
    """

    def __init__(self, *args, destroy_condition='keypress', lifetime=1.0, age=0,
                 **kwargs):
        super().__init__(*args, name='decay', **kwargs)
        if destroy_condition == 'keypress':
            self.dispatcher.register_listener(self, 'key_down')
        elif destroy_condition == 'timeout':
            self.dispatcher.register_listener(self, 'tick')
            self.lifetime = lifetime
            self.age = age
        else:
            raise ValueError(
                f'destroy_condition should be either keypress or timeout')
        self.destroy_condition = destroy_condition

    def on_event(self, event):
        if self.destroy_condition == 'keypress' and event.event_type == 'key_down':
            self.owner.destructor.destroy()
        elif self.destroy_condition == 'timeout' and event.event_type == 'tick':
            self.age += event.event_value
            if self.age >= self.lifetime:
                self.owner.destructor.destroy()

    def __repr__(self):
        return dumps({'class': self.__class__.__name__,
                      'destroy_condition': self.destroy_condition,
                      'lifetime': self.lifetime,
                      'age': self.age})


def deserialize_component(serial, dispatcher):
    """
    Provided a JSON string, creates a necessary object.
    
    Does not subscribe a component to anything (which can be done either by a
    caller or in the ComponentSubclass.__init__) or assign it to any Entity
    (which is probably done within `deserialize_entity`)
    :param json_string:
    :param dispatcher:
    :return:
    """
    if isinstance(serial, str):
        d = loads(serial)
    elif isinstance(serial, dict):
        d = serial
    else:
        raise BearJSONException(f'Attempting to deserialize {type(serial)} to Component')
    for forbidden_key in ('name', 'owner', 'dispatcher'):
        if forbidden_key in d.keys():
            raise BearJSONException(f'Forbidden key {forbidden_key} in component JSON')
    if 'class' not in d:
        raise BearJSONException('No class provided in component JSON')
    # Only builtins supported for converters. Although custom converters could
    # be provided like with classes, IMO this way is safer
    converters = {}
    for key in d:
        if '_type' in key:
            converters[key[:-5]] = globals()['__builtins__'][d[key]]
    types = [x for x in d if '_type' in x]
    for t in types:
        del(d[t])
    # Try to get the Component class from where the function was imported, or
    # the importers of *that* frame. Without this, the function would only see
    # classes from this very file, or ones imported into it, and that would
    # break the deserialization of custom components.
    class_var = None
    for frame in inspect.getouterframes(inspect.currentframe()):
        if d['class'] in frame.frame.f_globals:
            class_var = frame.frame.f_globals[d['class']]
            break
    del frame
    if not class_var:
        raise BearJSONException(f"Class name {class_var} not imported anywhere in the frame stack")
    if not issubclass(class_var, Component):
        raise BearJSONException(f"Class name {class_var}mapped to something other than a Component subclass")
    kwargs = {}
    for key in d:
        if key == 'class':
            continue
        if key in converters:
            kwargs[key] = converters[key](d[key])
        elif key == 'widget':
            w = deserialize_widget(d['widget'])
            #TODO: subscribe widgets to events other than 'tick' in deserialization
            dispatcher.register_listener(w, 'tick')
            kwargs['widget'] = w
        else:
            kwargs[key] = d[key]
    return class_var(dispatcher, **kwargs)


def deserialize_entity(serial, dispatcher):
    """Load the entity from JSON string or dict.
    
    Does not subscribe a new entity to anything or emit `bear_create` events;
    this should be done by a caller."""
    if isinstance(serial, str):
        d = loads(serial)
    elif isinstance(serial, dict):
        d = serial
    else:
        raise BearJSONException(f'Attempting to deserialize {type(serial)} to Entity')
    components = [deserialize_component(d['components'][x], dispatcher)
                  for x in d['components']]
    return Entity(id=d['id'], components=components)
    
    

