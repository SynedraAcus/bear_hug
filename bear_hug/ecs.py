"""
Entity-component system.

Entities are just an ID and the container of components. The major way for them
to do something useful should be components calling something like
``self.owner.that_other_component.do_stuff()`` or emitting events.

The creation of a new Entity is announced by the following event:
``BearEvent(event_type='ecs_create', event_value=entity)``

It is an only event type that uses the actual entity object, not its ID, as
``event_value``. When this event is emitted, the entity should be ready to work;
in particular, all its components should be subscribed to the appropriate events.

Both Entities and Components can be serialized to JSON using ``repr(object)``
and then deserialized.
"""

from bear_hug.bear_utilities import BearECSException, BearJSONException, \
    rectangles_collide
from bear_hug.widgets import Widget, Listener, deserialize_widget,\
    SwitchingWidget
from bear_hug.event import BearEvent, BearEventDispatcher

import inspect
from json import dumps, loads


class Entity:
    """
    A root entity class.

    This is basically a container of components, and an ID.

    Entity ID not checked for uniqueness during Entity creation, because it's
    possible that the Entity object will be created before the queue is turned
    on (and, therefore, before EntityTracker knows anything about any entities),
    but having non-unique IDs is practically guaranteed to cause some
    entertaining glitches.

    When the component is added to the Entity, its name (a ``component.name``
    attribute) is added to ``entity.__dict__``. This way, other components can
    then address it as ``self.owner.position`` or ``self.owner.widget`` or
    whatever. Names thus serve as something like slots, so that an entity
    couldn't have multiple components for the same function. Possible names are
    not restricted in any way, but it is strongly recommended not to change them
    during inheritance between Component subclasses, and especially not to use
    the same name for any two components that could ever possibly be used within
    a single entity.

    :param id: a string used as an Entity ID.

    :param components: an iterable of Component instances that can will be added to this entity.
    """
    def __init__(self, id='Default ID', components=[]):
        self.components = []
        self.id = id
        for component in components:
            self.add_component(component)
        
    def add_component(self, component):
        """
        Add a single component to the Entity.

        Raises exception if ``Component.name`` is already in ``self.__dict__``
        and not in ``self.components``. This allows overwriting
        components (should you want to change eg the entity's widget), while
        protecting the non-Component properties.

        :param component: A Component instance.
        """
        if not isinstance(component, Component):
            raise BearECSException('Only Component instance can be added' +
                                   ' as an entity\'s component')
        if component.name not in self.components and \
                component.name in self.__dict__:
            raise BearECSException('Cannot add component' +
                   '{} that shadows builtin attribute'.format(component.name))
        self.__dict__[component.name] = component
        if component.name not in self.components:
            self.components.append(component.name)
        component.owner = self
    
    def remove_component(self, component_name):
        """
        Remove a single component from this entity.

        Uses the ``Component.name``, not an actual instance, as an argument. If
        the Entity doesn't have such a component, raises ``BearECSException``

        :param component_name: The name of a component to remove
        :return:
        """
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
    general type (normally, base class for a given role, like position
    component, AI/input controller or a widget interface) and all its
    subclasses). Component inherits from Listener and is therefore able to
    receive and return ``BearEvent``. Of course, it needs the correct
    subscriptions to actually get them.

    ``repr(component)`` is used for serialization and should generate a valid
    JSON-encoded dict. It should always include a 'class' key which
    should equal the class name for that component and will be used by a
    deserializer to determine what to create. All other keys will be
    deserialized and treated as kwargs to a newly-created object. To define the
    deserialization protocol, JSON dict may also contain keys formatted as
    ``{kwarg_name}_type`` which should be a string and will be eval-ed as during
    deserialization. Only Python's builtin converters (eg ``str``, ``int`` or
    ``float``) are allowed; custom ones are currently unsupported.

    For example, the following is a valid JSON:

    ```
    {"class": "TestComponent",
    "x": 5,
    "y": 5,
    "direction": "r",
    "former_owners": ["asd", "zxc", "qwe"],
    "former_owners_type": "set"}
    ```

    Its deserialization is equivalent to the following call:

    ``x = TestComponent(x=5, y=5, direction='r', former_owners=set(['asd', 'zxc', 'qwe']))``

    The following keys are forbidden: 'name', 'owner', 'dispatcher'. Kwarg
    validity is not controlled except by ``Component.__init__()``.

    :param dispatcher: A queue that the component should subscribe to. ``Component.__init__()`` may use this to subscribe to whatever events it needs.

    :param name: A name that will be added to ``Entity.__dict__``. Should be hardcoded in all Component subclasses.

    :param owner: the Entity (actual object, not ID) to which this object should attach.
    """
    def __init__(self, dispatcher, name='Root', owner=None):
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
        Register a component owner.
        
        This is only useful if the component is passed from one owner to
        another, or if the component is created with the `owner` argument (thus
        attaching it immediately upon creation). This method calls owner's
        ``add_component``

        :param owner: an Entity to attach to.
        """
        if owner:
            if not isinstance(owner, Entity):
                raise BearECSException('Only an Entity can be Component owner')
            owner.add_component(self)
        
    def on_event(self, event):
        """
        Component's event callback. Should be overridden if subclasses want to
        process events.

        :param event: BearEvent instance
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
# TODO: move Singleton to bear_utilities?
class Singleton(type):
    """
    A Singleton metaclass for EntityTracker
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                 **kwargs)
        return cls._instances[cls]


class EntityTracker(Listener, metaclass=Singleton):
    """
    A singleton Listener that keeps track of all existing entities.

    Listens to the ``ecs_add`` and ``ecs_destroy events``, updating
    ``self.entities`` accordingly.

    Can be used to look up an entity by its ID:

    ``entity_called_id = EntityTracker.entities['entity_id']``

    Can also be used to get all entities that correspond to some criterion:

    ``entity_iter = EntityTracker().filter_entities(lambda x: 'part_of_id' in x.id)``
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

        :returns: iterator of Entities
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
    ``on_event`` method simply passes the events to the Widget. It also supports
    ``height``, ``width`` and ``size`` properties, also by calling widget's ones.

    :param widget: A Widget instance.
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
        """
        Height of the widget
        """
        return self.widget.height

    @property
    def width(self):
        """
        Width of the widget
        """
        return self.widget.width

    @property
    def size(self):
        """
        A (width, height) tuple
        """
        return self.widget.size

    @property
    def z_level(self):
        return self.widget.z_level

    @z_level.setter
    def z_level(self, value):
        self.widget.z_level = value
    
    def __repr__(self):
        d = {'widget': loads(repr(self.widget)),
             'class': self.__class__.__name__}
        return dumps(d)


class SwitchWidgetComponent(WidgetComponent):
    """
    A widget component that supports SwitchingWidget.

    Provides methods to use its widget-switching abilities without other
    components having to call Widget object directly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(self.widget, SwitchingWidget):
            raise BearECSException(
                'SwitchWidgetComponent can only be used with SwitchingWidget')

    def switch_to_image(self, image_id):
        """
        Switch widget to a necessary image.

        If image ID is incorrect, the widget will raise BearException.

        :param image_id: image ID (str)
        """
        self.widget.switch_to_image(image_id)

    def validate_image(self, image_id):
        """
        Return True if image_id is a valid ID for its widget

        :param image_id: image ID (str)
        """
        return image_id in self.widget.images


class PositionComponent(Component):
    """
    A component responsible for positioning an Entity on ECSLayout.
    
    :param x: A position of top left corner along X axis.

    :param y: A position of top left corner along Y axis

    :param vx: Horizontal speed (chars per second)

    :param vy: Vertical speed (chars per second)

    :param affect_z: Set Z-level for widgets when placing. Default True
    """
    def __init__(self, dispatcher, x=0, y=0, vx=0, vy=0,
                 last_move = (1, 0), affect_z=True, owner=None):
        super().__init__(dispatcher, name='position', owner=owner)
        self._x = x
        self._y = y
        self.x_delay = None
        self.y_delay = None
        self.x_waited = 0
        self.y_waited = 0
        self.vx = vx
        self.vy = vy
        self.last_move = last_move
        self.affect_z = affect_z
        if self.dispatcher:
            dispatcher.register_listener(self, 'tick')

    @property
    def pos(self):
        return (self._x, self._y)

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

        :param emit_event: If True, emit an 'esc_move' event. There are a few cases (ie setting the coordinates after the component is created, but before the entity is added to the terminal) where this is undesirable.
        """
        # This attr is set so that the turn could be undone (for example, that's
        # what WalkerCollision uses to avoid impossible steps).
        self.last_move = (x - self._x, y - self._y)
        self._x = x
        self._y = y
        if self.affect_z and hasattr(self.owner, 'widget'):
            self.owner.widget.widget.z_level = y + self.owner.widget.height
        if emit_event:
            self.dispatcher.add_event(BearEvent(event_type='ecs_move',
                                                event_value=(self.owner.id,
                                                             self._x,
                                                             self._y)))

    def relative_move(self, dx, dy, emit_event=True):
        """
        Move the Entity to a specified position relative to its current position.

        :param dx: Movement along X axis, in chars

        :param dy: Movement along Y axis, in chars

        :param emit_event: gets passed to ``self.move()`` under the hood.
        """
        self.move(self.x+dx, self.y+dy, emit_event=emit_event)
        
    def on_event(self, event):
        """
        Process tick, if dx != 0 or dy != 0

        :param event: A BearEvent instance
        """
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
             'vy': self.vy,
             'last_move': self.last_move}
        return dumps(d)
                

class DestructorComponent(Component):
    """
    A component responsible for cleanly destroying its entity and everything
    that has to do with it.

    When used, all owner's components except this one are unsubscribed from all
    events. The deletion does not happen until tick end, to let any running
    interactions involving the owner finish cleanly.
    """
    def __init__(self, *args, is_destroying=False, **kwargs):
        super().__init__(*args, name='destructor', **kwargs)
        self.is_destroying = is_destroying
        self.dispatcher.register_listener(self, ['service', 'tick'])
    
    def destroy(self):
        """
        Destroy this component's owner.

        Unsubscribes owner and all its components from the queue and sends
        'ecs_remove'. Then all components are deleted. Entity itself is left at
        the mercy of garbage collector.
        """
        self.dispatcher.add_event(BearEvent('ecs_destroy', self.owner.id))
        self.is_destroying = True
        # Destroys item on the 'tick_over', so that all
        # existing events involving owner (including 'ecs_remove') are processed
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
            # Otherwise this component remembers entity and probably blocks GC
            del self.owner
            del self

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'is_destroying': self.is_destroying} # Could be saved right in the middle of destruction
        return dumps(d)


class CollisionComponent(Component):
    """
    A component responsible for processing collisions of this object.

    Stores the following data:

    ``depth``: Int, a number of additional Z-levels over which collision is possible.
    Additional collisions are detected on lower Z-levels, ie the level where the
    object is displayed is always considered to be the front. Defaults to 0,
    ie collides only to the objects within its own Z-level.

    ``z_shift``: A 2-tuple of ints. Every next Z-level is offset from the
    previous one by this much, to create perspective. Defaults to (0, 0), ie no
    offset.

    ``face_position``: A tuple of ints describing upper left corner of the
    collidable part of the entity on the top Z-level. Defaults to (0, 0), ie the
    upper left corner of the widget is where the hitbox begins. This is a
    suitable default for flat items, but not for something drawn in perspective.

    ``face_size``: A tuple of ints describing the size of the collidable part
    of the entity on the top Z-level. If set to (0, 0), entire entity widget is
    considered collidable. Defaults to (0, 0). There is no method for making
    uncollidable entities via setting zero face size; for that, just create your
    entities without any CollisionComponent at all.

    ``passable``: whether collisions with this item should be blocking. This
    class by itself does nothing with this knowledge, but child classes may
    need it to make distinction between collisions where further movement is
    impossible (eg walls) and collisions that should be detected, but do
    not prevent movement (eg walking through fire). Defaults to False, ie
    blocking collision.

    This is a base class, so its event processing just calls
    ``self.collided_into(other_entity)`` when owner moves into something, and
    ``self.collided_by(other_entity)`` when something else moves into the owner.
    Both methods do nothing by themselves;actual collision processing logic
    should be provided by subclasses.

    Creating entities with the CollisionComponent but without either
    PositionComponent or WidgetComponent is just asking for trouble.
    """

    def __init__(self, *args, depth=0, z_shift=(0, 0),
                 face_position=(0, 0), face_size=(0, 0),
                 passable=False, **kwargs):
        super().__init__(*args, name='collision', **kwargs)
        self.dispatcher.register_listener(self, 'ecs_collision')
        self.depth = depth
        self.passable = passable
        if len(z_shift) != 2 or not all(isinstance(x, int) for x in z_shift):
            raise BearECSException('z_shift for a CollisionComponent should be a tuple of 2 ints')
        self.z_shift = z_shift
        if len(face_position) != 2 or not all(isinstance(x, int) for x in face_position):
            raise BearECSException(
                'face_position for a CollisionComponent should be a tuple of 2 ints')
        self.face_position = face_position
        if len(face_size) != 2 or not all(isinstance(x, int) for x in face_size):
            raise BearECSException('z_shift for a CollisionComponent should be a tuple of 2 ints')
        self.face_size = face_size

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
    A collision component that, upon colliding into something impassable (or
    screen edges), moves the entity back to where it came from.

    Expects both entities involved to have a PositionComponent and a
    PassabilityComponent.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevents the infinite cycle of movement-collision-return-collision...
        # when moving within impassable area
        self.collided_this_tick = False
        self.dispatcher.register_listener(self, 'tick')

    def on_event(self, event):
        if event.event_type == 'tick' and self.collided_this_tick:
            self.collided_this_tick = False
        return super().on_event(event)

    def collided_into(self, entity):
        if self.collided_this_tick:
            return
        if entity is not None:
            try:
                other = EntityTracker().entities[entity]
            except KeyError:
                # Silently pass collisions into nonexistent entities
                return
            # if 'passability' in self.owner.__dict__ and 'passability' in other.__dict__:
            #     if rectangles_collide((self.owner.position.x +
            #                            self.owner.passability.shadow_pos[0],
            #                            self.owner.position.y +
            #                            self.owner.passability.shadow_pos[1]),
            #                           self.owner.passability.shadow_size,
            #                           (other.position.x +
            #                            other.passability.shadow_pos[0],
            #                            other.position.y +
            #                            other.passability.shadow_pos[1]),
            #                           other.passability.shadow_size):
            if hasattr(other, 'collision') and not other.collision.passable:
                tmp_move = self.owner.position.last_move
                self.owner.position.relative_move(
                    self.owner.position.last_move[0] * -1,
                    self.owner.position.last_move[1] * -1)
                # Do not change last_move after collision. We pretend that
                # this move never happened and other components may rely on
                # it
                self.owner.position.last_move = tmp_move
                self.collided_this_tick = True
        else:
            # Processing collisions with screen edges without involving passability
            self.owner.position.relative_move(
                self.owner.position.last_move[0] * -1,
                self.owner.position.last_move[1] * -1)
            self.collided_this_tick = True


class DecayComponent(Component):
    """
    Attaches to an entity and destroys it when conditions are met.

    Expects the owner to have DestructorComponent.

    :param destroy_condition: either 'keypress' or 'timeout'

    :param lifetime: time between entity creation and its destruction. Does nothing if ``destroy_condition`` is set to 'keypress'. Defaults to 1 second.

    :param age: the age of a given entity. Not meant to be set explicitly, except during deserialization.
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


class CollisionListener(Listener):
    """
    A listener responsible for detecting collision
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entities = {}
        self.currently_tracked = set()

    def on_event(self, event):
        if event.event_type == 'ecs_create':
            entity = event.event_value
            # if hasattr(entity, 'position') and hasattr(entity, 'collision'):
            self.entities[entity.id] = entity
        elif event.event_type == 'ecs_destroy':
            del(self.entities[event.event_value])
            if event.event_value in self.currently_tracked:
                self.currently_tracked.remove(event.event_value)
        elif event.event_type == 'ecs_remove':
            if event.event_value in self.currently_tracked:
                self.currently_tracked.remove(event.event_value)
        elif event.event_type == 'ecs_add':
            # Anything added to the screen should have position and widget
            # But if it doesn't have CollisionComponent, it's not our problem
            if hasattr(self.entities[event.event_value[0]], 'collision'):
                self.currently_tracked.add(event.event_value[0])
            print(self.currently_tracked)
        elif event.event_type == 'ecs_move' \
                and event.event_value[0] in self.currently_tracked:
            # Only process collisions between entities; if a collision into the
            # screen edge happens, it's the ECSLayout job to detect it
            moved_id, x, y = event.event_value
            moved_z = self.entities[moved_id].widget.z_level
            moved_depth = self.entities[moved_id].collision.depth
            moved_face = self.entities[moved_id].collision.face_position
            moved_face_size = self.entities[moved_id].collision.face_size
            moved_shift = self.entities[moved_id].collision.z_shift
            if moved_face_size == (0, 0):
                moved_face_size = self.entities[moved_id].widget.size
            r = []
            for other_id in self.currently_tracked:
                other = self.entities[other_id]
                if other_id == moved_id or not hasattr(other, 'position') \
                        or not hasattr(other, 'collision'):
                    continue
                other_z = other.widget.z_level
                other_depth = other.collision.depth
                other_shift = other.collision.z_shift
                if moved_z - moved_depth <= other_z and \
                        other_z - other_depth <= moved_z:
                    # Only check if two entities are within collidable z-levels
                    other_face = other.collision.face_position
                    other_face_size = other.collision.face_size
                    if other_face_size == (0, 0):
                        other_face_size = other.widget.size
                    z_range = (max(moved_z - moved_depth, other_z - other_depth),
                               min(moved_z, other_z))
                    for z_level in range(z_range[0], z_range[1] + 1):
                        moved_pos = (x + moved_face[0] + moved_shift[0]*(moved_z - z_level),
                                     y + moved_face[1] + moved_shift[1]*(moved_z - z_level))
                        other_pos = (other.position.x + other_face[0] + other_shift[0]*(other_z - z_level),
                                     other.position.y + other_face[1] + other_shift[1]*(other_z - z_level))
                        if rectangles_collide(moved_pos, moved_face_size,
                                              other_pos, other_face_size):
                            r.append(BearEvent('ecs_collision',
                                               (moved_id, other_id)))
                            continue
            return r


def deserialize_component(serial, dispatcher):
    """
    Load the component from a JSON string or dict.

    Does not subscribe a component to anything (which can be done either by a
    caller or in the ``ComponentClass.__init__``) or assign it to any Entity
    (which is probably done within ``deserialize_entity``). The class of a
    deserialized Component should be imported by the code that calls this
    function, or someone within its call stack.

    :param serial: A valid JSON string or a dict produced by deserializing such a string.

    :param dispatcher: A queue passed to the ``Component.__init__``

    :returns: a Component instance.
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
            dispatcher.register_listener(w, 'tick')
            kwargs['widget'] = w
        else:
            kwargs[key] = d[key]
    return class_var(dispatcher, **kwargs)


def deserialize_entity(serial, dispatcher):
    """
    Load the entity from JSON string or dict.
    
    Does not subscribe a new entity to anything or emit ``bear_create`` events;
    this should be done by a caller. All components within the entity are
    deserialized by calls to ``deserialize_component``

    :param serial: A valid JSON string or a dict produced by deserializing such a string.

    :returns: an Entity instance
    """
    if isinstance(serial, str):
        d = loads(serial)
    elif isinstance(serial, dict):
        d = serial
    else:
        raise BearJSONException(f'Attempting to deserialize {type(serial)} to Entity')
    components = [deserialize_component(d['components'][x], dispatcher)
                  for x in d['components']]
    return Entity(id=d['id'], components=components)
