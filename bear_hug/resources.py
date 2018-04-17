"""
Loaders for the various ASCII-art formats
"""

from bear_hug.bear_utilities import BearException, copy_shape, rotate_list
from copy import deepcopy
import base64
import gzip
import json
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


class XpLoader(ASCIILoader):
    """
    A loader that reads REXPaint *.xp files.
    As with the other loaders, the file is not parsed until one of the `get_*`
    methods gets called. Its existence, though, is checked on Loader creation.
    
    Most of the code is taken from MIT-licensed XPLoaderPy3, copyright
    Sean Hagar, Erwan Castioni and Gawein Le Goff.
    
    As the bear_hug widget API does not allow multi-layered widgets, `get_image`
    and `get_image_region` return the image with the only the character and
    color from the highest layer which is non-empty for a given cell. For
    getting data from layers separately, use `get_layer` and `get_layer_region`.
    
    Background colors are ignored altogether.
    """

    version_bytes = 4
    layer_count_bytes = 4

    layer_width_bytes = 4
    layer_height_bytes = 4
    layer_keycode_bytes = 4
    layer_fore_rgb_bytes = 3
    layer_back_rgb_bytes = 3
    layer_cell_bytes = layer_keycode_bytes + layer_fore_rgb_bytes + \
                       layer_back_rgb_bytes
    transparent_cell_back_r = 255
    transparent_cell_back_g = 0
    transparent_cell_back_b = 255

    # These chars are not correctly decoded by python's bytes-to-str conversion
    # and have to be processed manually in `_parse_individual_cell()`
    fix_chars = {0x01: "\u263A", 0x02: "\u263B", 0x03: "\u2665", 0x04: "\u2666",
        0x05: "\u2663", 0x06: "\u2660", 0x07: "\u2022", 0x08: "\u25D8",
        0x09: "\u25CB", 0x0a: "\u25D9", 0x0b: "\u2642", 0x0c: "\u2640",
        0x0d: "\u266A", 0x0e: "\u266B", 0x0f: "\u263C", 0x10: "\u25BA",
        0x11: "\u25C4", 0x12: "\u2195", 0x13: "\u203C", 0x14: "\u00B6",
        0x15: "\u00A7", 0x16: "\u25AC", 0x17: "\u21A8", 0x18: "\u2191",
        0x19: "\u2193", 0x1a: "\u2192", 0x1b: "\u2190", 0x1c: "\u221F",
        0x1d: "\u2194", 0x1e: "\u25B2", 0x1f: "\u25BC", 0x7f: "\u2302"}
    
    def __init__(self, filename, default_color='white'):
        super().__init__()
        if not os.path.exists(filename):
            raise ValueError('Nonexistent path {}'.format(filename))
        self.filename = filename
        self.default_color = default_color
        self.layers = []
        self.rexpaint_version = None
        self.width = None
        self.height = None
        self.layer_count = None
    
    def get_image(self):
        """
        Return chars and colors for the entire image. For each cell only the
        values from the topmost layer are used. Background colors are
        ignored altogether.
        :return:
        """
        if not self.chars:
            self._process_xp_file()
            self._get_topmost_layer()
        return super().get_image()

    def get_image_region(self, x, y, xsize, ysize):
        """
        Return chars and colors for the image region. For each cell only the
        values from the topmost layer are used. Background colors are
        ignored altogether.
        :param x:
        :param y:
        :param xsize:
        :param ysize:
        :return:
        """
        if not self.chars:
            self._process_xp_file()
            self._get_topmost_layer()
        return super().get_image_region(x, y, xsize, ysize)
    
    def get_layer(self, layer):
        """
        Get chars and (foreground) colors for the entire image layer. This
        method does not check layer size and returns whatever available.
        
        By default, the REXPaint creates layers the size of the entire image, so
        this shouldn't be much of an issue.
        :param layer:
        :return:
        """
        if not self.layers:
            self._process_xp_file()
        if layer >= self.layer_count:
            raise BearException('Nonexistent layer in XpLoader')
        return deepcopy(self.layers[layer][0]), deepcopy(self.layers[layer][1])
    
    def get_layer_region(self, layer, x, y, xsize, ysize):
        if not self.layers:
            self._process_xp_file()
        if layer >= self.layer_count:
            raise BearException('Nonexistent layer in XpLoader')
        # Shamelessly copypasted from ASCIILoader.get_image_region
        ch = []
        co = []
        for y_offset in range(ysize):
            r = []
            c = []
            for x_offset in range(xsize):
                r.append(self.layers[layer][0][y + y_offset][x + x_offset])
                c.append(self.layers[layer][1][y + y_offset][x + x_offset])
            ch.append(r)
            co.append(c)
        return ch, co

    def _process_xp_file(self):
        gz_handle = gzip.open(self.filename)
        line = gz_handle.read()
        self._load_xp_string(line)
        
    def _get_topmost_layer(self):
        if self.layer_count == 1:
            self.chars = deepcopy(self.layers[0][0])
            self.colors = deepcopy(self.layers[0][1])
        else:
            self.chars = [ [' ' for x in range(self.width)]
                           for y in range(self.height)]
            self.colors = copy_shape(self.chars, None)
            for row in range(self.height):
                for column in range(self.width):
                    for layer in self.layers[::-1]:
                        if layer[0][row][column] != ' ':
                            self.chars[row][column] = layer[0][row][column]
                            self.colors[row][column] = layer[1][row][column]
                            break
        
    # All code from here to the end of the class is adapted from XPLoaderPy3
    # Looks like a mess of crutches on top of other crutches, but I'm not really
    # up to building an elegant solution right now.
    def _load_xp_string(self, file_string, reverse_endian=True):
        """
        Parse REXpaint string and populate self.layers
        :param file_string:
        :param reverse_endian:
        :return:
        """
        offset = 0
        version = file_string[offset: offset + self.version_bytes]
        offset += self.version_bytes
        layer_count = file_string[offset: offset + self.layer_count_bytes]
        offset += self.layer_count_bytes
        if reverse_endian:
            version = version[::-1]
            layer_count = layer_count[::-1]
        self.version = int(base64.b16encode(version), 16)
        self.layer_count = int(base64.b16encode(layer_count), 16)
        current_largest_width = 0
        current_largest_height = 0
        for layer in range(self.layer_count):
            # slight lookahead to figure out how much data to feed load_layer
            this_layer_width = file_string[offset:offset +
                                           self.layer_width_bytes]
            this_layer_height = file_string[
                            offset + self.layer_width_bytes:offset +
                            self.layer_width_bytes + self.layer_height_bytes]
            
            if reverse_endian:
                this_layer_width = this_layer_width[::-1]
                this_layer_height = this_layer_height[::-1]
                
            this_layer_width = int(base64.b16encode(this_layer_width), 16)
            this_layer_height = int(base64.b16encode(this_layer_height), 16)
            current_largest_width = max(current_largest_width, this_layer_width)
            current_largest_height = max(current_largest_height,
                                         this_layer_height)
        
            layer_data_size = self.layer_width_bytes + self.layer_height_bytes\
                + (self.layer_cell_bytes * this_layer_width * this_layer_height)
            layer_data = self._parse_layer(
                file_string[offset:offset + layer_data_size], reverse_endian)
            self.layers.append(layer_data)
            offset += layer_data_size

    def _parse_layer(self, layer_string, reverse_endian=True):
        """
        Parse a file portion for a single layer
        :param layer_string:
        :param reverse_endian:
        :return:
        """
        offset = 0
        width = layer_string[offset:offset + self.layer_width_bytes]
        offset += self.layer_width_bytes
        height = layer_string[offset:offset + self.layer_height_bytes]
        offset += self.layer_height_bytes
    
        if reverse_endian:
            width = width[::-1]
            height = height[::-1]
    
        self.width = int(base64.b16encode(width), 16)
        self.height = int(base64.b16encode(height), 16)
        cells = []
        for x in range(self.width):
            row = []
            for y in range(self.height):
                cell_data_raw = layer_string[offset:offset +
                                                    self.layer_cell_bytes]
                cell_data = self._parse_individual_cell(cell_data_raw,
                                                        reverse_endian)
                row.append(cell_data)
                offset += self.layer_cell_bytes
            cells.append(row)
        cells = rotate_list(cells)
        chars = copy_shape(cells, None)
        colors = copy_shape(cells, self.default_color)
        for r in range(len(cells)):
            for c in range(len(cells[0])):
                chars[r][c] = cells[r][c][0]
                colors[r][c] = cells[r][c][1]
        return chars, colors

    def _parse_individual_cell(self, cell_string, reverse_endian=True):
        """
        Process individual cell data
        :param cell_string:
        :param reverse_endian:
        :return:
        """
        offset = 0
        keycode = cell_string[offset:offset + self.layer_keycode_bytes]
        if reverse_endian:
            keycode = keycode[::-1]
        keycode = int(base64.b16encode(keycode), 16)
        # Processing characters that are redefined by IBM437 from ASCII control
        # sequences and are thus not correctly decoded by `.decode('cp437')`
        if keycode in self.fix_chars:
            char = self.fix_chars[keycode]
        else:
            char = bytes([keycode]).decode('cp437')
        if not char or char == '\x00':
            char = ' '
        offset += self.layer_keycode_bytes
        fore_r = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        fore_g = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        fore_b = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        # Covering cases when we have like '0x4' and '0xAB' in color
        # panning shorter values with zeroes to max size
        rgb = [str(hex(x)).split('x')[1] for x in (fore_r, fore_g, fore_b)]
        length = max((len(x) for x in rgb))
        if length >= 2:
            for index in range(len(rgb)):
                if len(rgb[index]) < length:
                    rgb[index] = '0'*(length - len(rgb[index])) + rgb[index]
        color = '#' + ''.join(rgb)
        # `Back_*` values are ignored, but this code isn't removed in case they
        # are needed later.
        back_r = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        back_g = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        back_b = int(base64.b16encode(cell_string[offset:offset + 1]), 16)
        offset += 1
        return char, color


class Atlas:
    """
    An image atlas.
    
    An instance of this class accepts a Loader instance and a path to the JSON
    file. The latter is parsed immediately.
    """
    def __init__(self, loader, json_file):
        self.loader = loader
        # A dict of {name: (x, y, xsize, ysize)}
        self.elements = {}
        for item in json.load(open(json_file)):
            self.elements[item['name']] = (item['x'], item['y'],
                                        item['xsize'], item['ysize'])
        
    def get_element(self, name):
        """
        Return an element with a given name
        :param name:
        :return:
        """
        return self.loader.get_image_region(*self.elements[name])
