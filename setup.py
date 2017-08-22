#!/usr/bin/env python

from distutils.core import setup

setup(name='carbonstat',
      version='1.0',
      description='Metric collection agent for Carbon',
      long_description=open('README.rst').read(),
      platforms='all',
      license='MIT',
      author='Alexander Tikhonov',
      author_email='random.gauss@gmail.com',
      url='https://github.com/Fatal1ty/carbonstat',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: Implementation :: CPython',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System',
          'Topic :: System :: Software Distribution',
          ],
      py_modules=['carbonstat'])
