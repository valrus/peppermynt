# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from argparse import ArgumentParser
from copy import deepcopy
from glob import iglob
import locale
import logging
from os import chdir, getcwd, path as op
import re
from time import sleep
from tempfile import gettempdir

from doit.task import dict_to_task
from doit.cmd_base import TaskLoader2, Command, DoitCmdBase
from doit.doit_cmd import DoitMain
from pkg_resources import resource_filename
from watchdog.observers import Observer

from peppermynt import __version__
from peppermynt.containers import Config
from peppermynt.exceptions import ConfigException, OptionException
from peppermynt.fs import Directory, EventHandler, File
from peppermynt.processors import Reader, Writer
from peppermynt.server import RequestHandler, Server
from peppermynt.utils import get_logger, normpath, Timer, Url


logger = get_logger('peppermynt')


class PeppermyntTaskLoader(TaskLoader2):
    """Peppermynt-specific task loader."""
    def __init__(self, peppermynt, args):
        self.peppermynt = peppermynt
        self.args = args


class PeppermyntGenerateTaskLoader(PeppermyntTaskLoader):
    def load_doit_config(self):
        pass

    def load_tasks(self, cmd, pos_args):
        pass

    def setup(self, opt_values):
        pass


class PeppermyntInitTaskLoader(PeppermyntTaskLoader):
    def load_doit_config(self):
        pass

    def load_tasks(self, cmd, pos_args):
        pass

    def setup(self, opt_values):
        pass


class ServeCmd(Command):
    def execute(self, params, args):
        self.src = Directory(args.src)
        base_url = Url.join(args.base_url, '')

        if not self.src.exists:
            raise OptionException('Source must exist.')

        logger.info('>> Serving at 127.0.0.1:%s', args.port)
        logger.info('Press ctrl+c to stop.')

        cwd = getcwd()
        self.server = Server(('', args.port), base_url, RequestHandler)

        chdir(self.src.path)

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()
            chdir(cwd)

            # why?
            print('')


class WatchCmd(Command):
    def execute(self, params, args):
        self.src = Directory(args.src)
        self.dest = Directory(args.dest)

        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not args.force:
            raise OptionException('Destination already exists.',
                'the -f flag must be passed to force watching by emptying the destination every time a change is made')

        logger.info('>> Watching')
        logger.info('Press ctrl+c to stop.')

        self.observer = Observer()

        self.observer.schedule(EventHandler(self.src.path, self._regenerate), self.src.path, True)
        self.observer.start()

        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()

            print('')

        self.observer.join()



class DoitPeppermynt(DoitMain):
    """Peppermynt-specific DoitMain."""
    pass


class Peppermynt(object):
    defaults = {
        'archive_layout': None,
        'archives_url': '/',
        'assets_url': '/assets/',
        'base_url': '/',
        'containers': {},
        'date_format': '%A, %B %d, %Y',
        'domain': None,
        'include': [],
        'locale': None,
        'posts_order': 'desc',
        'posts_sort': 'timestamp',
        'posts_url': '/<year>/<month>/<day>/<slug>/',
        'pygmentize': True,
        'renderer': 'jinja',
        'tag_layout': None,
        'tags_url': '/',
        'version': __version__
    }

    container_defaults = {
        'archive_layout': None,
        'archives_url': '/',
        'order': 'desc',
        'sort': 'timestamp',
        'tag_layout': None,
        'tags_url': '/'
    }

    def __init__(self, args = None):
        self._reader = None
        self._writer = None

        self.config = None
        self.posts = None
        self.containers = None
        self.data = {}
        self.pages = None

        self.args = self._get_args(args)

        logger.setLevel(self.args.level)

        if self.args.cmd:
            self.doit = DoitPeppermynt(self.args.task_loader(self.args))
        elif self.args.func:
            self.args.func()

    @staticmethod
    def _logging_level(arg):
        return getattr(logging, arg, logging.INFO)

    def _get_args(self, args):
        parser = ArgumentParser(description = 'A static blog generator.')
        sub = parser.add_subparsers()

        level = parser.add_mutually_exclusive_group()

        level.add_argument(
            '-l', '--level',
            default=logging.INFO, type=self._logging_level,
            choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR],
            help='Sets %(prog)s\'s log level.')
        level.add_argument('-q', '--quiet',
            action='store_const', const='ERROR', dest='level',
            help='Sets %(prog)s\'s log level to ERROR.')
        level.add_argument('-v', '--verbose',
            action='store_const', const='DEBUG', dest='level',
            help='Sets %(prog)s\'s log level to DEBUG.')

        parser.add_argument('-V', '--version',
            action='version', version='%(prog)s v{0}'.format(__version__),
            help='Prints %(prog)s\'s version and exits.')

        gen=sub.add_parser('gen')

        gen.add_argument('src',
            nargs='?', default='.', metavar='source',
            help='The directory %(prog)s looks in for source files.')
        gen.add_argument('dest',
            metavar='destination',
            help='The directory %(prog)s outputs to.')

        gen.add_argument('--base-url',
            help='Sets the site\'s base URL overriding the config setting.')
        gen.add_argument('--locale',
            help='Sets the locale used by the renderer.')

        force=gen.add_mutually_exclusive_group()

        force.add_argument('-c', '--clean',
            action='store_true',
            help='Forces generation by deleting the destination if it exists.')
        force.add_argument('-f', '--force',
            action='store_true',
            help='Forces generation by emptying the destination if it exists.')

        gen.set_defaults(cmd="generate")

        init=sub.add_parser('init')

        init.add_argument('dest',
            metavar='destination',
            help='The directory %(prog)s outputs to.')

        init.add_argument('--bare',
            action='store_true',
            help='Initializes a new site without using a theme.')
        init.add_argument('-f', '--force',
            action='store_true',
            help='Forces initialization by deleting the destination if it exists.')
        init.add_argument('-t', '--theme',
            default='dark',
            help='Sets which theme will be used.')

        init.set_defaults(cmd="init")

        serve=sub.add_parser('serve')

        serve.add_argument('src',
            nargs='?', default='.', metavar='source',
            help='The directory %(prog)s will serve.')

        serve.add_argument('--base-url',
            default='/',
            help='Sets the site\'s base URL overriding the config setting.')
        serve.add_argument('-p', '--port',
            default=8080, type=int,
            help='Sets the port used by the server.')

        serve.set_defaults(func=self.serve)

        watch=sub.add_parser('watch')

        watch.add_argument('src',
            nargs='?', default='.', metavar='source',
            help='The directory %(prog)s looks in for source files.')
        watch.add_argument('dest',
            metavar='destination',
            help='The directory %(prog)s outputs to.')

        watch.add_argument('--base-url',
            help='Sets the site\'s base URL overriding the config setting.')
        watch.add_argument('-f', '--force',
            action='store_true',
            help='Forces watching by emptying the destination every time a change is made if it exists.')
        watch.add_argument('--locale',
            help='Sets the locale used by the renderer.')

        watch.set_defaults(func=self.watch)

        return parser.parse_args(args)

    def _get_theme(self, theme):
        return resource_filename(__name__, 'themes/{0}'.format(theme))

    def _update_config(self):
        self.config = deepcopy(self.defaults)

        logger.debug('>> Searching for config')

        for ext in ('.yml', '.yaml'):
            f = File(normpath(self.src.path, 'config' + ext))

            if f.exists:
                logger.debug('..  found: %s', f.path)

                try:
                    self.config.update(Config(f.content))
                except ConfigException as e:
                    raise ConfigException(e.message, 'src: {0}'.format(f.path))

                self.config['locale'] = self.args.locale or self.config['locale']

                self.config['assets_url'] = Url.join(self.config['assets_url'], '')
                self.config['base_url'] = Url.join(self.args.base_url or self.config['base_url'], '')

                for setting in ('archives_url', 'posts_url', 'tags_url'):
                    self.config[setting] = Url.join(self.config[setting])

                for setting in ('archives_url', 'assets_url', 'base_url', 'posts_url', 'tags_url'):
                    if re.search(r'(?:^\.{2}/|/\.{2}$|/\.{2}/)', self.config[setting]):
                        raise ConfigException('Invalid config setting.',
                            'setting: {0}'.format(setting),
                            'path traversal is not allowed')

                containers_src = normpath(self.src.path, '_containers')

                for name, config in self.config['containers'].items():
                    if op.commonprefix((containers_src, normpath(containers_src, name))) != containers_src:
                        raise ConfigException('Invalid config setting.',
                            'setting: containers:{0}'.format(name),
                            'container name contains illegal characters')

                    try:
                        url = Url.join(config['url'])
                    except KeyError:
                        raise ConfigException('Invalid config setting.',
                            'setting: containers:{0}'.format(name),
                            'url must be set for all containers')

                    if re.search(r'(?:^\.{2}/|/\.{2}$|/\.{2}/)', url):
                        raise ConfigException('Invalid config setting.',
                            'setting: containers:{0}:url'.format(name),
                            'path traversal is not allowed')

                    config.update((k, v) for k, v in self.container_defaults.items() if k not in config)
                    config['url'] = url

                for pattern in self.config['include']:
                    if op.commonprefix((self.src.path, normpath(self.src.path, pattern))) != self.src.path:
                        raise ConfigException('Invalid include path.',
                            'path: {0}'.format(pattern),
                            'path traversal is not allowed')

                break
        else:
            logger.debug('..  no config file found')


    def _initialize(self):
        logger.debug('>> Initializing\n..  src:  %s\n..  dest: %s', self.src.path, self.dest.path)

        self._update_config()

        if self.config['locale']:
            try:
                locale.setlocale(locale.LC_ALL, (self.config['locale'], 'utf-8'))
            except locale.Error:
                raise ConfigException('Locale not available.',
                    'run `locale -a` to see available locales')

        self.writer.register({'site': self.config})

    def _parse(self):
        logger.info('>> Parsing')

        self.posts, self.containers, self.pages = self.reader.parse()

        self.data['posts'] = self.posts.data
        self.data['containers'] = {}

        for name, container in self.containers.items():
            self.data['containers'][name] = container.data

    def _render(self):
        logger.info('>> Rendering')

        self.writer.register(self.data)

        for i, page in enumerate(self.pages):
            self.pages[i] = self.writer.render(*page)

    def _generate(self):
        self._initialize()
        self._parse()
        self._render()

        logger.info('>> Generating')

        assets_src = Directory(normpath(self.src.path, '_assets'))
        assets_dest = Directory(normpath(self.dest.path, *self.config['assets_url'].split('/')))

        if self.dest.exists:
            if self.args.force:
                self.dest.empty()
            else:
                self.dest.rm()
        else:
            self.dest.mk()

        for page in self.pages:
            page.mk()

        assets_src.cp(assets_dest.path)

        for pattern in self.config['include']:
            for path in iglob(normpath(self.src.path, pattern)):
                dest = path.replace(self.src.path, self.dest.path)

                if op.isdir(path):
                    Directory(path).cp(dest, False)
                elif op.isfile(path):
                    File(path).cp(dest)

    def _regenerate(self):
        self._reader = None
        self._writer = None

        self.config = None
        self.posts = None
        self.containers = None
        self.data.clear()
        self.pages = None

        self._generate()

    def generate(self):
        Timer.start()

        self.src = Directory(self.args.src)
        self.temp = Directory(op.join(gettempdir(), 'peppermynt'))
        self.dest = Directory(self.args.dest)

        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not (self.args.force or self.args.clean):
            raise OptionException('Destination already exists.',
                'the -c or -f flag must be passed to force generation by deleting or emptying the destination')

        self._generate()

        logger.info('Completed in %.3fs', Timer.stop())

    def init(self):
        Timer.start()

        self.src = Directory(self._get_theme(self.args.theme))
        self.dest = Directory(self.args.dest)

        if not self.src.exists:
            raise OptionException('Theme not found.')
        elif self.dest.exists and not self.args.force:
            raise OptionException('Destination already exists.',
                'the -f flag must be passed to force initialization by deleting the destination')

        logger.info('>> Initializing')

        if self.args.bare:
            self.dest.rm()

            for d in ('_assets/css', '_assets/images', '_assets/js', '_templates', '_posts'):
                Directory(normpath(self.dest.path, d)).mk()

            File(normpath(self.dest.path, 'config.yml')).mk()
        else:
            self.src.cp(self.dest.path, False)

        logger.info('Completed in %.3fs', Timer.stop())

    @property
    def reader(self):
        if self._reader is None:
            self._reader = Reader(self.src, self.temp, self.dest, self.config, self.writer)

        return self._reader

    @property
    def writer(self):
        if self._writer is None:
            self._writer = Writer(self.src, self.temp, self.dest, self.config)

        return self._writer
