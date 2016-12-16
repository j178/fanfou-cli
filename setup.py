#!/usr/bin/env python3

from setuptools import setup
version = '0.1'

setup(name='fanfou-cli',
      version=version,
      packages=['fanfou_cli'],
      install_requires=['requests-oauthlib'],
      keywords=['internet', 'oauth', 'sns'],
      description=open('README.rst').read(),
      author='John Jiang',
      author_email='nigelchiang@outlook.com',
      license='MIT',
      url='https://github.com/j178/fanfou-cli',

      classifiers=[],

      entry_points={
          'console_scripts': [
              'fan = fanfou_cli.fan:cli'
          ]
      })
