#!/usr/bin/env python3

from setuptools import setup

version = '0.1.1'

setup(name='fanfou-cli',
      version=version,
      packages=['fanfoucli'],
      install_requires=['requests-oauthlib'],
      keywords=['internet', 'oauth', 'sns'],
      description='Fanfou Command Line Client',
      long_description=open('README.md').read(),
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
