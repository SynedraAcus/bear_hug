"""
Loaders for the various ASCII-art formats
"""

from bear_utilities import BearException, copy_shape
import os


class ASCIILoader:
    """
    A base class for all the resource loaders. It knows how to return its chars
    and colors (or a fragment thereof), but expects the children to do their
    loading by themselves.
    """
    def __init__(self):
        self.chars = None
        self.colors = None
    
    def get_image(self):
        """
        Return the entire chars and colors of this loader
        :return:x
        """
        if not self.chars or not self.colors:
            raise BearException('Loader is empty')
        return self.chars, self.colors
    
    def get_image_region(self, x, y, xsize, ysize):
        """
        Return some region of this loader's chars and colors
        As everywhere, the coordinates start from 0.
        :return:
        """
        if not self.chars or not self.colors:
            raise BearException('Loader is empty')
        # Checking for the correct pos and size
        if x < 0 or x > len(self.chars[0]) or y < 0 or y > len(self.chars):
            raise BearException('Region outside loader boundaries')
        if x + xsize > len(self.chars[0]) or y + ysize > len(self.chars):
            raise BearException('Region too huge')
        ch = []
        co = []
        for y_offset in range(ysize):
            r = []
            c = []
            for x_offset in range(xsize):
                try:
                    r.append(self.chars[y + y_offset][x + x_offset])
                    c.append(self.colors[y + y_offset][x + x_offset])
                except IndexError:
                    print(x_offset, y_offset)
            ch.append(r)
            co.append(c)
        return ch, co


class TxtLoader(ASCIILoader):
    """
    A loader that reads a plaintext file.
    On the creation, the loader accepts a filename (anything acceptable by
    `open()`), default color and a bool `load_file`.
    The first argument controls what color would the characters be assigned. As
    `.txt` format does not store colors, all chars will be the same color. The
    latter controls whether the file is read immediately. If False (default), on
    loader creation it only checks that the file exists; if True, its contents
    are immediately loaded to `loader.chars`.
    """
    def __init__(self, filename, default_color='white', load_file=False):
        super().__init__()
        self.default_color = default_color
        if not os.path.exists(filename):
            raise ValueError('Nonexistent path {}'.format(filename))
        self.filename = filename
        if load_file:
            self._load_file()
        
    def _load_file(self):
        for line in open(self.filename):
            f = list(line.rstrip('\n'))
            if self.chars and len(f) != len(self.chars[0]):
                raise BearException('All lines should be equal length')
            if not self.chars:
                self.chars = [f]
            else:
                self.chars.append(f)
        self.colors = copy_shape(self.chars, self.default_color)
        
    def get_image(self):
        if not self.chars or not self.colors:
            self._load_file()
        return super().get_image()
        
    def get_image_region(self, x, y, xsize, ysize):
        if not self.chars or not self.colors:
            self._load_file()
        return super().get_image_region(x, y, xsize, ysize)
