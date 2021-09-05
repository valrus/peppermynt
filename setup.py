'''
peppermynt
----------

*Another static site generator?*

With the ever growing population of static site generators, all filling a certain need, I've yet to find one that allows the generation of anything but the simplest of blogs.

That's where mynt comes in, being designed to give you all the features of a CMS with none of the often rigid implementations of those features.


Install
=======

From PyPI::

    $ pip install peppermynt

Latest trunk::

    $ pip install git+https://github.com/valrus/peppermynt.git


Getting started
===============

After installing mynt head on over and give the `quickstart`_ page and `docs`_ a read.


Dependencies
============

+ `Jinja2`_
+ `Pygments`_
+ `PyYAML`_
+ `watchdog`_
+ `pypandoc`_
+ `pandoc-sidenote`_
+ `doit`_


Support
=======

If you run into any issues or have any questions, open an `issue`_.

.. _docs: http://mynt.uhnomoli.com/
.. _issue: https://github.com/valrus/peppermynt/issues
.. _Jinja2: http://jinja.pocoo.org/
.. _Pygments: http://pygments.org/
.. _PyYAML: http://pyyaml.org/
.. _quickstart: http://mynt.uhnomoli.com/docs/quickstart/
.. _watchdog: http://packages.python.org/watchdog/
.. _pypandoc: https://github.com/bebraw/pypandoc
.. _pandoc-sidenote: https://github.com/jez/pandoc-sidenote
.. _doit: http://pydoit.org/
'''
from setuptools import find_packages, setup

from peppermynt import __version__


setup(
    name = 'peppermynt',
    version = str(__version__),
    author = 'Andrew Fricke, Ian McCowan',
    author_email = 'imccowan@gmail.com',
    url = 'http://mynt.uhnomoli.com/',
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
