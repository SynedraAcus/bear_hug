from setuptools import setup
setup(
  name = 'bear_hug',
  packages = ['bear_hug'],
  version = '0.2.3',
  description = 'An object-oriented ECS library for ASCII games. Wraps bearlibterminal.',
  author = 'Alexey Morozov',
  author_email = 'alexeymorozov1991@gmail.com',
  url = 'https://github.com/SynedraAcus/bear_hug',
  download_url = 'https://github.com/SynedraAcus/bear_hug/archive/v0.2.2.tar.gz',
  keywords = ['gamedev', 'ascii', 'ASCII'],
  license = 'MIT',
  python_requires = '>=3.6',
  install_requires=['bearlibterminal', 'simpleaudio'],
  classifiers = [],
)
