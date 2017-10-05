#  Pytest-compatible tests
import pytest

from bear_hug import BearTerminal, Label, BearException

@pytest.fixture
def terminal():
    t = BearTerminal()
    t.start()
    yield t
    t.close()


def test_drawable_pointers(terminal):
    #  Check that the correct drawable is returned by get_drawable_by_pos
    l = Label('Quick fox\nJumped over\nThe lazy dog', just='center',
              color='yellow')
    terminal.add_drawable(l, pos=(11, 11), layer=5)
    l2 = Label('Lorem ipsum\ndolor sit amet')
    terminal.add_drawable(l2, pos=(11, 11), layer=10)
    assert terminal.get_drawable_by_pos((12, 11)) == l2
    assert terminal.get_drawable_by_pos((12, 11), layer=5) == l
    assert terminal.get_drawable_by_pos((14, 10)) is None


def test_collision_check(terminal):
    l = Label('Quick fox\nJumped over\nThe lazy dog', just='center',
              color='yellow')
    terminal.add_drawable(l, pos=(11, 11), layer=5)
    l2 = Label('Lorem ipsum\ndolor sit amet')
    l3 = Label('Lorem ipsum\ndolor sit amet')
    l4 = Label('Lorem ipsum\ndolor sit amet')
    # These two should work
    # No collision, same layer
    terminal.add_drawable(l3, pos=(0,0), layer=5)
    # Collision, other layer
    terminal.add_drawable(l4, pos=(11, 11), layer=2)
    with pytest.raises(BearException):
        # Adding a colliding drawable
        terminal.add_drawable(l2, pos=(11, 11), layer=5)
    with pytest.raises(BearException):
        # Adding the same drawable twice
        terminal.add_drawable(l, pos=(0, 0), layer=2)
