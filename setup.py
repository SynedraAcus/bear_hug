from setuptools import setup
setup(
  name = 'bear_hug',
  packages = ['bear_hug'], # this must be the same as the name above
  version = '0.0.1',
  description = 'An object-oriented ECS library for ASCII games. Wraps bearlibterminal',
  author = 'Alexey Morozov',
  author_email = 'alexeymorozov1991@gmail.com',
  url = 'https://github.com/SynedraAcus/bear_hug', # use the URL to the github repo
  download_url = 'https://github.com/SynedraAcus/bear_hug/archive/0.0.1.tar.gz', # I'll explain this in a second
  keywords = ['gamedev', 'ascii', 'ASCII'],
  license='MIT',
  install_requires=['bearlibterminal'],
  classifiers = [],
)
