#!/usr/bin/env python3

from setuptools import setup

import fanfoucli

setup(name='fanfou-cli',
      version=fanfoucli.__version__,
      packages=['fanfoucli'],
      install_requires=['requests-oauthlib', 'arrow'],
      keywords=['internet', 'oauth', 'sns'],
      description='Fanfou Command Line Client',
      long_description=open('README.md', encoding='utf8').read(),
      author='John Jiang',
      author_email='nigelchiang@outlook.com',
      license='MIT',
      url='https://github.com/j178/fanfou-cli',

      classifiers=[],

      entry_points={
          'console_scripts': [
              'fan = fanfoucli.cli:main'
          ]
      })
