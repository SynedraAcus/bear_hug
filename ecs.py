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

from bear_utilities import BearECSException, BearException
from widgets import Widget, Listener
from event import BearEvent, BearEventDispatcher


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
    def __init__(self, name='Root component', owner=None):
        if not name:
            raise BearECSException('Cannot create a component without a name')
        self.name = name
        if owner:
            self.set_owner(owner)
            
    def set_owner(self, owner):
        """
        Registers a component owner.
        
        This is only useful if the component is passed from one owner to
        another.
        :param owner:
        :return:
        """
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
    
    This component is responsible for drawing stuff on the screen. Since Widgets
    can accept events and it is sometimes reasonable to keep some event logic in
    the Widget instead of Components (ie to keep animation running), its
    `on_event` method simply passes the events to the Widget
    """
    
    def __init__(self, widget, owner=None):
        if not isinstance(widget, Widget):
            raise TypeError('A widget is not actually a Widget')
        super().__init__(name='widget', owner=owner)
        self.widget = widget
        
    def on_event(self, event):
        self.widget.on_event(event)
        
        
class PositionComponent(Component):
    """
    A component responsible for positioning Widget on ECSLayout.
    
    It has x and y coordinates, as well as vx and vy speed components.
    Coordinates are given in tiles and speed is in tiles per second.
    """
    def __init__(self, x=0, y=0, vx=0, vy=0, owner=None):
        super().__init__(name='position', owner=owner)
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        
    def on_event(self, event):
        # TODO: process vx and vy
        pass
        

