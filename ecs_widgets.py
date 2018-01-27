"""
A collection of Widgets designed specifically for the ECS system.
"""

from bear_utilities import BearECSException
from ecs import Entity
from widgets import Layout


class ECSLayout(Layout):
    """
    A Layout of entities.
    
    It is controlled entirely by events. Although Layour methods like
    `add_child` and `move_child` are not overloaded, their use is discouraged.
    
    In all events, entity IDs, not the actual Entity objects, are passed. Event
    conventions are as following:
    
    `BearEvent(event_type='ecs_move', event_value=(entity, x, y))`.
    Announces that the widget of the entity in question should be moved
    to (x; y). Behaviour for widgets trying to leave map edges is left to
    be determined by ECSLayout or its children.
    
    `BearEvent(event_type='ecs_remove', event_value=entity)`.
    Announces that the widget of the entity in question should be removed from
    the ECSLayout. Does not cause or imply the destruction of entity object.
    
    `BearEvent(event_type='ecs_add', event_value=(entity, x, y))`.
    Announces that the widget of the entity in question should be added to the
    ECSLayout at (x;y). The emission of this event implies the existence of the
    entity and its widget.
    """
    
    def __init__(self, chars, colors):
        super().__init__(chars, colors)
        self.entities = {}
        self.widgets = {}
    
    def add_entity(self, entity):
        """
        Register the entity to be displayed. Assumes that the entity has a
        widget already.
        
        The entity is not actually shown until the `'ecs_add'` event is emitted
        :return:
        """
        if not isinstance(entity, Entity):
            raise BearECSException('Cannot add non-Entity to ECSLayout')
        self.entities[entity.id] = entity
        self.widgets[entity.id] = entity.widget.widget
        print('Registered entity {}'.format(entity.id))
        
    def on_event(self, event):
        # React to the events
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            # Attempts to move beyond the screen borders are silently ignored
            # Properly processing them is the collision detector's job anyway
            if not 0 < x < len(self.chars[0]) or not \
                    0 < y < len(self.chars):
                return
            self.move_child(self.widgets[entity_id], (x, y))
        elif event.event_type == 'ecs_create':
            self.add_entity(event.event_value)
        elif event.event_type == 'ecs_remove':
            self.remove_child(self.entities[event.event_value].widget)
        elif event.event_type == 'ecs_add':
            entity_id, x, y = event.event_value
            print('Drawing entity {}'.format(entity_id))
            self.add_child(self.widgets[entity_id], (x, y))
        super().on_event(event)



            