#  Pytest-compatible tests
import pytest

from bear_hug import BearTerminal, Label

@pytest.fixture
def terminal():
    t = BearTerminal()
    t.start()
    yield t
    t.close()


def test_drawable_pointers(terminal):
    l = Label('Quick fox\nJumped over\nThe lazy dog', just='center',
              color='yellow')
    terminal.add_drawable(l, pos=(11, 11), layer=5)
    l2 = Label('Lorem ipsum\ndolor sit amet')
    terminal.add_drawable(l2, pos=(11, 11), layer=10)
    assert terminal.get_drawable_by_pos((12, 11)) == l2
    assert terminal.get_drawable_by_pos((12, 11), layer=5) == l
    assert terminal.get_drawable_by_pos((14, 10)) is None
