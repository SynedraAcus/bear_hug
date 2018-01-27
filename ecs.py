"""
Entity-component system.
"""

from bear_utilities import BearECSException


class Entity:
    """
    A root entity class.
    """
    
    def __init__(self, components=[]):
        self.components = []
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
        

class Component:
    """
    A root component class.
    
    Component name is expected to be the same between all components of the same
    class.
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
