'''
peppermynt
----------

peppermynt is a fork of the `mynt`_ static site generator, adding a few features:
+ (Mostly) incremental builds using `pydoit`_
+ `Tufte CSS`_, including sidenotes
+ `mathjax` for rendering math


Install
=======

Latest trunk::

    $ pip install git+https://github.com/valrus/peppermynt.git


Dependencies
============

+ `pandoc`_
+ `pandoc-sidenote`_


Support
=======

If you run into any issues or have any questions, open an `issue`_.

.. _mynt: https://github.com/Anomareh/mynt
.. _issue: https://github.com/valrus/peppermynt/issues
.. _Jinja2: http://jinja.pocoo.org/
.. _pandoc: https://pandoc.org/
.. _pandoc-sidenote: https://github.com/jez/pandoc-sidenote
.. _pydoit: http://pydoit.org/
.. _Tufte CSS: https://edwardtufte.github.io/tufte-css/
.. _mathjax: https://www.mathjax.org/
'''
from setuptools import find_packages, setup

from peppermynt import __version__


setup(
    name = 'peppermynt',
    version = str(__version__),
    author = 'Andrew Fricke, Ian McCowan',
    author_email = 'ian@mccowan.space',
    url = 'https://github.com/valrus/peppermynt',
    description = 'A static site generator with Tufte CSS.',
    long_description = __doc__,
    license = 'BSD',
    platforms = 'any',
    zip_safe = False,
    packages = find_packages(),
    include_package_data = True,
    entry_points = {
        'peppermynt.parsers' : [
            'tufte = peppermynt.parsers.tufte:Parser'
        ],
        'peppermynt.renderers': [
            'jinja = peppermynt.renderers.jinja:Renderer'
        ],
        'console_scripts': 'peppermynt = peppermynt.main:main'
    },
    install_requires = [
        'Jinja2>=2.7.2',
        'Pygments',
        'PyYAML',
        'watchdog',
        'pypandoc',
        'doit'
    ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Text Processing',
        'Topic :: Utilities'
    ]
)
