.. bear_hug documentation master file, created by
   sphinx-quickstart on Thu Sep 26 14:27:08 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to bear_hug's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Module API reference <modules>

bear_hug is a library for building ASCII-art games and apps in Python 3.6+.

Note that this is *not* curses-like library; bear_hug uses
`bearliterminal <http://foo.wyrd.name/en:bearlibterminal>`_ as a backend, which
in turn uses SDL. It is not meant to work in a TTY.

Currently available:

* multiple useful widgets like layouts, labels, animated
  widgets and so on
* event system
* basic input (keyboard and mouse)
* WAV sound using `simpleaudio <https://pypi.org/project/simpleaudio/>`_
* entity-component system for your gamedev needs

Source code is available (and pull requests are welcome) at the
`github repository <https://github.com/synedraacus/bear_hug>`_

For an example of a simple game made with this library, check out my Ludum Dare
41 gravity-controlled Tetris variant.

.. image:: https://raw.githubusercontent.com/SynedraAcus/bear_hug/master/fd24.png
   :alt: Indirectris screenshot

(`LD page <https://ldjam.com/events/ludum-dare/41/indirectris>`_ |
`repository <https://github.com/synedraacus/indirectris>`_ )

This one is made using only basic widgets and events. For a more complex
ECS-based game, take a look at
`this repository <https://github.com/synedraacus/brutality>`_ (work in progress).

Installation
============

Stable version can be downloaded from PyPI with

`pip install bear_hug`

Latest versions can always be downloaded from the
`repository <https://github.com/synedraacus/bear_hug>`_. Prerequisites are
``bearlibterminal`` and, if you plan to use sound, ``simpleaudio``.

Authors
=======

Alexey Morozov *aka* synedraacus

License
=======

The library itself is available under the terms of MIT license.

Sounds and images included in the demos are available under the terms of CC-BY 3.0

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
