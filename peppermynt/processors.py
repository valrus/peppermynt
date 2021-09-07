# -*- coding: utf-8 -*-

from calendar import timegm
from collections import defaultdict
from datetime import datetime
from importlib import import_module
from os import path as op
import re

from pkg_resources import DistributionNotFound, iter_entry_points, load_entry_point
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from peppermynt.containers import Config, Container, Item, Items, Posts, SiteContent, Page
from peppermynt.exceptions import ConfigException, ContentException, ParserException, RendererException
from peppermynt.fs import File
from peppermynt.utils import get_logger, dest_path, Timer, unescape, Url


logger = get_logger('peppermynt')


class Reader:
    def __init__(self, src, temp, dest, site, writer):
        self._writer = writer

        self._parsers = {}
        self._extensions = defaultdict(list)
        self._cache = {}

        self.src = src
        self.temp = temp
        self.dest = dest
        self.site = site

        self._find_parsers()

    def _find_parsers(self):
        for parser in iter_entry_points('peppermynt.parsers'):
            name = parser.name

            try:
                Parser = parser.load()
            except DistributionNotFound as e:
                logger.debug('@@ The %s parser could not be loaded due to a missing requirement: %s.', name, str(e))

                continue

            for extension in Parser.accepts:
                if 'parsers' in self.site and self.site['parsers'].get(extension.lstrip('.')) == name:
                    self._extensions[extension].insert(0, name)
                else:
                    self._extensions[extension].append(name)

            self._parsers[name] = Parser

    def _get_date(self, mtime, date):
        if not date:
            return mtime

        d = [None, None, None, 0, 0]

        for i, v in enumerate(date.split('-')):
            d[i] = v

        if not d[3]:
            d[3], d[4] = mtime.strftime('%H %M').split()
        elif not d[4]:
            d[4] = '{0:02d}'.format(d[4])

        return datetime.strptime('-'.join(d), '%Y-%m-%d-%H-%M')

    def _get_parser(self, item, parser = None):
        if not parser:
            try:
                parser = self._extensions[item.extension()][0]
            except KeyError:
                raise ParserException('No parser found that accepts \'{0}\' files.'.format(item.extension()),
                    'src: {0}'.format(item))

        if parser in self._cache:
            return self._cache[parser]

        options = self.site.get(parser, None)

        if parser in self._parsers:
            Parser = self._parsers[parser](options)
        else:
            try:
                Parser = import_module('peppermynt.parsers.{0}'.format(parser)).Parser(options)
            except ImportError:
                raise ParserException('The {0} parser could not be found.'.format(parser))

        self._cache[parser] = Parser

        return Parser

    def _parse_filename(self, f):
        date, text = re.match(r'(?:(\d{4}(?:-\d{2}-\d{2}){1,2})-)?(.+)', f.name).groups()
        return (text, self._get_date(f.mtime, date))

    def _init_container(self, container):
        for f in container.path:
            container.add(self._init_item(container.config, f))

        container.sort()
        container.tag()
        container.archive()

        return container

    def _init_item(self, config, f, simple = False):
        Timer.start()

        frontmatter, bodymatter = self._parse_item_frontmatter(f)

        item = Item(f.path)

        text, date = self._parse_filename(f)
        item['date'] = date.strftime(self.site['date_format'])
        item['timestamp'] = timegm(date.utctimetuple())

        if simple:
            item['url'] = Url.from_path(f.root.path.replace(self.src.path, ''), text)
        else:
            item['tags'] = []
            item['url'] = Url.from_format(config['url'], text, date, frontmatter)
        item['dest'] = dest_path(self.dest.path, item['url'])

        item.update(frontmatter)
        item['raw_content'] = bodymatter

        return item

    def parse_item(self, config, item, simple = False):
        bodymatter = item.pop('raw_content')
        parser = self._get_parser(item, item.get('parser', config.get('parser', None)))
        content = parser.parse(self._writer.from_string(bodymatter, item))
        item['content'] = content
        if not simple:
            item['excerpt'] = re.search(r'\A.*?(?:<p>(.+?)</p>)?', content, re.M | re.S).group(1)

        logger.debug('..  (%.3fs) %s', Timer.stop(), str(item).replace(self.src.path, ''))

        return item

    def _parse_item_frontmatter(self, f):
        try:
            frontmatter, bodymatter = re.search(r'\A---\s+^(.+?)$\s+---\s*(.*)\Z', f.content, re.M | re.S).groups()
            frontmatter = Config(frontmatter)
        except AttributeError:
            raise ContentException('Invalid frontmatter.',
                'src: {0}'.format(f.path),
                'frontmatter must not be empty')
        except ConfigException:
            raise ConfigException('Invalid frontmatter.',
                'src: {0}'.format(f.path),
                'fontmatter contains invalid YAML')

        if 'layout' not in frontmatter:
            raise ContentException('Invalid frontmatter.',
                'src: {0}'.format(f.path),
                'layout must be set')

        frontmatter.pop('url', None)

        return frontmatter, bodymatter

    def init_parse(self):
        posts = self._init_container(Posts(self.src, self.site))
        containers = {}
        miscellany = Container('miscellany', self.src, None)
        pages = posts.pages
        feeds = []

        for name, config in self.site['containers'].items():
            container = self._init_container(Items(name, self.src, config))

            containers[name] = container
            pages.extend(container.pages)

        for f in miscellany.path:
            if f.extension in self._extensions:
                miscellany.add(self._init_item(miscellany.config, f, True))
            elif f.extension == '.xml':
                # Assume for now that the only xml files are feeds
                feeds.append(Page(f.path.replace(self.src.path, ''), None, None))
            elif f.extension in ('.html', '.htm'):
                pages.append(Page(f.path.replace(self.src.path, ''), None, None))

        pages.extend(miscellany.pages)

        return SiteContent(posts, containers, pages, feeds)


class Writer:
    def __init__(self, src, temp, dest, site):
        self.src = src
        self.temp = temp
        self.dest = dest
        self.site = site

        self._renderer = self._get_renderer()

    def _get_renderer(self):
        renderer = self.site['renderer']
        options = self.site.get(renderer, None)

        try:
            Renderer = load_entry_point('peppermynt', 'peppermynt.renderers', renderer)
        except DistributionNotFound as e:
            raise RendererException('The {0} renderer requires {1}.'.format(renderer, str(e)))
        except ImportError:
            try:
                Renderer = import_module('peppermynt.renderers.{0}'.format(renderer)).Renderer
            except ImportError:
                raise RendererException('The {0} renderer could not be found.'.format(renderer))

        return Renderer(self.src.path, options)

    def _highlight(self, match):
        language, code = match.groups()
        formatter = HtmlFormatter(linenos = 'table')
        code = unescape(code)

        try:
            code = highlight(code, get_lexer_by_name(language), formatter)
        except ClassNotFound:
            code = highlight(code, get_lexer_by_name('text'), formatter)

        return '<div class="code"><div>{0}</div></div>'.format(code)

    def _pygmentize(self, html):
        return re.sub(r'<pre><code[^>]+data-lang="([^>]+)"[^>]*>(.+?)</code></pre>', self._highlight, html, flags = re.S)

    def from_string(self, string, data = None):
        return self._renderer.from_string(string, data)

    def register(self, data):
        self._renderer.register(data)

    def render_path(self, template, _data = None, url = None):
        return dest_path(self.dest.path, url or template)

    def render(self, template, data = None, url = None):
        path = self.render_path(template, data, url)

        try:
            Timer.start()

            content = self._renderer.render(template, data)

            if self.site['pygmentize']:
                content = self._pygmentize(content)

            logger.debug('..  (%.3fs) %s', Timer.stop(), path.replace(self.dest.path, ''))
        except RendererException as e:
            raise RendererException(
                e.message,
                '{0} in container item {1}'.format(template, data.get('item', url or template))
            )

        return File(path, content)
