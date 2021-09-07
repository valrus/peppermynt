# peppermynt

peppermynt is a fork of the [mynt] static site generator, adding a few features:
* (Mostly) incremental builds using [pydoit]
* [Tufte CSS], including sidenotes
* [mathjax] for rendering math

[mynt]: https://github.com/Anomareh/mynt
[pydoit]: http://pydoit.org/
[Tufte CSS]: https://edwardtufte.github.io/tufte-css/
[mathjax]: https://www.mathjax.org/

### Install

Latest trunk:

    $ pip install git+https://github.com/valrus/peppermynt.git


### Dependencies

* [pandoc]
* [pandoc-sidenote]

[pandoc]: https://pandoc.org/
[pandoc-sidenote]: https://github.com/jez/pandoc-sidenote

### Support

If you run into any issues or have any questions, feel free to open an [issue].
Be warned that peppermynt is currently very much a personal "it works on my machine" kind of situation,
and I only work on it in my free time.
So please don't expect much in the way of support.

[issue]: https://github.com/valrus/peppermynt/issues
