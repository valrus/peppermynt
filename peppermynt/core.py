# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from argparse import ArgumentParser
from copy import deepcopy
from glob import iglob
from itertools import chain
from os import path as op
from tempfile import gettempdir
import locale
import logging
import os
import re

from doit.doit_cmd import DoitMain
from pkg_resources import resource_filename

from peppermynt import __version__
from .containers import Config
from .exceptions import ConfigException, OptionException
from .fs import Directory, File
from .processors import Reader, Writer
from .task_loader import PeppermyntTaskLoader
from .utils import get_logger, normpath, Timer, Url
from .cmds import Generate, Gen, Serve, Watch # , Init, Watch, Serve


logger = get_logger('peppermynt')


class DoitPeppermynt(DoitMain):
    """Peppermynt-specific DoitMain."""

    DOIT_CMDS = list(DoitMain.DOIT_CMDS) + [Generate, Gen, Serve]
    TASK_LOADER = PeppermyntTaskLoader

    def __init__(self, peppermynt, *args, **kwargs):
        """Initialize DoitPeppermynt."""
        kwargs.setdefault('extra_config', {})
        kwargs['extra_config']['PEPPERMYNT'] = { 'peppermynt': peppermynt }
        kwargs['extra_config']['GLOBAL'] = {'verbosity': 2 }
        super().__init__(*args, **kwargs)
        peppermynt.doit = self
        self.task_loader = self.TASK_LOADER(peppermynt)


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

    def __init__(self, args=None):
        self._writer = None

        self.content = None
        self.data = {}

        self.src, self.dest, self.temp = None, None, None

        self.args, self.doit_args = self._get_args(args)

        self._reader, self._writer = None, None

        logger.setLevel(self.args.level)

        # if self.args.cmd:
        #     self.doit = DoitPeppermynt(self.args.task_loader(self.args))
        # elif self.args.func:
        #     self.args.func()

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

        force.add_argument(
            '-c', '--clean',
            action='store_true',
            help='Forces generation by deleting the destination if it exists.'
        )
        force.add_argument(
            '-f', '--force',
            action='store_true',
            help='Forces generation by emptying the destination if it exists.'
        )

        gen.set_defaults(doit_cmd='generate')

        init = sub.add_parser('init')

        init.add_argument(
            'dest',
            metavar='destination',
            help='The directory %(prog)s outputs to.'
        )

        init.add_argument('--bare',
            action='store_true',
            help='Initializes a new site without using a theme.')
        init.add_argument('-f', '--force',
            action='store_true',
            help='Forces initialization by deleting the destination if it exists.')
        init.add_argument('-t', '--theme',
            default='dark',
            help='Sets which theme will be used.')

        init.set_defaults(doit_cmd='init')

        serve=sub.add_parser('serve')

        serve.add_argument(
            'src',
            nargs='?', default='.', metavar='source',
            help='The directory %(prog)s will serve.'
        )

        serve.add_argument('--base-url',
            default='/',
            help='Sets the site\'s base URL overriding the config setting.')
        serve.add_argument('-p', '--port',
            default=8080, type=int,
            help='Sets the port used by the server.')

        serve.set_defaults(doit_cmd='serve')

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

        watch.set_defaults(doit_cmd='watch')

        for cmd in DoitMain.DOIT_CMDS:
            cmd_name = cmd.__name__.lower()
            doit_cmd = sub.add_parser(cmd_name)
            doit_cmd.set_defaults(doit_cmd=cmd_name)

        peppermynt_args, doit_args = parser.parse_known_args(args)

        doit_args = [ peppermynt_args.doit_cmd ] + doit_args

        return peppermynt_args, doit_args

    def _get_theme(self, theme):
        return resource_filename(__name__, 'themes/{0}'.format(theme))

    def update_config(self):
        self.config = deepcopy(self.defaults)

        logger.debug('>> Searching for config')

        for ext in ('.yml', '.yaml'):
            f = File(normpath(self.src.path, 'config' + ext))

            if f.exists:
                self._update_config_from_file(f)

                break
        else:
            logger.debug('..  no config file found')

    def _update_config_from_file(self, f):
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
                raise ConfigException(
                    'Invalid config setting.',
                    'setting: {0}'.format(setting),
                    'path traversal is not allowed'
                )

        containers_src = normpath(self.src.path, '_containers')

        for name, config in self.config['containers'].items():
            url = self._container_url(name, config, containers_src)

            config.update((k, v) for k, v in self.container_defaults.items() if k not in config)
            config['url'] = url

        for pattern in self.config['include']:
            if op.commonprefix((self.src.path, normpath(self.src.path, pattern))) != self.src.path:
                raise ConfigException(
                    'Invalid include path.',
                    'path: {0}'.format(pattern),
                    'path traversal is not allowed'
                )


    @staticmethod
    def _container_url(container_name, container_config, containers_src):
        if op.commonprefix((containers_src, normpath(containers_src, container_name))) != containers_src:
            raise ConfigException(
                'Invalid config setting.',
                'setting: containers:{0}'.format(container_name),
                'container name contains illegal characters'
            )

        try:
            url = Url.join(container_config['url'])
        except KeyError:
            raise ConfigException(
                'Invalid config setting.',
                'setting: containers:{0}'.format(container_name),
                'url must be set for all containers'
            )

        if re.search(r'(?:^\.{2}/|/\.{2}$|/\.{2}/)', url):
            raise ConfigException(
                'Invalid config setting.',
                'setting: containers:{0}:url'.format(container_name),
                'path traversal is not allowed'
            )

        return url

    def _initialize(self):
        if self.args.doit_cmd in ['gen', 'generate', 'watch']:
            self.src = Directory(self.args.src)
            self.dest = Directory(self.args.dest)
            self.temp = Directory(op.join(gettempdir(), 'peppermynt'))

            logger.debug('>> Initializing\n..  src:  %s\n..  dest: %s', self.src.path, self.dest.path)

            self.update_config()

            if self.config['locale']:
                try:
                    locale.setlocale(locale.LC_ALL, (self.config['locale'], 'utf-8'))
                except locale.Error:
                    raise ConfigException('Locale not available.', 'run `locale -a` to see available locales')

            self.writer.register({'site': self.config})

    def _init_parse(self):
        Timer.start()
        logger.info('>> Parsing frontmatter')

        self.content = self.reader.init_parse()

        self.data['posts'] = self.content.posts.data
        self.data['containers'] = {}

        for name, container in self.content.containers.items():
            self.data['containers'][name] = container.data

        logger.info('<< Completed frontmatter parsing in %.3fs', Timer.stop())

    def _render(self):
        logger.info('>> Rendering')

        self.writer.register(self.data)

        for i, page in enumerate(self.content.pages):
            self.content.pages[i] = self.writer.render(*page)

    def create_dirs_tasks(self):
        if self.dest.exists:
            if self.args.force:
                yield {
                    'basename': f'empty {self.dest.path}',
                    'actions': [(self.dest.empty, [])]
                }
            elif self.args.clean:
                yield {
                    'basename': f'rm {self.dest.path}',
                    'actions': [(self.dest.rm, [])]
                }
        else:
            yield {
                'basename': f'create dir {self.dest.path}',
                'actions': [(self.dest.mk, [])],
                'targets': [self.dest.path]
            }

    def parse_item_action(self, item):
        item = self.reader.parse_item(self.config, item)
        return item['content']

    def parse_task(self, page):
        _template, data, _url = page
        if data and 'item' in data:
            return {
                'basename': f'parse {page.identifier()}',
                'file_dep': [str(data['item'])],
                'actions': [(self.parse_item_action, (data['item'], ))],
                'uptodate': [not self._fresh()]
            }

        return {
            'basename': f'parse {page.identifier()}',
            'actions': ['true'],
        }

    def render_to_file_action(self, *args):
        out_file = self.writer.render(*args)
        out_file.mk()

    def _new_adjacent_item(self, adjacent_item):
        return False if adjacent_item is None else not File(adjacent_item.output_path(self.dest.path)).exists

    def render_task(self, page):
        _template, data, _url = page
        common_params = {
            'basename': f'render {page.identifier()}',
            'targets': [self.writer.render_path(*page)],
        }
        if data and 'item' in data:
            return {
                'file_dep': [str(data['item'])],
                'actions': [
                    (self.parse_item_action, (data['item'], )),
                    (self.render_to_file_action, tuple(page)),
                ],
                # make sure we re-render if we've added a new post before or after this one,
                # to create the prev/next links
                'uptodate': [
                    not self._new_adjacent_item(data['item'].get('next')),
                    not self._new_adjacent_item(data['item'].get('prev')),
                ],
                **common_params
            }

        return {
            'actions': [(self.render_to_file_action, tuple(page))],
            **common_params
        }

    @staticmethod
    def read_content_action(item, render_path):
        item.read_content(render_path)

    def read_content_task(self, page):
        _template, data, _url = page
        if data and 'item' in data:
            return {
                'basename': f'read content for {page.identifier()}',
                'actions': [
                    (self.read_content_action, (data['item'], self.writer.render_path(*page)))
                ],
                'file_dep': [self.writer.render_path(*page)],
                'uptodate': [False],
            }

        return {
            'basename': f'read content for {page.identifier()}',
            'actions': ['true'],
        }

    def render_feed_task(self, feed):
        return {
            'basename': f'render {feed.identifier()}',
            'task_dep': [
                f'read content for {post.identifier()}'
                for post in self.content.posts.pages
            ],
            'actions': [(self.render_to_file_action, tuple(feed))],
            'targets': [self.writer.render_path(*feed)],
        }

    @staticmethod
    def mk_asset_dir_action(asset_dir):
        asset_dir.mk()

    @staticmethod
    def cp_file_action(src_file, dest_file_path):
        src_file.cp(dest_file_path)

    def copy_assets_tasks(self):
        assets_src = Directory(normpath(self.src.path, '_assets'))
        assets_dest = Directory(normpath(self.dest.path, *self.config['assets_url'].split('/')))

        yield {
            'basename': f'make root asset directory {assets_dest.path}',
            'actions': [(self.mk_asset_dir_action, (assets_dest, ))],
            'targets': [assets_dest.path],
            'uptodate': [True],
        }

        for (dirpath, dirnames, filenames) in os.walk(assets_src.path, True):
            if Directory(dirpath).should_ignore():
                continue
           
            for dirname in dirnames:
                assets_dest_subdir = Directory(
                    os.path.join(
                        assets_dest.path,
                        op.relpath(dirpath, assets_src.path),
                        dirname
                    )
                )
                if assets_dest_subdir.should_ignore():
                    continue
                yield {
                    'basename': f'make asset subdirectory {assets_dest_subdir.path}',
                    'actions': [(self.mk_asset_dir_action, (assets_dest_subdir, ))],
                    'targets': [assets_dest_subdir.path],
                    'uptodate': [True],
                }

            for filename in filenames:
                assets_src_file = File(os.path.join(dirpath, filename))
                assets_dest_file = File(
                    os.path.join(
                        assets_dest.path,
                        op.relpath(dirpath, assets_src.path),
                        filename
                    )
                )
                if assets_src_file.should_ignore():
                    continue
                yield {
                    # debug
                    # 'title': lambda task: f'copy D: {task.file_dep}, CH: {task.dep_changed} > {task.targets}',
                    'basename': f'copy asset {assets_src_file.path} -> {assets_dest_file.path}',
                    'file_dep': [assets_src_file.path],
                    'actions': [(self.cp_file_action, (assets_src_file, assets_dest_file.path))],
                    'targets': [assets_dest_file.path],
                    'verbosity': 0,
                }

    @staticmethod
    def cp_include_dir_action(src_dir, dest_path):
        src_dir.cp(dest_path, True)

    def copy_includes_tasks(self):
        for pattern in self.config['include']:
            for path in iglob(normpath(self.src.path, pattern)):
                dest = path.replace(self.src.path, self.dest.path)

                if op.isdir(path):
                    src_dir = Directory(path)
                    if src_dir.should_ignore():
                        continue
                    yield {
                        'basename': f'copy include directory {src_path.path}',
                        'actions': [(self.cp_include_dir_action, (src_dir, dest))],
                        'targets': [dest],
                        'uptodate': [True],
                    }
                elif op.isfile(path):
                    src_file = File(path)
                    if src_file.should_ignore():
                        continue
                    yield {
                        'basename': f'copy include file {src_file.path}',
                        'file_dep': [src_file.path],
                        'actions': [(self.cp_file_action, (src_file, dest))],
                        'targets': [dest],
                    }

    def generate_tasks(self):
        self._initialize()
        self._init_parse()
        self.writer.register(self.data)

        create_dirs_tasks = self.create_dirs_tasks() # this function should yield one or two things
        # parse_pages_tasks = (self.parse_task(page) for page in self.content.pages)
        render_pages_tasks = (self.render_task(page) for page in self.content.pages)
        read_content_tasks = (self.read_content_task(page) for page in self.content.pages)
        render_feeds_tasks = (self.render_feed_task(feed) for feed in self.content.feeds)
        copy_assets_tasks = self.copy_assets_tasks()
        copy_includes_tasks = self.copy_includes_tasks()

        task_chain = chain(
            create_dirs_tasks,
            # parse_pages_tasks,
            render_pages_tasks,
            read_content_tasks,
            render_feeds_tasks,
            copy_assets_tasks,
            copy_includes_tasks
        )

        # doit expects specifically a generator, of which an itertools chain isn't one
        return (task for task in task_chain)

    def _fresh(self):
        return self.args.force or self.args.clean

    def regenerate(self):
        self._writer = None

        self.config = None
        self.content = None
        self.data.clear()

        self.generate_tasks()

    def generate(self):
        Timer.start()

        if not self.src.exists:
            raise OptionException('Source must exist.')
        elif self.src == self.dest:
            raise OptionException('Source and destination must differ.')
        elif self.dest.exists and not self._fresh():
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
        elif self.dest.exists and not self._fresh():
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
