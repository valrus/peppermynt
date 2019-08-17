#!/usr/bin/env python

from os import chdir, getcwd, path as op
from tempfile import gettempdir
import locale
import sys

from doit.cmd_base import TaskLoader
from doit.loader import generate_tasks
from doit.reporter import ExecutedOnlyReporter

from .containers import Posts, Items
from .exceptions import ConfigException, OptionException
from .fs import Directory, EventHandler, File
from .utils import get_logger, normpath, Timer, Url


logger = get_logger('peppermynt')


def items(src, site):
    posts = Posts(src, site)
    for f in posts.path:
        yield {
            'file': f,
            'container_config': posts.config,
        }

    for name, container_config in site['containers'].items():
        item_container = Items(name, src, container_config)
        for f in item_container.path:
            yield {
                'file': f,
                'container_config': item_container.config
            }


class PeppermyntTaskLoader(TaskLoader):
    def __init__(self, peppermynt):
        super().__init__()
        self.peppermynt = peppermynt

    def load_tasks(self, cmd, opt_values, pos_args):
        doit_config = {
            'reporter': ExecutedOnlyReporter,
            'outfile': sys.stderr,
        }
        return generate_tasks('render_site', self.peppermynt.generate_tasks()), doit_config
