"""
A collection of Widgets and Listeners designed specifically for the ECS system.
"""

from bear_utilities import BearECSException, rectangles_collide, copy_shape
from ecs import Entity
from event import BearEvent
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
    
    This widget also provides the collision detection for all widgets within it.
    If a widget attempts to move into the position occupied by some other
    widget, the movement is not blocked, but the 'ecs_collision' event(s) get
    emitted. The event follows the following convention:
    
    `BearEvent(event_type='ecs_collision', event_value=(widget_moved.id,
                                                    widget_collided_into.id))`
    If the widget enters the screen border (ie will go outside it the next time
    it moves, assuming it keeps the direction), the event takes the following
    form:
    `BearEvent(event_type='ecs_collision', event_value=(widget_moved.id,
                                                        None))`
    """
    
    def __init__(self, chars, colors):
        super().__init__(chars, colors)
        self.entities = {}
        # Pointers to actual widgets, not widget components
        self.widgets = {}
        self.need_redraw = False
        # A copy of child_pointers that stores entity IDs instead of Widget objs
        self._child_ids = copy_shape(self._child_pointers)
    
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
        
    def on_event(self, event):
        # A list of events that would be emitted in response to this one
        r = []
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            self.move_child(self.widgets[entity_id], (x, y))
            self.need_redraw = True
            # Checking if collision events need to be emitted
                # Check for collisions with border. Note that it checks
                # self._child_pointers, not self.size, because this could be a
                # ScrollableLayout
            if x == 0 or x+self.entities[entity_id].widget.width\
                 == len(self._child_pointers[0]) or y == 0 or \
                 y + self.entities[entity_id].widget.height == \
                    len(self._child_pointers):
                r.append(BearEvent(event_type='ecs_collision',
                                   event_value=(entity_id, None)))
            else:
                # Collisions with other entities
                collided_ent_ids = set()
                for y_offset in range(self.entities[entity_id].widget.size[1]):
                    for x_offset in range(self.entities[entity_id].widget.size[0]):
                        for other in self._child_ids[y+y_offset][x+x_offset]:
                            if other and other != entity_id:
                                collided_ent_ids.add(other)
                for child in collided_ent_ids:
                    r.append(BearEvent('ecs_collision', (entity_id, child)))
        elif event.event_type == 'ecs_create':
            self.add_entity(event.event_value)
            self.need_redraw = True
        elif event.event_type == 'ecs_remove':
            entity_id = event.event_value
            x, y = self.child_locations[self.widgets[entity_id]]
            self.remove_child(self.widgets[entity_id])
            self.need_redraw = True
            # Updating self._child_ids
            for char_x in range(x, x+self.widgets[entity_id].width):
                for char_y in range(y, y+self.widgets[entity_id].height):
                    self._child_ids[char_y][char_x].remove(entity_id)
        elif event.event_type == 'ecs_add':
            entity_id, x, y = event.event_value
            self.add_child(self.widgets[entity_id], (x, y))
            self.need_redraw = True
            # Updating self._child_ids
            for char_x in range(x, x+self.widgets[entity_id].width):
                for char_y in range(y, y+self.widgets[entity_id].height):
                    self._child_ids[char_y][char_x].append(entity_id)
        elif event.event_type == 'ecs_update':
            # Some entity has decided it's time to redraw itself
            # Not really important which one, just redraw the whole screen
            self.need_redraw = True
        elif event.event_type == 'service' and event.event_value == 'tick_over'\
                and self.need_redraw:
            self._rebuild_self()
            self.terminal.update_widget(self)
            self.need_redraw = False
        if r:
            return r
